import os
import tempfile
import base64
import platform
import datetime
import psutil
from fastapi import FastAPI, File, UploadFile, HTTPException, status, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.config import settings
from backend.utils.logger import logger
from backend.ai.client import ai_client
from backend.voice.stt import transcribe_audio
from backend.voice.tts import synthesize_speech
from backend.memory.service import memory_service

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Verify setup configuration on application startup."""
    logger.info("Initializing JARVIS V10 Application (Advanced Unified Architecture Online)...")
    try:
        settings.validate_config()
        logger.info("Configuration check passed successfully.")
    except ValueError as e:
        logger.error(f"Configuration Validation Error: {e}")
    yield

# Initialize FastAPI application
app = FastAPI(
    title="JARVIS AI Agent Backend",
    description="Backend services for JARVIS (V10 — Advanced Unified Architecture)",
    version="10.0.0",
    lifespan=lifespan
)

# Enable CORS for local, LAN, and mobile clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    )


async def verify_api_key(x_jarvis_api_key: str = Header(None, alias="X-Jarvis-API-Key")):
    """Verify that incoming requests carry a valid JARVIS API authentication token."""
    if not settings.jarvis_api_key:
        return
        
    if x_jarvis_api_key != settings.jarvis_api_key:
        logger.warning(f"Rejected unauthorized API request. Invalid key provided: '{x_jarvis_api_key}'")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Invalid or missing X-Jarvis-API-Key header."
        )

# Pydantic schemas for request/response bodies
class Message(BaseModel):
    role: str = Field(..., description="The role of the message sender, e.g. 'user', 'assistant', or 'system'")
    content: str = Field(..., description="The text content of the message")

class ChatRequest(BaseModel):
    messages: list[Message] = Field(..., description="The context/history of the conversation")
    session_id: str = Field(default="default", description="Session identifier for memory history")

class ChatResponse(BaseModel):
    response: str = Field(..., description="The AI's text response")

class VoiceResponse(BaseModel):
    transcribed_text: str = Field(..., description="The transcribed text from the uploaded audio")
    llm_response: str = Field(..., description="The LLM response to the transcription")
    audio_base64: str = Field(..., description="Base64-encoded string of the synthesized response audio (MP3)")

class RememberRequest(BaseModel):
    content: str = Field(..., description="The fact, note, or information to remember")
    key: str = Field(default="", description="Short title or key identifier")
    category: str = Field(default="fact", description="Category: fact, project, note, preference, general")
    tags: list[str] = Field(default=[], description="Optional tags")

class PreferenceRequest(BaseModel):
    key: str = Field(..., description="The preference key")
    value: str = Field(..., description="The preference value")
    category: str = Field(default="general", description="Category")

class TaskCreateRequest(BaseModel):
    title: str = Field(..., description="Title of the task")
    description: str = Field(default="", description="Optional description")
    project: str = Field(default="General", description="Project name")
    priority: str = Field(default="medium", description="low, medium, high, urgent")
    due_date: str = Field(default="", description="Due date string")


from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
def serve_pwa_root():
    """Serves the JARVIS Mobile PWA web app."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {"status": "online", "app": "JARVIS Backend", "version": "10.0.0"}

@app.get("/health")
def health_check():
    """Basic service health check."""
    return {
        "status": "healthy",
        "app": "JARVIS Backend",
        "version": "10.0.0"
    }


@app.post("/api/chat", response_model=ChatResponse, dependencies=[Depends(verify_api_key)])
async def chat(request: ChatRequest):
    """
    Accepts text messages history, queries the Groq LLM API, and returns the response.
    Automatically persists conversation turns in SQLite memory.
    """
    logger.info(f"Received text chat request with {len(request.messages)} messages.")
    try:
        # Save latest user message to SQLite memory
        last_user_msg = next((m for m in reversed(request.messages) if m.role == "user"), None)
        if last_user_msg:
            memory_service.save_conversation(
                role="user",
                content=last_user_msg.content,
                session_id=request.session_id
            )

        # Convert request models to dictionary format required by Groq API
        messages_dict = [msg.model_dump() for msg in request.messages]
        
        # Call Groq LLM
        response_text = await ai_client.generate_chat_response(messages_dict)
        
        # Save assistant response to SQLite memory
        memory_service.save_conversation(
            role="assistant",
            content=response_text,
            session_id=request.session_id
        )
        
        return ChatResponse(response=response_text)
        
    except Exception as e:
        logger.error(f"Error in /api/chat endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while generating the chat response: {str(e)}"
        )


