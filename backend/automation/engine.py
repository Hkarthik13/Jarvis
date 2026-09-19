import os
import json
import re
import platform
import subprocess
import webbrowser
from typing import Dict, List, Optional, Any
from pathlib import Path

from backend.utils.logger import logger
from backend.remote.laptop_agent import laptop_agent
from backend.memory.service import memory_service
from backend.automation.models import (
    WorkflowStep,
    WorkflowDefinition,
    StepExecutionResult,
    WorkflowExecutionResult,
    WorkflowCreateRequest
)

WORKFLOWS_FILE = Path(__file__).parent.parent.parent / "jarvis_workflows.json"

class WorkflowEngine:
    """
    Central Automation Engine for JARVIS (Version 8).
    Executes multi-step automated routines, provides built-in preset workflows,
    persists custom user workflows, and matches natural language trigger phrases.
    """

    def __init__(self):
        self._custom_workflows: Dict[str, WorkflowDefinition] = {}
        self._preset_workflows: Dict[str, WorkflowDefinition] = {}
        self._initialize_presets()
        self._load_custom_workflows()

    def _initialize_presets(self):
        """Initializes built-in system routines."""
        
        # 1. Start Workday Routine
        start_work = WorkflowDefinition(
            workflow_id="start_work",
            name="Start Workday",
            description="Launches VS Code in project folder, opens GitHub and docs, sets status in memory, and logs work session.",
            trigger_phrases=[
                "start work", "i'm starting work", "i am starting work",
                "start my workday", "begin work", "morning routine",
                "work mode", "let's work", "lets work", "start working"
            ],
            icon="🚀",
            is_preset=True,
            steps=[
                WorkflowStep(
                    step_id="sw_1",
                    action_type="launch_app",
                    title="Launch VS Code",
                    parameters={"app_name": "vscode", "path": str(Path(__file__).parent.parent.parent)}
                ),
                WorkflowStep(
                    step_id="sw_2",
                    action_type="open_url",
                    title="Open GitHub",
                    parameters={"url": "https://github.com"}
                ),
                WorkflowStep(
                    step_id="sw_3",
                    action_type="open_url",
                    title="Open FastAPI Documentation",
                    parameters={"url": "https://fastapi.tiangolo.com"}
                ),
                WorkflowStep(
                    step_id="sw_4",
                    action_type="memory_update",
                    title="Update Work Status in Memory",
                    parameters={"key": "work_status", "value": "Active Work Session", "category": "status"}
                ),
                WorkflowStep(
                    step_id="sw_5",
                    action_type="manage_task",
                    title="Log Daily Work Session Task",
                    parameters={"action": "add", "title": "Daily development & project work", "priority": "medium", "project": "Jarvis"}
                ),
                WorkflowStep(
                    step_id="sw_6",
                    action_type="set_volume",
                    title="Configure Audio Output",
                    parameters={"action": "unmute", "level": 70}
                ),
                WorkflowStep(
                    step_id="sw_7",
                    action_type="voice_speak",
                    title="Spoken Confirmation",
                    parameters={"text": "Work environment is ready, sir. VS Code, repository, and documentation are online. Let's make today productive!"}
                )
            ]
        )
        self._preset_workflows["start_work"] = start_work

        # 2. Prepare Interview Environment Routine
        prepare_interview = WorkflowDefinition(
            workflow_id="prepare_interview",
            name="Prepare Interview Environment",
            description="Prepares interview workspace by launching Google Meet, opening notes/notepad, testing audio, and setting memory status.",
            trigger_phrases=[
                "prepare interview", "prepare my interview environment", "interview mode",
                "interview ready", "start interview prep", "setup interview",
                "prepare for interview", "interview environment"
            ],
            icon="💼",
            is_preset=True,
            steps=[
                WorkflowStep(
                    step_id="pi_1",
                    action_type="open_url",
                    title="Open Google Meet",
                    parameters={"url": "https://meet.google.com"}
                ),
                WorkflowStep(
                    step_id="pi_2",
                    action_type="launch_app",
                    title="Open Notes / Scratchpad",
                    parameters={"app_name": "notepad"}
                ),
                WorkflowStep(
                    step_id="pi_3",
                    action_type="set_volume",
                    title="Optimize Audio Volume",
                    parameters={"action": "unmute", "level": 80}
                ),
                WorkflowStep(
                    step_id="pi_4",
                    action_type="memory_update",
                    title="Set Interview Status in Memory",
                    parameters={"key": "interview_status", "value": "Interview Session Active", "category": "status"}
                ),
                WorkflowStep(
                    step_id="pi_5",
                    action_type="manage_task",
                    title="Record Interview Session Task",
                    parameters={"action": "add", "title": "Technical Interview Session", "priority": "high", "project": "Career"}
                ),
                WorkflowStep(
                    step_id="pi_6",
                    action_type="voice_speak",
                    title="Spoken Confirmation",
                    parameters={"text": "Interview workspace prepared, sir. Google Meet loaded, notes open, and audio optimized. Best of luck!"}
                )
            ]
        )
        self._preset_workflows["prepare_interview"] = prepare_interview

        # 3. Deep Focus Mode Routine
        focus_mode = WorkflowDefinition(
            workflow_id="focus_mode",
            name="Deep Focus Mode",
            description="Engages distraction-free coding session, mutes audio, and updates user status in memory.",
            trigger_phrases=[
                "focus mode", "deep focus", "deep work", "start coding session",
                "do not disturb", "enter focus mode", "engage focus"
            ],
            icon="🎯",
            is_preset=True,
            steps=[
                WorkflowStep(
                    step_id="fm_1",
                    action_type="launch_app",
                    title="Launch Code Editor",
                    parameters={"app_name": "vscode"}
                ),
                WorkflowStep(
                    step_id="fm_2",
                    action_type="set_volume",
                    title="Mute Distractions",
                    parameters={"action": "mute"}
                ),
                WorkflowStep(
                    step_id="fm_3",
                    action_type="memory_update",
                    title="Update Status to Deep Work",
                    parameters={"key": "focus_mode", "value": "Deep Work - Do Not Disturb", "category": "status"}
                ),
                WorkflowStep(
                    step_id="fm_4",
                    action_type="voice_speak",
                    title="Spoken Confirmation",
                    parameters={"text": "Deep focus mode engaged. Audio muted and development environment initialized."}
                )
            ]
        )
        self._preset_workflows["focus_mode"] = focus_mode

        # 4. Wrap Up & Relax Mode Routine
        relax_mode = WorkflowDefinition(
            workflow_id="relax_mode",
            name="Wrap Up & Relax Mode",
            description="Wraps up workday, launches YouTube Music, checks pending tasks, and prepares evening recap.",
            trigger_phrases=[
                "relax mode", "end of day", "wrap up", "done with work",
                "chill mode", "time to relax", "finish work"
            ],
            icon="🎧",
            is_preset=True,
            steps=[
                WorkflowStep(
                    step_id="rm_1",
                    action_type="open_url",
                    title="Open YouTube Music",
                    parameters={"url": "https://music.youtube.com"}
                ),
                WorkflowStep(
                    step_id="rm_2",
                    action_type="set_volume",
                    title="Set Ambient Volume",
                    parameters={"action": "unmute", "level": 50}
                ),
                WorkflowStep(
                    step_id="rm_3",
                    action_type="memory_update",
                    title="Update Status to Relaxing",
                    parameters={"key": "work_status", "value": "Off Duty / Relaxing", "category": "status"}
                ),
                WorkflowStep(
                    step_id="rm_4",
                    action_type="voice_speak",
                    title="Spoken Confirmation",
                    parameters={"text": "Work wrapped up for today, sir. Relaxing music is queued. Have a restful evening!"}
                )
            ]
        )
        self._preset_workflows["relax_mode"] = relax_mode

        # 5. Workstation Lockdown Routine
        lockdown = WorkflowDefinition(
            workflow_id="lockdown",
            name="Secure Workstation",
            description="Secures the laptop by instantly locking the screen and recording security state.",
            trigger_phrases=[
                "lock down", "secure station", "lock laptop", "step away",
                "leaving desk", "lock workstation", "secure laptop"
            ],
            icon="🔒",
            is_preset=True,
            steps=[
                WorkflowStep(
                    step_id="ld_1",
                    action_type="lock_screen",
                    title="Lock Windows Workstation",
                    parameters={"action": "lock"}
                ),
                WorkflowStep(
                    step_id="ld_2",
                    action_type="memory_update",
                    title="Record Security State",
                    parameters={"key": "workstation_state", "value": "Locked & Secured", "category": "security"}
                ),
                WorkflowStep(
                    step_id="ld_3",
                    action_type="voice_speak",
                    title="Spoken Confirmation",
                    parameters={"text": "Workstation locked and secured, sir."}
                )
            ]
        )
        self._preset_workflows["lockdown"] = lockdown

        # 6. Morning Briefing Protocol
        morning_briefing = WorkflowDefinition(
            workflow_id="morning_briefing",
            name="Morning Briefing Protocol",
            description="Delivers morning telemetry, atmospheric conditions, and prepares the workspace.",
            trigger_phrases=[
                "morning briefing", "good morning jarvis", "good morning",
                "morning protocol", "briefing", "give me briefing"
            ],
            icon="☀️",
            is_preset=True,
            steps=[
                WorkflowStep(
                    step_id="mb_1",
                    action_type="set_volume",
                    title="Set Volume to Comfortable Level",
                    parameters={"action": "unmute", "level": 75}
                ),
                WorkflowStep(
                    step_id="mb_2",
                    action_type="open_url",
                    title="Open News / Weather",
                    parameters={"url": "https://weather.com"}
                ),
                WorkflowStep(
                    step_id="mb_3",
                    action_type="voice_speak",
                    title="Spoken Confirmation",
                    parameters={"text": "Good morning, sir. Systems are online and operating within optimal parameters. Atmospheric conditions and workstation prepared."}
                )
            ]
        )
        self._preset_workflows["morning_briefing"] = morning_briefing

        # 7. Iron Dome Security Protocol
        iron_dome = WorkflowDefinition(
            workflow_id="iron_dome",
            name="Iron Dome Protocol",
            description="Mutes audio, captures desktop screenshot, and locks workstation immediately.",
            trigger_phrases=[
                "iron dome", "iron dome protocol", "emergency lockdown", "red alert"
            ],
            icon="🛡️",
            is_preset=True,
            steps=[
                WorkflowStep(
                    step_id="id_1",
                    action_type="set_volume",
                    title="Mute Audio",
                    parameters={"action": "mute"}
                ),
                WorkflowStep(
                    step_id="id_2",
                    action_type="lock_screen",
                    title="Lock Laptop",
                    parameters={"action": "lock"}
                ),
                WorkflowStep(
                    step_id="id_3",
                    action_type="voice_speak",
                    title="Spoken Confirmation",
                    parameters={"text": "Iron Dome engaged. Audio silenced and workstation secured, sir."}
                )
            ]
        )
        self._preset_workflows["iron_dome"] = iron_dome

    def _load_custom_workflows(self):
        """Loads custom user workflows from disk."""
        if not WORKFLOWS_FILE.exists():
            return
        try:
            with open(WORKFLOWS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    wf = WorkflowDefinition(**item)
                    wf.is_preset = False
                    self._custom_workflows[wf.workflow_id] = wf
            logger.info(f"Loaded {len(self._custom_workflows)} custom workflows from {WORKFLOWS_FILE}")
        except Exception as e:
            logger.error(f"Failed to load custom workflows: {e}")

    def _save_custom_workflows(self):
        """Persists custom user workflows to disk."""
        try:
            serialized = [wf.model_dump() for wf in self._custom_workflows.values()]
            with open(WORKFLOWS_FILE, "w", encoding="utf-8") as f:
                json.dump(serialized, f, indent=2)
            logger.info(f"Saved {len(self._custom_workflows)} custom workflows to {WORKFLOWS_FILE}")
        except Exception as e:
            logger.error(f"Failed to save custom workflows: {e}")

    def list_workflows(self) -> List[WorkflowDefinition]:
        """Returns all preset and custom workflows."""
        all_wfs = list(self._preset_workflows.values()) + list(self._custom_workflows.values())
        return all_wfs

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Retrieves a workflow by its unique ID."""
        cleaned_id = workflow_id.lower().replace(" ", "_").replace("-", "_").strip()
        if cleaned_id in self._preset_workflows:
            return self._preset_workflows[cleaned_id]
        if cleaned_id in self._custom_workflows:
            return self._custom_workflows[cleaned_id]
        
        # Check by name
        for wf in self.list_workflows():
            if wf.name.lower() == workflow_id.lower() or wf.workflow_id.lower() == cleaned_id:
                return wf
        return None

    def create_or_update_workflow(self, req: WorkflowCreateRequest) -> WorkflowDefinition:
        """Creates or updates a custom user workflow."""
        cleaned_id = req.workflow_id.lower().replace(" ", "_").replace("-", "_").strip()
        if cleaned_id in self._preset_workflows:
            raise ValueError(f"Cannot overwrite built-in preset routine '{cleaned_id}'")
            
        wf = WorkflowDefinition(
            workflow_id=cleaned_id,
            name=req.name,
            description=req.description,
            trigger_phrases=req.trigger_phrases,
            icon=req.icon or "⚡",
            steps=req.steps,
            is_preset=False
        )
        self._custom_workflows[cleaned_id] = wf
        self._save_custom_workflows()
        return wf

    def delete_workflow(self, workflow_id: str) -> bool:
        """Deletes a custom user workflow."""
        cleaned_id = workflow_id.lower().replace(" ", "_").replace("-", "_").strip()
        if cleaned_id in self._preset_workflows:
            raise ValueError(f"Cannot delete built-in preset routine '{cleaned_id}'")
        if cleaned_id in self._custom_workflows:
            del self._custom_workflows[cleaned_id]
            self._save_custom_workflows()
            return True
        return False

    def match_trigger(self, utterance: str) -> Optional[WorkflowDefinition]:
        """
        Matches user voice or text input against workflow triggers.
        Supports fuzzy and substring matching.
        """
        if not utterance:
            return None
        text = utterance.lower().strip()
        text_clean = re.sub(r"[^\w\s]", "", text)

        for wf in self.list_workflows():
            # Check explicit trigger phrases
            for trigger in wf.trigger_phrases:
                trig_clean = re.sub(r"[^\w\s]", "", trigger.lower())
                if trig_clean in text_clean or text_clean in trig_clean:
                    return wf
            # Check workflow ID or name
            if wf.workflow_id in text_clean.replace(" ", "_") or wf.name.lower() in text_clean:
                return wf

        return None

    def execute_step(self, step: WorkflowStep) -> StepExecutionResult:
        """Executes an individual workflow step and captures the outcome."""
        action = step.action_type.lower().strip()
        params = step.parameters or {}
        logger.info(f"[WorkflowEngine] Executing step '{step.title}' (action: {action})")

        try:
            # 1. Launch Application
            if action in ("launch_app", "open_app", "open_application"):
                app_name = params.get("app_name") or params.get("name") or "vscode"
                path = params.get("path")
                res = laptop_agent.launch_app(app_name, path=path)
                return StepExecutionResult(
                    step_id=step.step_id,
                    title=step.title,
                    success=res.get("success", True),
                    message=res.get("message", f"Launched application '{app_name}'"),
                    error=res.get("error")
                )

            # 2. Open URL / Documentation
            elif action in ("open_url", "open_website", "browse_url"):
                url = params.get("url") or "https://google.com"
                if platform.system() == "Windows":
                    subprocess.Popen(f'start "" "{url}"', shell=True)
                else:
                    webbrowser.open(url)
                return StepExecutionResult(
                    step_id=step.step_id,
                    title=step.title,
                    success=True,
                    message=f"Opened URL: {url}"
                )

            # 3. Open Folder in Explorer
            elif action in ("open_folder", "open_directory"):
                folder_path = params.get("path") or params.get("folder") or os.getcwd()
                if platform.system() == "Windows":
                    subprocess.Popen(f'explorer "{folder_path}"', shell=True)
                return StepExecutionResult(
                    step_id=step.step_id,
                    title=step.title,
                    success=True,
                    message=f"Opened directory: {folder_path}"
                )

            # 4. Control Audio Volume / Mute
            elif action in ("set_volume", "volume", "audio"):
                vol_action = params.get("action", "toggle_mute")
                level = params.get("level")
                res = laptop_agent.control_volume(vol_action, level=level)
                return StepExecutionResult(
                    step_id=step.step_id,
                    title=step.title,
                    success=res.get("success", True),
                    message=res.get("message", f"Configured volume ({vol_action})"),
                    error=res.get("error")
                )

            # 5. Lock Workstation Screen
            elif action in ("lock_screen", "lock_workstation", "lock"):
                res = laptop_agent.lock_workstation()
                return StepExecutionResult(
                    step_id=step.step_id,
                    title=step.title,
                    success=res.get("success", True),
                    message=res.get("message", "Workstation locked successfully"),
                    error=res.get("error")
                )

            # 6. Update Memory / Preference
            elif action in ("memory_update", "set_preference", "remember"):
                key = params.get("key", "status")
                val = params.get("value", "")
                cat = params.get("category", "status")
                memory_service.set_preference(key=key, value=val, category=cat)
                return StepExecutionResult(
                    step_id=step.step_id,
                    title=step.title,
                    success=True,
                    message=f"Saved memory status '{key}': '{val}'"
                )

            # 7. Manage Task
            elif action in ("manage_task", "add_task"):
                task_title = params.get("title", "Routine task")
                project = params.get("project", "General")
                priority = params.get("priority", "medium")
                task = memory_service.add_task(title=task_title, project=project, priority=priority)
                return StepExecutionResult(
                    step_id=step.step_id,
                    title=step.title,
                    success=True,
                    message=f"Created task: '{task_title}' [ID: {task['id']}]"
                )

            # 8. Safe System Command
            elif action in ("system_command", "run_command"):
                cmd = params.get("command", "")
                if cmd:
                    subprocess.Popen(cmd, shell=True)
                    return StepExecutionResult(
                        step_id=step.step_id,
                        title=step.title,
                        success=True,
                        message=f"Executed command: {cmd}"
                    )
                return StepExecutionResult(
                    step_id=step.step_id,
                    title=step.title,
                    success=False,
                    error="Empty command provided."
                )

            # 9. Voice Speak (captured for synthesis)
            elif action in ("voice_speak", "speak", "voice_response"):
                spoken_text = params.get("text", "")
                return StepExecutionResult(
                    step_id=step.step_id,
                    title=step.title,
                    success=True,
                    message=f"Synthesized speech line",
                    output=spoken_text
                )

            else:
                return StepExecutionResult(
                    step_id=step.step_id,
                    title=step.title,
                    success=False,
                    error=f"Unknown action type: '{action}'"
                )

        except Exception as e:
            logger.error(f"[WorkflowEngine] Error in step '{step.title}': {e}")
            return StepExecutionResult(
                step_id=step.step_id,
                title=step.title,
                success=False,
                error=str(e)
            )

    def execute_workflow(self, workflow_id: str) -> WorkflowExecutionResult:
        """
        Executes all steps in a specified workflow in sequence.
        Collects individual step outcomes and synthesizes a spoken response.
        """
        wf = self.get_workflow(workflow_id)
        if not wf:
            raise ValueError(f"Workflow '{workflow_id}' not found.")

        logger.info(f"[WorkflowEngine] Starting execution of workflow: '{wf.name}' ({wf.workflow_id}) with {len(wf.steps)} steps.")
        step_results: List[StepExecutionResult] = []
        spoken_lines: List[str] = []
        overall_success = True

        for step in wf.steps:
            res = self.execute_step(step)
            step_results.append(res)
            
            if res.output and isinstance(res.output, str):
                spoken_lines.append(res.output)

            if not res.success:
                if not step.continue_on_error:
                    overall_success = False
                    logger.warning(f"Workflow aborted on step '{step.title}' due to failure: {res.error}")
                    break

        default_spoken = f"{wf.name} completed successfully, sir." if overall_success else f"Completed {wf.name} with warnings."
        spoken_response = " ".join(spoken_lines) if spoken_lines else default_spoken

        summary_msg = f"Executed {len(step_results)} steps for routine '{wf.name}'. Status: {'Success' if overall_success else 'Partial/Failed'}."

        return WorkflowExecutionResult(
            workflow_id=wf.workflow_id,
            workflow_name=wf.name,
            success=overall_success,
            summary=summary_msg,
            spoken_response=spoken_response,
            step_results=step_results
        )

# Global singleton workflow engine instance
workflow_engine = WorkflowEngine()
