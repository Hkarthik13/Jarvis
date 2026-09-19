from typing import Any, Dict
from backend.ai.registry import BaseTool, registry
from backend.remote.laptop_agent import laptop_agent

class CheckLaptopStatusTool(BaseTool):
    @property
    def name(self) -> str:
        return "check_laptop_status"

    @property
    def description(self) -> str:
        return (
            "Check if the laptop is powered on, active, and get its live battery level, CPU load, and charging status. "
            "Use whenever the user asks 'is my laptop on?', 'is my laptop awake?', or queries laptop power."
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
        stats = laptop_agent.get_status_summary()
        power_str = "Plugged in (Charging)" if stats["power_plugged"] else "On Battery"
        return (
            f"Laptop '{stats['laptop_name']}' is ONLINE. "
            f"OS: {stats['os']}, Battery: {stats['battery_percent']}% ({power_str}), "
            f"CPU Load: {stats['cpu_percent']}%, RAM Usage: {stats['ram_percent']}%."
        )


class RemoteLaunchAppTool(BaseTool):
    @property
    def name(self) -> str:
        return "remote_launch_app"

    @property
    def description(self) -> str:
        return (
            "Launch an application on the user's laptop remotely (e.g. VS Code, Chrome, Spotify, Terminal, Notepad, File Explorer). "
            "Use whenever the user asks to open or start any app on their laptop."
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
                        "app_name": {
                            "type": "string",
                            "description": "Name of the app to launch (e.g. 'vscode', 'code', 'chrome', 'spotify', 'terminal', 'notepad', 'explorer')"
                        }
                    },
                    "required": ["app_name"]
                }
            }
        }

    def validate_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        app_name = args.get("app_name", "vscode").strip()
        if not app_name:
            raise ValueError("Parameter 'app_name' cannot be empty.")
        return {"app_name": app_name}

    def execute(self, args: Dict[str, Any]) -> Any:
        res = laptop_agent.launch_app(args["app_name"])
        if res.get("success"):
            return res.get("message", f"Launched {args['app_name']} on your laptop.")
        return f"Failed to launch {args['app_name']}: {res.get('error')}"


class RemoteLockLaptopTool(BaseTool):
    @property
    def name(self) -> str:
        return "remote_lock_laptop"

    @property
    def description(self) -> str:
        return (
            "Locks the laptop workstation screen immediately. "
            "Use when user asks to 'lock my laptop', 'lock screen', or 'secure my computer'."
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
        res = laptop_agent.lock_workstation()
        if res.get("success"):
            return "Your laptop screen has been locked."
        return f"Could not lock laptop: {res.get('error')}"


class RemoteMediaControlTool(BaseTool):
    @property
    def name(self) -> str:
        return "remote_media_control"

    @property
    def description(self) -> str:
        return (
            "Control laptop audio volume or mute state remotely. "
            "Options: 'mute', 'unmute', 'toggle_mute', 'volume_up', 'volume_down'."
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
                        "action": {
                            "type": "string",
                            "description": "The audio action: 'mute', 'unmute', 'toggle_mute', 'volume_up', 'volume_down'"
                        }
                    },
                    "required": ["action"]
                }
            }
        }

    def validate_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        action = args.get("action", "toggle_mute")
        return {"action": action}

    def execute(self, args: Dict[str, Any]) -> Any:
        res = laptop_agent.control_volume(args["action"])
        if res.get("success"):
            return res.get("message", f"Audio command '{args['action']}' executed.")
        return f"Audio command failed: {res.get('error')}"


class RemoteScreenCaptureTool(BaseTool):
    @property
    def name(self) -> str:
        return "remote_screen_capture"

    @property
    def description(self) -> str:
        return (
            "Captures a live screenshot of the laptop's active screen display. "
            "Use when the user asks for a screenshot or asks what is currently displayed on the laptop."
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
        res = laptop_agent.capture_screenshot()
        if res.get("success"):
            return "Captured a live screenshot of your laptop screen successfully."
        return f"Screen capture failed: {res.get('error')}"


class MediaPlaybackTool(BaseTool):
    @property
    def name(self) -> str:
        return "media_playback_control"

    @property
    def description(self) -> str:
        return (
            "Controls media playback on the laptop (Spotify, YouTube, Media Player). "
            "Supported actions: 'play_pause', 'next', 'prev', 'stop'."
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
                        "action": {
                            "type": "string",
                            "description": "Media action: 'play_pause', 'next', 'prev', 'stop'"
                        }
                    },
                    "required": ["action"]
                }
            }
        }

    def validate_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        action = args.get("action", "play_pause")
        return {"action": action}

    def execute(self, args: Dict[str, Any]) -> Any:
        res = laptop_agent.media_control(args["action"])
        if res.get("success"):
            return res.get("message", f"Media command '{args['action']}' executed.")
        return f"Media command failed: {res.get('error')}"


class ClipboardTool(BaseTool):
    @property
    def name(self) -> str:
        return "manage_clipboard"

    @property
    def description(self) -> str:
        return "Reads or writes text from/to the Windows clipboard on the laptop."

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
                        "action": {
                            "type": "string",
                            "description": "'get' to read clipboard, 'set' to copy text to clipboard."
                        },
                        "text": {
                            "type": "string",
                            "description": "Text to write when action is 'set'."
                        }
                    },
                    "required": ["action"]
                }
            }
        }

    def validate_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        action = args.get("action", "get")
        text = args.get("text", "")
        return {"action": action, "text": text}

    def execute(self, args: Dict[str, Any]) -> Any:
        res = laptop_agent.manage_clipboard(args["action"], args.get("text"))
        if res.get("success"):
            if "content" in res:
                return f"Clipboard content: {res['content']}"
            return res.get("message", "Clipboard operation successful.")
        return f"Clipboard operation failed: {res.get('error')}"


# Register remote control tools into the global registry
registry.register(CheckLaptopStatusTool())
registry.register(RemoteLaunchAppTool())
registry.register(RemoteLockLaptopTool())
registry.register(RemoteMediaControlTool())
registry.register(RemoteScreenCaptureTool())
registry.register(MediaPlaybackTool())
registry.register(ClipboardTool())