@app.post("/api/voice", response_model=VoiceResponse, dependencies=[Depends(verify_api_key)])
async def voice_chat(file: UploadFile = File(...)):
    """
    Voice Chat pipeline:
    1. Receives an audio file (wav, mp3, m4a, etc.).
    2. Transcribes it into text using Groq's Whisper API.
    3. Feeds transcription into the LLM.
    4. Generates a spoken MP3 version of the LLM response using Edge-TTS.
    5. Returns transcribed text, response text, and the synthesized audio encoded as Base64.
    """
    logger.info(f"Received voice chat request. File: '{file.filename}', Content Type: '{file.content_type}'")
    
    temp_input_path = None
    temp_output_path = None
    
    try:
        # 1. Save uploaded file to a temporary file locally
        file_ext = os.path.splitext(file.filename)[1] or ".wav"
        with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as temp_in:
            audio_bytes = await file.read()
            if not audio_bytes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uploaded audio file content is empty."
                )
            temp_in.write(audio_bytes)
            temp_input_path = temp_in.name
            
        logger.info(f"Saved uploaded voice recording to: {temp_input_path}")
        
        # 2. Convert Speech to Text (STT) via Groq Whisper API
        try:
            transcribed_text = await transcribe_audio(temp_input_path)
            logger.info(f"Speech transcription success. Result: '{transcribed_text}'")
        except Exception as e:
            logger.error(f"Failed to transcribe user audio: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Speech-to-Text transcription failed: {str(e)}"
            )
            
        if not transcribed_text.strip():
            logger.info("Transcribed text was empty. Returning empty response.")
            return VoiceResponse(
                transcribed_text="",
                llm_response="I'm sorry, I couldn't hear anything.",
                audio_base64=""
            )
            
        # Save user voice message to memory
        memory_service.save_conversation(role="user", content=transcribed_text, session_id="voice")

        # 3. Feed transcribed text to Groq LLM
        try:
            chat_history = [
                {
                    "role": "system",
                    "content": "You are JARVIS, a helpful, polite, and witty AI assistant. Keep responses brief, conversational, and natural to read out loud."
                },
                {"role": "user", "content": transcribed_text}
            ]
            llm_response = await ai_client.generate_chat_response(chat_history)
            logger.info(f"LLM generated response successfully: '{llm_response}'")
            
            # Save assistant response to memory
            memory_service.save_conversation(role="assistant", content=llm_response, session_id="voice")
        except Exception as e:
            logger.error(f"Failed to generate LLM response for voice input: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"LLM processing failed: {str(e)}"
            )
            
        # 4. Convert response text back to Speech (TTS) using Edge-TTS
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_out:
            temp_output_path = temp_out.name
            
        try:
            await synthesize_speech(llm_response, temp_output_path)
            logger.info(f"TTS audio response generated at: {temp_output_path}")
        except Exception as e:
            logger.error(f"Failed to synthesize TTS response audio: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Text-to-Speech synthesis failed: {str(e)}"
            )
            
        # 5. Read output file and encode as Base64 to return in JSON
        try:
            with open(temp_output_path, "rb") as out_file:
                output_audio_bytes = out_file.read()
                audio_base64 = base64.b64encode(output_audio_bytes).decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to base64-encode output speech file: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to process output audio stream: {str(e)}"
            )
            
        return VoiceResponse(
            transcribed_text=transcribed_text,
            llm_response=llm_response,
            audio_base64=audio_base64
        )
        
    finally:
        # Safeguard: Always clean up temporary files from disk
        if temp_input_path and os.path.exists(temp_input_path):
            try:
                os.remove(temp_input_path)
                logger.debug(f"Removed temp input file: {temp_input_path}")
            except Exception as e:
                logger.warning(f"Error removing temp input file {temp_input_path}: {e}")
                
        if temp_output_path and os.path.exists(temp_output_path):
            try:
                os.remove(temp_output_path)
                logger.debug(f"Removed temp output file: {temp_output_path}")
            except Exception as e:
                logger.warning(f"Error removing temp output file {temp_output_path}: {e}")


# --- Version 5: Memory REST Endpoints ---

@app.post("/api/memory/remember", dependencies=[Depends(verify_api_key)])
def remember_memory(req: RememberRequest):
    """Stores a fact, note, or project memory."""
    entry = memory_service.save_memory(
        content=req.content,
        key=req.key,
        category=req.category,
        tags=req.tags
    )
    return {"status": "success", "memory": entry}


@app.get("/api/memory/recall", dependencies=[Depends(verify_api_key)])
def recall_memory(query: str, category: str = None, top_k: int = 5):
    """Retrieves memories matching query using hybrid semantic search."""
    results = memory_service.recall_memories(query=query, category=category, top_k=top_k)
    return {"status": "success", "query": query, "results": results}


