from typing import Any, Dict, List
from backend.ai.registry import BaseTool, registry
from backend.automation.engine import workflow_engine
from backend.automation.models import WorkflowCreateRequest, WorkflowStep
from backend.utils.logger import logger

class RunAutomationWorkflowTool(BaseTool):
    @property
    def name(self) -> str:
        return "run_automation_workflow"

    @property
    def description(self) -> str:
        return (
            "Executes an automated multi-step routine or workflow on the user's laptop. "
            "Available preset routines include: 'start_work' (opens VS Code, docs, github, status), "
            "'prepare_interview' (opens Google Meet, notes, sets audio, status), 'focus_mode' (deep work, IDE, mute), "
            "'relax_mode' (youtube music, evening recap), and 'lockdown' (secure workstation). "
            "Use whenever the user says 'I am starting work', 'prepare my interview environment', "
            "'focus mode', 'relax mode', or requests a multi-step routine."
        )

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "workflow_name_or_id": {
                            "type": "string",
                            "description": "ID or name of the workflow to run (e.g. 'start_work', 'prepare_interview', 'focus_mode', 'relax_mode', 'lockdown')"
                        }
                    },
                    "required": ["workflow_name_or_id"]
                }
            }
        }

    def validate_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        name_or_id = args.get("workflow_name_or_id") or args.get("workflow_id") or args.get("name") or "start_work"
        return {"workflow_name_or_id": str(name_or_id).strip()}

    def execute(self, args: Dict[str, Any]) -> Any:
        target = args["workflow_name_or_id"]
        wf = workflow_engine.get_workflow(target)
        if not wf:
            # Try trigger matching
            wf = workflow_engine.match_trigger(target)
            
        if not wf:
            available = [w.workflow_id for w in workflow_engine.list_workflows()]
            return f"Workflow '{target}' not found. Available routines: {', '.join(available)}"

        result = workflow_engine.execute_workflow(wf.workflow_id)
        step_summaries = [f"- {s.title}: {'✅' if s.success else '❌'} {s.message or s.error}" for s in result.step_results]
        
        return (
            f"Routine '{result.workflow_name}' executed. "
            f"Spoken Response: \"{result.spoken_response}\"\n"
            f"Step Details:\n" + "\n".join(step_summaries)
        )


class ListAvailableWorkflowsTool(BaseTool):
    @property
    def name(self) -> str:
        return "list_available_workflows"

    @property
    def description(self) -> str:
        return (
            "Lists all available automated workflows and routines (both built-in presets and user custom routines) "
            "with their trigger phrases and descriptions."
        )

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }

    def validate_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return {}

    def execute(self, args: Dict[str, Any]) -> Any:
        workflows = workflow_engine.list_workflows()
        output = [f"Found {len(workflows)} automated routines:"]
        for w in workflows:
            triggers = f" (Triggers: {', '.join(w.trigger_phrases[:3])})" if w.trigger_phrases else ""
            output.append(f"{w.icon} `{w.workflow_id}` - **{w.name}**: {w.description}{triggers} [{len(w.steps)} steps]")
        return "\n".join(output)


class CreateAutomationWorkflowTool(BaseTool):
    @property
    def name(self) -> str:
        return "create_automation_workflow"

    @property
    def description(self) -> str:
        return (
            "Creates a new custom multi-action automation workflow / routine for JARVIS. "
            "Supports step actions: 'launch_app', 'open_url', 'open_folder', 'set_volume', 'memory_update', 'manage_task', 'lock_screen', 'voice_speak'."
        )

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {
                            "type": "string",
                            "description": "Unique identifier for routine, e.g. 'study_mode'"
                        },
                        "name": {
                            "type": "string",
                            "description": "Display name of workflow, e.g. 'Study Session'"
                        },
                        "description": {
                            "type": "string",
                            "description": "Summary of what this routine does"
                        },
                        "trigger_phrases": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Phrases that will trigger this workflow"
                        },
                        "steps": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "step_id": {"type": "string"},
                                    "action_type": {"type": "string"},
                                    "title": {"type": "string"},
                                    "parameters": {"type": "object"}
                                },
                                "required": ["step_id", "action_type", "title"]
                            },
                            "description": "List of ordered step actions"
                        }
                    },
                    "required": ["workflow_id", "name", "steps"]
                }
            }
        }

    def validate_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if not args.get("workflow_id"):
            raise ValueError("Parameter 'workflow_id' is required.")
        if not args.get("name"):
            raise ValueError("Parameter 'name' is required.")
        if not args.get("steps") or not isinstance(args.get("steps"), list):
            raise ValueError("Parameter 'steps' must be a non-empty list.")
        return args

    def execute(self, args: Dict[str, Any]) -> Any:
        steps = []
        for idx, s in enumerate(args["steps"]):
            steps.append(WorkflowStep(
                step_id=s.get("step_id", f"step_{idx+1}"),
                action_type=s.get("action_type", "open_url"),
                title=s.get("title", f"Step {idx+1}"),
                parameters=s.get("parameters", {})
            ))

        req = WorkflowCreateRequest(
            workflow_id=args["workflow_id"],
            name=args["name"],
            description=args.get("description", ""),
            trigger_phrases=args.get("trigger_phrases", []),
            icon=args.get("icon", "⚡"),
            steps=steps
        )
        created = workflow_engine.create_or_update_workflow(req)
        return f"Successfully created custom workflow '{created.name}' (ID: `{created.workflow_id}`) with {len(created.steps)} steps."


# Register workflow tools into global registry
registry.register(RunAutomationWorkflowTool())
registry.register(ListAvailableWorkflowsTool())
registry.register(CreateAutomationWorkflowTool())
