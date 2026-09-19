import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from backend.knowledge.models import CitationItem

class UnifiedInteractionRequest(BaseModel):
    text: str = Field(..., description="User input text or command")
    session_id: str = Field(default="default", description="Conversation session identifier")
    synthesize_voice: bool = Field(default=False, description="Whether to generate MP3 audio stream")
    category_hint: Optional[str] = Field(default=None, description="Optional intent category hint")

class UnifiedInteractionResponse(BaseModel):
    query: str
    response_text: str
    audio_base64: Optional[str] = None
    citations: List[CitationItem] = Field(default_factory=list)
    tools_executed: List[str] = Field(default_factory=list)
    workflow_triggered: Optional[str] = None
    session_id: str = "default"
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

class SystemOverviewResponse(BaseModel):
    version: str = "10.0.0"
    app_name: str = "JARVIS Advanced AI Assistant"
    status: str = "online"
    timestamp: str
    host_os: str
    hardware: Dict[str, Any]
    subsystems: Dict[str, bool]
    counts: Dict[str, int]
    registered_tools: List[str]
    preset_workflows: List[str]