@app.get("/api/memory/preferences", dependencies=[Depends(verify_api_key)])
def get_preferences():
    """Returns all stored user preferences."""
    prefs = memory_service.get_all_preferences()
    return {"status": "success", "preferences": prefs}


@app.post("/api/memory/preferences", dependencies=[Depends(verify_api_key)])
def set_preference(req: PreferenceRequest):
    """Sets or updates a user preference key-value."""
    pref = memory_service.set_preference(key=req.key, value=req.value, category=req.category)
    return {"status": "success", "preference": pref}


@app.get("/api/memory/tasks", dependencies=[Depends(verify_api_key)])
def list_tasks(status: str = None, project: str = None):
    """Lists user tasks with optional status and project filters."""
    tasks = memory_service.list_tasks(status=status, project=project)
    return {"status": "success", "tasks": tasks}


@app.post("/api/memory/tasks", dependencies=[Depends(verify_api_key)])
def create_task(req: TaskCreateRequest):
    """Creates a new task item."""
    task = memory_service.add_task(
        title=req.title,
        description=req.description,
        project=req.project,
        priority=req.priority,
        due_date=req.due_date
    )
    return {"status": "success", "task": task}


@app.get("/api/memory/history", dependencies=[Depends(verify_api_key)])
def get_history(session_id: str = "default", limit: int = 20):
    """Returns past conversation history from SQLite memory."""
    history = memory_service.get_conversation_history(session_id=session_id, limit=limit)
    return {"status": "success", "history": history}


@app.get("/api/system/status", dependencies=[Depends(verify_api_key)])
def get_system_status():
    """Returns real-time laptop hardware telemetry and system metrics."""
    cpu_percent = psutil.cpu_percent(interval=0.05)
    mem = psutil.virtual_memory()
    root_path = "C:\\" if platform.system() == "Windows" else "/"
    disk = psutil.disk_usage(root_path)
    battery = psutil.sensors_battery()
    
    battery_info = {
        "has_battery": battery is not None,
        "percent": battery.percent if battery else 100,
        "power_plugged": battery.power_plugged if battery else True,
        "status": ("Charging" if battery.power_plugged else "On Battery") if battery else "AC Power"
    }
    
    return {
        "status": "online",
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "cpu": {"percent": cpu_percent, "cores": psutil.cpu_count(logical=True)},
        "ram": {"percent": mem.percent, "used_gb": round(mem.used / (1024 ** 3), 2), "total_gb": round(mem.total / (1024 ** 3), 2), "free_gb": round(mem.available / (1024 ** 3), 2)},
        "disk": {"percent": disk.percent, "used_gb": round(disk.used / (1024 ** 3), 2), "total_gb": round(disk.total / (1024 ** 3), 2), "free_gb": round(disk.free / (1024 ** 3), 2)},
        "battery": battery_info,
        "os": {"system": platform.system(), "release": platform.release(), "version": platform.version(), "arch": platform.machine()}
    }

# --- Version 7: Mobile to Laptop Remote Control & WebSocket Endpoints ---

from fastapi import WebSocket, WebSocketDisconnect
from backend.remote.laptop_agent import laptop_agent
from backend.remote.hub import remote_hub
from backend.security.auth import device_auth

class RemoteActionRequest(BaseModel):
    action: str = Field(..., description="Action: launch_app, lock_workstation, screenshot, volume, status")
    app_name: str = Field(default="vscode", description="App name for launch_app")
    volume_action: str = Field(default="toggle_mute", description="mute, unmute, toggle_mute, volume_up, volume_down")
    level: int = Field(default=50, description="Volume level 0-100")

class DevicePairRequest(BaseModel):
    device_id: str = Field(..., description="Unique client identifier")
    device_name: str = Field(default="Mobile Client", description="Human readable device name")


@app.post("/api/remote/execute", dependencies=[Depends(verify_api_key)])
async def execute_remote_action(req: RemoteActionRequest):
    """
    Executes a direct command on the laptop (launch VS Code, lock screen, adjust volume, screenshot).
    """
    logger.info(f"Received remote execution request: action='{req.action}'")
    result = await remote_hub.execute_remote_action(
        action=req.action,
        payload=req.model_dump()
    )
    return {"status": "success", "result": result}


@app.get("/api/remote/screenshot", dependencies=[Depends(verify_api_key)])
def get_remote_screenshot():
    """Captures and returns a live Base64 JPEG screenshot of the laptop display."""
    result = laptop_agent.capture_screenshot()
    return result


