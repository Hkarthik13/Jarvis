from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

class WorkflowStep(BaseModel):
    step_id: str = Field(..., description="Unique step identifier")
    action_type: str = Field(..., description="Type of action: launch_app, open_url, open_folder, system_command, set_volume, memory_update, manage_task, voice_speak, lock_screen")
    title: str = Field(..., description="Human readable description of the step")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Arguments passed to the action executor")
    continue_on_error: bool = Field(default=True, description="Whether pipeline proceeds if this step fails")

class WorkflowDefinition(BaseModel):
    workflow_id: str = Field(..., description="Unique workflow identifier (e.g. 'start_work')")
    name: str = Field(..., description="Display title (e.g. 'Start Workday')")
    description: str = Field(default="", description="Summary of what the workflow performs")
    trigger_phrases: List[str] = Field(default_factory=list, description="Voice trigger phrases")
    icon: str = Field(default="⚡", description="Emoji or icon for UI deck")
    steps: List[WorkflowStep] = Field(default_factory=list, description="Ordered execution steps")
    is_preset: bool = Field(default=False, description="True if built-in system routine")

class StepExecutionResult(BaseModel):
    step_id: str
    title: str
    success: bool
    message: str = ""
    error: Optional[str] = None
    output: Any = None

class WorkflowExecutionResult(BaseModel):
    workflow_id: str
    workflow_name: str
    success: bool
    summary: str
    spoken_response: str
    step_results: List[StepExecutionResult] = Field(default_factory=list)

class WorkflowTriggerRequest(BaseModel):
    trigger: str = Field(..., description="Voice or text trigger phrase (e.g. 'Jarvis, I am starting work')")

class WorkflowCreateRequest(BaseModel):
    workflow_id: str = Field(..., description="Unique workflow id")
    name: str = Field(..., description="Workflow title")
    description: str = Field(default="", description="Workflow description")
    trigger_phrases: List[str] = Field(default_factory=list, description="Trigger phrases")
    icon: str = Field(default="⚡", description="Display icon")
    steps: List[WorkflowStep] = Field(default_factory=list, description="Steps")
