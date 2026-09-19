import os
import tempfile
import base64
import platform
import datetime
import psutil
from typing import Dict, Any, List, Optional

from backend.utils.logger import logger
from backend.config import settings
from backend.ai.client import ai_client
from backend.ai.registry import registry
from backend.memory.service import memory_service
from backend.memory.database import SessionLocal
from backend.knowledge.engine import knowledge_engine
from backend.knowledge.models import DocumentSource, DocumentChunk, CitationItem
from backend.automation.engine import workflow_engine
from backend.remote.laptop_agent import laptop_agent
from backend.voice.stt import transcribe_audio
from backend.voice.tts import synthesize_speech
from backend.core.models import (
    UnifiedInteractionRequest,
    UnifiedInteractionResponse,
    SystemOverviewResponse
)

class JarvisGatewayOrchestrator:
    """
    Central Gateway Orchestrator for JARVIS (Version 10 — Advanced Architecture).
    Coordinates AI Brain (Groq LLM), Memory & RAG Vault, Tools Engine & Laptop Agent,
    and Voice Synthesis into a unified multi-modal pipeline.
    """

    async def interact(
        self,
        text: str,
        session_id: str = "default",
        synthesize_voice: bool = False
    ) -> UnifiedInteractionResponse:
        """
        Executes unified query processing across AI Brain, Memory, Tools, and Workflows.
        """
        if not text or not text.strip():
            return UnifiedInteractionResponse(
                query="",
                response_text="How may I assist you today, sir?",
                session_id=session_id
            )

        query_clean = text.strip()
        logger.info(f"[Gateway V10] Processing interaction query: '{query_clean}' (Session: {session_id})")
        
        # Save user message to SQLite memory
        memory_service.save_conversation(role="user", content=query_clean, session_id=session_id)

        workflow_triggered_name = None
        executed_tools = []
        citations_found: List[CitationItem] = []
        response_text = ""

        # 1. Fast-path: Check natural language automation routine triggers (e.g. "I'm starting work")
        matched_wf = workflow_engine.match_trigger(query_clean)
        if matched_wf:
            logger.info(f"[Gateway V10] Natural trigger matched workflow: '{matched_wf.name}' ({matched_wf.workflow_id})")
            wf_result = workflow_engine.execute_workflow(matched_wf.workflow_id)
            workflow_triggered_name = matched_wf.name
            executed_tools.append(f"workflow:{matched_wf.workflow_id}")
            response_text = wf_result.spoken_response
            if not response_text:
                response_text = f"Executed {matched_wf.name} routine successfully on your laptop."
        
        else:
            fast_response = self._try_local_fast_path(query_clean)
            if fast_response:
                response_text = fast_response["response_text"]
                executed_tools.extend(fast_response.get("tools_executed", []))
                citations_found = fast_response.get("citations", [])
            else:
                # 2. Multi-turn AI Brain reasoning loop with recent context & RAG
                # Fetch recent conversation turns (up to 6 turns) so dialogue flows organically
                recent_history = memory_service.get_conversation_history(session_id=session_id, limit=6)
                chat_history = []
                for turn in recent_history[:-1]:  # exclude the query we just persisted
                    if turn.get("role") in ("user", "assistant") and turn.get("content"):
                        chat_history.append({"role": turn["role"], "content": turn["content"]})
                
                chat_history.append({"role": "user", "content": query_clean})

                try:
                    response_text = await ai_client.generate_chat_response(chat_history)
                except Exception as e:
                    logger.error(f"[Gateway V10] AI Client execution error: {e}")
                    local_answer = self._knowledge_fallback_answer(query_clean)
                    response_text = local_answer["response_text"] or f"I encountered an error processing your request: {str(e)}"
                    citations_found = local_answer["citations"]

                # 3. Check if query searched knowledge vault chunks to attach citations
                if not citations_found:
                    found_cites = knowledge_engine.search_chunks(query_clean, top_k=3)
                    if found_cites and found_cites[0].relevance_score > 0.25:
                        citations_found = found_cites

        # Save assistant turn to memory
        memory_service.save_conversation(role="assistant", content=response_text, session_id=session_id)

        # 4. Optional Voice Audio Synthesis (Edge-TTS)
        audio_base64 = None
        if synthesize_voice and response_text:
            try:
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_out:
                    temp_mp3_path = tmp_out.name

                await synthesize_speech(response_text, temp_mp3_path)
                with open(temp_mp3_path, "rb") as audio_file:
                    audio_base64 = base64.b64encode(audio_file.read()).decode("utf-8")

                if os.path.exists(temp_mp3_path):
                    os.remove(temp_mp3_path)
            except Exception as tts_err:
                logger.warning(f"[Gateway V10] Voice synthesis fallback warning: {tts_err}")

        return UnifiedInteractionResponse(
            query=query_clean,
            response_text=response_text,
            audio_base64=audio_base64,
            citations=citations_found,
            tools_executed=executed_tools,
            workflow_triggered=workflow_triggered_name,
            session_id=session_id
        )

    def _try_local_fast_path(self, query: str) -> Optional[Dict[str, Any]]:
        """Answers obvious local intents and greetings without paying cloud LLM latency."""
        q = query.lower().strip()

        # 1. Instant Conversational Greetings (0ms latency in English, Tanglish, Tamil)
        is_tanglish_greeting = any(w == q or q.startswith(w + " ") for w in ("vanakkam", "vanakkam jarvis", "epdi irukka", "epdi irukinga", "sollu jarvis", "enna paas"))
        if is_tanglish_greeting:
            return {
                "response_text": "Vanakkam boss! Naan super-ah irukken. Sollinga, iniki namma enna plan panrom?",
                "tools_executed": ["local:conversational_greeting"],
            }
            
        if q in ("வணக்கம்", "வணக்கம் ஜார்விஸ்", "எப்படி இருக்கிறீர்கள்"):
            return {
                "response_text": "வணக்கம் சார்! நான் சிறப்பாக செயல்படுகிறேன். உங்களுக்கு இன்று எவ்வாறு உதவலாம்?",
                "tools_executed": ["local:conversational_greeting"],
            }

        # 2. System diagnostics fast path
        if any(phrase in q for phrase in ("system summary", "diagnostics", "jarvis status", "system status", "run diagnostics", "full diagnostics")):
            overview = self.get_system_overview()
            return {
                "response_text": (
                    f"Diagnostics complete, sir. All core subsystems nominal. Arc Reactor and CPU load at {overview.hardware['cpu_percent']}%, "
                    f"Memory utilization at {overview.hardware['ram_percent']}%, storage capacity at {overview.hardware['disk_percent']}%. "
                    f"{overview.counts['registered_tools']} tactical tools active, "
                    f"and {overview.counts['knowledge_documents']} classified knowledge documents indexed in your vault."
                ),
                "tools_executed": ["local:system_overview"],
            }

        # 3. Hardware telemetry & battery fast path
        if any(term in q for term in ("battery", "charging", "laptop status", "is my laptop on", "cpu", "ram", "disk", "power level")):
            parts = []
            tools = []
            if "cpu" in q or "laptop status" in q or "system" in q or "is my laptop on" in q:
                parts.append(registry.execute_tool("get_cpu_usage", {}))
                tools.append("get_cpu_usage")
            if "ram" in q or "memory usage" in q or "laptop status" in q or "system" in q:
                parts.append(registry.execute_tool("get_ram_usage", {}))
                tools.append("get_ram_usage")
            if "disk" in q or "storage" in q or "laptop status" in q or "system" in q:
                parts.append(registry.execute_tool("get_disk_usage", {}))
                tools.append("get_disk_usage")
            if "battery" in q or "charging" in q or "power" in q or "laptop status" in q or "is my laptop on" in q:
                parts.append(registry.execute_tool("get_battery_status", {}))
                tools.append("get_battery_status")
            if parts:
                return {"response_text": f"Telemetry report, sir: {' '.join(parts)}", "tools_executed": tools}

        if any(term in q for term in ("time", "date", "day today")):
            return {
                "response_text": registry.execute_tool("get_current_time_date", {}),
                "tools_executed": ["get_current_time_date"],
            }

        if self._looks_like_knowledge_query(q):
            local_answer = self._knowledge_fallback_answer(query)
            if local_answer["citations"]:
                local_answer["tools_executed"] = ["query_personal_knowledge"]
                return local_answer

        return None

    def _looks_like_knowledge_query(self, q: str) -> bool:
        knowledge_terms = (
            "resume", "project", "knowledge", "document", "vault", "portfolio",
            "technologies", "tech stack", "ai resume analyzer"
        )
        return any(term in q for term in knowledge_terms)

    def _knowledge_fallback_answer(self, query: str) -> Dict[str, Any]:
        citations = knowledge_engine.search_chunks(query, top_k=4)
        if citations and citations[0].relevance_score > 0.15:
            return {
                "response_text": knowledge_engine.synthesize_local_answer(query, citations),
                "citations": citations,
            }
        return {"response_text": "", "citations": []}

    async def voice_interact(
        self,
        audio_file_path: str,
        session_id: str = "voice"
    ) -> UnifiedInteractionResponse:
        """
        Multi-modal Voice Pipeline:
        Audio Upload -> Whisper STT -> Unified Gateway Reasoning -> Edge-TTS Audio -> Base64 MP3.
        """
        logger.info(f"[Gateway V10] Transcribing voice input from: {audio_file_path}")
        transcribed_text = await transcribe_audio(audio_file_path)
        if not transcribed_text.strip():
            return UnifiedInteractionResponse(
                query="",
                response_text="I couldn't hear any speech in the audio recording.",
                session_id=session_id
            )

        return await self.interact(
            text=transcribed_text,
            session_id=session_id,
            synthesize_voice=True
        )

    def get_system_overview(self) -> SystemOverviewResponse:
        """
        Aggregates diagnostics and health telemetry across all Version 1-10 subsystems.
        """
        # Hardware Telemetry
        cpu_pct = psutil.cpu_percent(interval=0.02)
        mem = psutil.virtual_memory()
        root_path = "C:\\" if platform.system() == "Windows" else "/"
        disk = psutil.disk_usage(root_path)
        battery = psutil.sensors_battery()

        battery_data = {
            "has_battery": battery is not None,
            "percent": battery.percent if battery else 100,
            "power_plugged": battery.power_plugged if battery else True,
            "status": ("Charging" if battery.power_plugged else "On Battery") if battery else "AC Power"
        }

        # Database Entity Counts
        with SessionLocal() as db:
            doc_count = db.query(DocumentSource).count()
            chunk_count = db.query(DocumentChunk).count()

        all_memories = memory_service.list_all_memories()
        all_tasks = memory_service.list_tasks()
        all_workflows = workflow_engine.list_workflows()

        registered_tools = list(registry._tools.keys())
        preset_workflows = [w.name for w in all_workflows if w.is_preset]

        subsystems = {
            "ai_brain_groq": bool(settings.groq_api_key and settings.groq_api_key != "your_groq_api_key_here"),
            "memory_sqlite": True,
            "rag_knowledge_vault": doc_count > 0,
            "laptop_agent_windows": platform.system() == "Windows",
            "automation_engine": len(all_workflows) > 0,
            "voice_whisper_tts": True,
        }

        return SystemOverviewResponse(
            version="10.0.0",
            app_name="JARVIS Advanced AI Assistant",
            status="online",
            timestamp=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            host_os=f"{platform.system()} {platform.release()} ({platform.machine()})",
            hardware={
                "cpu_percent": cpu_pct,
                "cores": psutil.cpu_count(logical=True),
                "ram_percent": mem.percent,
                "ram_used_gb": round(mem.used / (1024 ** 3), 2),
                "ram_total_gb": round(mem.total / (1024 ** 3), 2),
                "disk_percent": disk.percent,
                "disk_free_gb": round(disk.free / (1024 ** 3), 2),
                "battery": battery_data
            },
            subsystems=subsystems,
            counts={
                "memory_facts": len(all_memories),
                "tasks": len(all_tasks),
                "knowledge_documents": doc_count,
                "knowledge_chunks": chunk_count,
                "workflows": len(all_workflows),
                "registered_tools": len(registered_tools)
            },
            registered_tools=registered_tools,
            preset_workflows=preset_workflows
        )

# Global singleton Gateway instance
jarvis_gateway = JarvisGatewayOrchestrator()