@app.get("/api/remote/status", dependencies=[Depends(verify_api_key)])
def get_remote_laptop_status():
    """Returns instant hardware & online state for 'is my laptop on?' queries."""
    status_data = laptop_agent.get_status_summary()
    return {"status": "online", "laptop": status_data}


@app.post("/api/remote/pair", dependencies=[Depends(verify_api_key)])
def pair_device(req: DevicePairRequest):
    """Pairs a mobile device and returns a cryptographic HMAC token."""
    secret = device_auth.generate_pairing_token(req.device_id, req.device_name)
    return {
        "status": "paired",
        "device_id": req.device_id,
        "token": secret
    }


@app.websocket("/ws/mobile")
async def websocket_mobile_endpoint(websocket: WebSocket, client_id: str = "mobile_client"):
    """
    Real-time bi-directional WebSocket connection for the Mobile Remote Deck.
    """
    await remote_hub.register_mobile(client_id, websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await remote_hub.handle_mobile_message(client_id, data)
    except WebSocketDisconnect:
        remote_hub.unregister_mobile(client_id)
    except Exception as e:
        logger.warning(f"WebSocket error for client '{client_id}': {e}")
        remote_hub.unregister_mobile(client_id)


# --- Version 8: Automation & Multi-Action Workflows Endpoints ---

from backend.automation.engine import workflow_engine
from backend.automation.models import (
    WorkflowDefinition,
    WorkflowCreateRequest,
    WorkflowTriggerRequest,
    WorkflowExecutionResult
)

@app.get("/api/workflows", dependencies=[Depends(verify_api_key)])
def list_workflows():
    """Returns all available preset and custom automation workflows."""
    workflows = workflow_engine.list_workflows()
    return {"status": "success", "workflows": [w.model_dump() for w in workflows]}


@app.get("/api/workflows/{workflow_id}", dependencies=[Depends(verify_api_key)])
def get_workflow_details(workflow_id: str):
    """Returns definition and steps for a specific workflow."""
    wf = workflow_engine.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Workflow '{workflow_id}' not found."
        )
    return {"status": "success", "workflow": wf.model_dump()}


@app.post("/api/workflows", dependencies=[Depends(verify_api_key)])
def create_or_update_workflow(req: WorkflowCreateRequest):
    """Creates or updates a custom multi-step automation workflow."""
    try:
        wf = workflow_engine.create_or_update_workflow(req)
        return {"status": "success", "workflow": wf.model_dump()}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.delete("/api/workflows/{workflow_id}", dependencies=[Depends(verify_api_key)])
def delete_custom_workflow(workflow_id: str):
    """Deletes a custom user workflow."""
    try:
        success = workflow_engine.delete_workflow(workflow_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Workflow '{workflow_id}' not found."
            )
        return {"status": "success", "message": f"Deleted workflow '{workflow_id}'."}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@app.post("/api/workflows/{workflow_id}/run", response_model=WorkflowExecutionResult, dependencies=[Depends(verify_api_key)])
def run_workflow_by_id(workflow_id: str):
    """Executes a workflow by its unique ID."""
    try:
        result = workflow_engine.execute_workflow(workflow_id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@app.post("/api/workflows/trigger", response_model=WorkflowExecutionResult, dependencies=[Depends(verify_api_key)])
def trigger_workflow_by_phrase(req: WorkflowTriggerRequest):
    """
    Matches user voice or text trigger phrase (e.g. 'Jarvis, I am starting work')
    and executes the corresponding automated workflow.
    """
    wf = workflow_engine.match_trigger(req.trigger)
    if not wf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No workflow matched trigger phrase: '{req.trigger}'"
        )
    result = workflow_engine.execute_workflow(wf.workflow_id)
    return result


# --- Version 9: Personal Knowledge & RAG REST Endpoints ---

from backend.knowledge.engine import knowledge_engine
from backend.knowledge.models import (
    RAGQueryRequest,
    RAGQueryResponse,
    DocumentIndexRequest
)

@app.post("/api/knowledge/query", response_model=RAGQueryResponse, dependencies=[Depends(verify_api_key)])
async def query_personal_knowledge(req: RAGQueryRequest):
    """
    Executes RAG semantic retrieval over personal documents (Resume, Projects, PDFs, Notes)
    and returns synthesized LLM answer with ground-truth citations.
    """
    try:
        response = await knowledge_engine.query_rag(
            query=req.query,
            category=req.category,
            top_k=req.top_k
        )
        return response
    except Exception as e:
        logger.error(f"Error in /api/knowledge/query: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Knowledge retrieval error: {str(e)}"
        )


@app.get("/api/knowledge/documents", dependencies=[Depends(verify_api_key)])
def list_knowledge_documents(category: str = None):
    """Lists all indexed knowledge documents with optional category filtering."""
    docs = knowledge_engine.list_documents(category=category)
    return {"status": "success", "documents": docs}


@app.get("/api/knowledge/documents/{doc_id}", dependencies=[Depends(verify_api_key)])
def get_knowledge_document_details(doc_id: int):
    """Returns details and chunk excerpts for a specific indexed document."""
    doc = knowledge_engine.get_document(doc_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {doc_id} not found."
        )
    return {"status": "success", "document": doc}


@app.delete("/api/knowledge/documents/{doc_id}", dependencies=[Depends(verify_api_key)])
def delete_knowledge_document(doc_id: int):
    """Deletes an indexed document and its vector chunks from the knowledge vault."""
    success = knowledge_engine.delete_document(doc_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {doc_id} not found."
        )
    return {"status": "success", "message": f"Deleted document ID {doc_id}."}


@app.post("/api/knowledge/index-file", dependencies=[Depends(verify_api_key)])
def index_knowledge_file(req: DocumentIndexRequest):
    """Indexes a document from a local file path or direct text content."""
    try:
        if req.file_path:
            doc = knowledge_engine.index_file(
                file_path=req.file_path,
                category=req.category,
                title=req.title
            )
        elif req.content:
            doc = knowledge_engine.index_text(
                title=req.title or "Untitled Note",
                content=req.content,
                category=req.category
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either 'file_path' or 'content' must be provided."
            )
        return {"status": "success", "document": doc}
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(fnf))
    except Exception as e:
        logger.error(f"Error indexing document: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@app.post("/api/knowledge/upload", dependencies=[Depends(verify_api_key)])
async def upload_knowledge_document(
    file: UploadFile = File(...),
    category: str = "project"
):
    """Uploads and indexes a document file (PDF, TXT, MD, Code)."""
    file_ext = os.path.splitext(file.filename)[1] or ".txt"
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as tmp:
            contents = await file.read()
            tmp.write(contents)
            temp_path = tmp.name

        doc = knowledge_engine.index_file(
            file_path=temp_path,
            category=category,
            title=os.path.splitext(file.filename)[0].replace("_", " ").title()
        )
        return {"status": "success", "document": doc}
    except Exception as e:
        logger.error(f"Error processing uploaded document: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


@app.post("/api/knowledge/scan-vault", dependencies=[Depends(verify_api_key)])
def scan_knowledge_vault():
    """Scans and synchronizes documents from the knowledge_vault folder."""
    indexed = knowledge_engine.scan_vault()
    return {"status": "success", "indexed_count": len(indexed), "documents": indexed}


# --- Version 10: Advanced Unified Gateway Endpoints ---

from backend.core.gateway import jarvis_gateway
from backend.core.models import (
    UnifiedInteractionRequest,
    UnifiedInteractionResponse,
    SystemOverviewResponse
)

@app.post("/api/gateway/interact", response_model=UnifiedInteractionResponse, dependencies=[Depends(verify_api_key)])
async def gateway_interact(req: UnifiedInteractionRequest):
    """
    Unified multi-modal Gateway endpoint.
    Processes queries across AI Brain, Memory, Tools, and Workflows with optional voice synthesis.
    """
    result = await jarvis_gateway.interact(
        text=req.text,
        session_id=req.session_id,
        synthesize_voice=req.synthesize_voice
    )
    return result


@app.post("/api/gateway/voice-interact", response_model=UnifiedInteractionResponse, dependencies=[Depends(verify_api_key)])
async def gateway_voice_interact(
    file: UploadFile = File(...),
    session_id: str = "voice"
):
    """
    Unified voice input endpoint:
    Audio recording upload -> Whisper STT -> Gateway Reasoning -> Edge-TTS Audio -> Response.
    """
    file_ext = os.path.splitext(file.filename)[1] or ".wav"
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=file_ext, delete=False) as tmp:
            contents = await file.read()
            tmp.write(contents)
            temp_path = tmp.name

        result = await jarvis_gateway.voice_interact(
            audio_file_path=temp_path,
            session_id=session_id
        )
        return result
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


@app.get("/api/gateway/system-summary", response_model=SystemOverviewResponse, dependencies=[Depends(verify_api_key)])
def get_system_summary():
    """
    Returns unified diagnostic overview across all subsystems (Hardware, Subsystems, Counts, Tools).
    """
    return jarvis_gateway.get_system_overview()






