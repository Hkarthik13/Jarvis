import os
import sys
import platform
import subprocess
import webbrowser
import datetime
import urllib.parse
from typing import Any, Dict
import psutil

from backend.ai.registry import BaseTool, registry
from backend.utils.logger import logger

# Approved safe desktop applications mapping
SAFE_APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "paint": "mspaint.exe"
}

# Approved browsers list
SAFE_BROWSERS = {"chrome", "edge", "firefox", "default"}


# --- Helper Function for Browser Launching ---
def launch_browser(browser_name: str, url: str = "about:blank") -> None:
    """Helper to launch a specific browser or default browser securely."""
    name = browser_name.lower().strip()
    if name == "chrome" and platform.system() == "Windows":
        paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
        ]
        for p in paths:
            if os.path.exists(p):
                subprocess.Popen([p, url], shell=False)
                return
    elif name == "edge" and platform.system() == "Windows":
        p = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        if os.path.exists(p):
            subprocess.Popen([p, url], shell=False)
            return
            
    # Fallback to python webbrowser module
    try:
        if name in ("chrome", "firefox"):
            webbrowser.get(name).open(url)
        else:
            webbrowser.open(url)
    except Exception:
        webbrowser.open(url)


# --- Tool Classes ---

class OpenApplicationTool(BaseTool):
    @property
    def name(self) -> str:
        return "open_application"

    @property
    def description(self) -> str:
        return "Opens a predefined safe desktop application. Supported apps: notepad, calculator, paint."

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
                            "description": "Name of the application to open (notepad, calculator, paint)."
                        }
                    },
                    "required": ["app_name"]
                }
            }
        }

    def validate_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        app_name = args.get("app_name")
        if not app_name:
            raise ValueError("Parameter 'app_name' is required.")
            
        normalized = app_name.lower().strip()
        if normalized not in SAFE_APPS:
            raise ValueError(f"Application '{app_name}' is not in the safe approved list. Allowed: {list(SAFE_APPS.keys())}")
            
        return {"app_name": normalized}

    def execute(self, args: Dict[str, Any]) -> Any:
        app_name = args["app_name"]
        executable = SAFE_APPS[app_name]
        subprocess.Popen([executable], shell=False)
        return f"Successfully opened {app_name}."


class OpenWebsiteTool(BaseTool):
    @property
    def name(self) -> str:
        return "open_website"

    @property
    def description(self) -> str:
        return "Opens a web URL in the user's default browser."

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
                        "url": {
                            "type": "string",
                            "description": "The URL of the website to open (e.g., google.com or news.ycombinator.com)."
                        }
                    },
                    "required": ["url"]
                }
            }
        }

    def validate_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        url = args.get("url")
        if not url:
            raise ValueError("Parameter 'url' is required.")
            
        cleaned_url = url.strip()
        dangerous_chars = (" ", '"', "'", ";", "|", "&", "<", ">", "`", "$", "\r", "\n")
        if any(char in cleaned_url for char in dangerous_chars):
            raise ValueError("Dangerous characters detected in URL.")
            
        parsed = urllib.parse.urlparse(cleaned_url)
        if not parsed.scheme:
            cleaned_url = "https://" + cleaned_url
            parsed = urllib.parse.urlparse(cleaned_url)
            
        if parsed.scheme not in ("http", "https"):
            raise ValueError(f"Invalid scheme '{parsed.scheme}'. Only http and https URLs are allowed.")
            
        return {"url": cleaned_url}

    def execute(self, args: Dict[str, Any]) -> Any:
        url = args["url"]
        webbrowser.open(url)
        return f"Successfully opened website: {url}"


class OpenFolderTool(BaseTool):
    @property
    def name(self) -> str:
        return "open_folder"

    @property
    def description(self) -> str:
        return "Opens a folder on the local machine in File Explorer. Use '.' or 'current' to open the current project folder."

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
                        "folder_path": {
                            "type": "string",
                            "description": "The local system path of the directory to open, or '.' for current project folder."
                        }
                    },
                    "required": ["folder_path"]
                }
            }
        }

    def validate_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        folder_path = args.get("folder_path", ".")
        if not folder_path or not str(folder_path).strip():
            folder_path = "."
            
        path_str = str(folder_path).strip()
        if path_str.lower() in ("current", "project", "current project", "workspace", "here", "current directory", "this folder"):
            path_str = "."
        if path_str.startswith(("\\\\", "//")):
            raise ValueError("UNC / Network paths are blocked for security.")
            
        abs_path = os.path.abspath(path_str)
        if abs_path.startswith(("\\\\", "//")):
            raise ValueError("Resolved absolute path is a UNC network path.")
            
        blocked_system_names = {"windows", "system volume information", "$recycle.bin"}
        path_parts = abs_path.lower().split(os.sep)
        for part in path_parts:
            if part in blocked_system_names:
                raise ValueError("Access to system directory is restricted for security.")
                
        if not os.path.exists(abs_path):
            raise ValueError(f"Folder path does not exist: {folder_path}")
            
        if not os.path.isdir(abs_path):
            raise ValueError(f"Path is not a directory/folder: {folder_path}")
            
        return {"abs_path": abs_path}

    def execute(self, args: Dict[str, Any]) -> Any:
        abs_path = args["abs_path"]
        if platform.system() == "Windows":
            subprocess.Popen(["explorer", abs_path], shell=False)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", abs_path])
        else:
            subprocess.Popen(["xdg-open", abs_path])
        return f"Successfully opened folder: {abs_path}"


class GetCpuUsageTool(BaseTool):
    @property
    def name(self) -> str:
        return "get_cpu_usage"

    @property
    def description(self) -> str:
        return "Gets the current system CPU utilization percentage."

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {"type": "object", "properties": {}}
            }
        }

    def validate_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return {}

    def execute(self, args: Dict[str, Any]) -> Any:
        usage = psutil.cpu_percent(interval=0.1)
        return f"Current CPU usage is at {usage}%."


class GetRamUsageTool(BaseTool):
    @property
    def name(self) -> str:
        return "get_ram_usage"

    @property
    def description(self) -> str:
        return "Gets the system's RAM utilization (percent, used, total)."

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {"type": "object", "properties": {}}
            }
        }

    def validate_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return {}

    def execute(self, args: Dict[str, Any]) -> Any:
        mem = psutil.virtual_memory()
        total_gb = mem.total / (1024 ** 3)
        used_gb = mem.used / (1024 ** 3)
        percent = mem.percent
        return f"RAM usage: {percent}% used ({used_gb:.2f} GB used out of {total_gb:.2f} GB total)."


class GetDiskUsageTool(BaseTool):
    @property
    def name(self) -> str:
        return "get_disk_usage"

    @property
    def description(self) -> str:
        return "Gets the primary storage drive's space utilization details (percent, used, total)."

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {"type": "object", "properties": {}}
            }
        }

    def validate_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return {}

    def execute(self, args: Dict[str, Any]) -> Any:
        root_path = "C:\\" if platform.system() == "Windows" else "/"
        disk = psutil.disk_usage(root_path)
        total_gb = disk.total / (1024 ** 3)
        used_gb = disk.used / (1024 ** 3)
        free_gb = disk.free / (1024 ** 3)
        percent = disk.percent
        return f"Primary disk usage ({root_path}): {percent}% used ({used_gb:.2f} GB used, {free_gb:.2f} GB free out of {total_gb:.2f} GB total)."


class GetBatteryStatusTool(BaseTool):
    @property
    def name(self) -> str:
        return "get_battery_status"

    @property
    def description(self) -> str:
        return "Gets the laptop battery status, charge level, and whether it is charging or on battery power."

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {"type": "object", "properties": {}}
            }
        }

    def validate_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return {}

    def execute(self, args: Dict[str, Any]) -> Any:
        battery = psutil.sensors_battery()
        if battery is None:
            return "No battery detected. The device is likely a desktop computer or running on direct AC power."
            
        percent = battery.percent
        power_plugged = battery.power_plugged
        charging_status = "charging/plugged in" if power_plugged else "discharging/on battery power"
        
        remaining_time = ""
        if not power_plugged and battery.secsleft != psutil.POWER_TIME_UNLIMITED and battery.secsleft != psutil.POWER_TIME_UNKNOWN:
            hours = battery.secsleft // 3600
            minutes = (battery.secsleft % 3600) // 60
            remaining_time = f" (estimated time remaining: {hours}h {minutes}m)"
            
        return f"Battery status: {percent}% charge, currently {charging_status}{remaining_time}."


class GetOsInfoTool(BaseTool):
    @property
    def name(self) -> str:
        return "get_os_info"

    @property
    def description(self) -> str:
        return "Gets operating system and hardware architecture details."

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {"type": "object", "properties": {}}
            }
        }

    def validate_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return {}

    def execute(self, args: Dict[str, Any]) -> Any:
        system = platform.system()
        release = platform.release()
        version = platform.version()
        arch = platform.machine()
        return f"Operating System: {system} {release} (Version: {version}, Architecture: {arch})."


class GetCurrentTimeDateTool(BaseTool):
    @property
    def name(self) -> str:
        return "get_current_time_date"

    @property
    def description(self) -> str:
        return "Gets the current local date, day of the week, and time on the system."

    @property
    def schema(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {"type": "object", "properties": {}}
            }
        }

    def validate_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        return {}

    def execute(self, args: Dict[str, Any]) -> Any:
        now = datetime.datetime.now()
        formatted = now.strftime("%A, %B %d, %Y at %I:%M:%S %p")
        return f"The current system date and time is {formatted}."


class OpenBrowserTool(BaseTool):
    @property
    def name(self) -> str:
        return "open_browser"

    @property
    def description(self) -> str:
        return "Opens a web browser. Supported browsers: chrome, edge, firefox, default."

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
                        "browser_name": {
                            "type": "string",
                            "description": "The browser to open (chrome, edge, firefox, default)."
                        }
                    },
                    "required": ["browser_name"]
                }
            }
        }

    def validate_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        browser_name = args.get("browser_name", "default")
        normalized = browser_name.lower().strip()
        if normalized not in SAFE_BROWSERS:
            raise ValueError(f"Browser '{browser_name}' is not in the safe approved list. Allowed: {list(SAFE_BROWSERS)}")
        return {"browser_name": normalized}

    def execute(self, args: Dict[str, Any]) -> Any:
        browser_name = args["browser_name"]
        launch_browser(browser_name, "about:blank")
        return f"Successfully opened {browser_name} browser."


class SearchWebTool(BaseTool):
    @property
    def name(self) -> str:
        return "search_web"

    @property
    def description(self) -> str:
        return "Performs a web search in the browser with the given query."

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
                        "query": {
                            "type": "string",
                            "description": "The search query to look up."
                        },
                        "browser": {
                            "type": "string",
                            "description": "Optional browser to open the search in (chrome, edge, firefox, default)."
                        }
                    },
                    "required": ["query"]
                }
            }
        }

    def validate_args(self, args: Dict[str, Any]) -> Dict[str, Any]:
        query = args.get("query")
        if not query:
            raise ValueError("Parameter 'query' is required.")
            
        cleaned_query = query.strip()
        if len(cleaned_query) > 200:
            raise ValueError("Query length exceeds maximum limit of 200 characters.")
            
        # Strip command separators to block injection
        dangerous_chars = (";", "|", "&", "<", ">", "`", "$", "\r", "\n")
        if any(char in cleaned_query for char in dangerous_chars):
            raise ValueError("Dangerous character tokens detected in search query.")
            
        browser = args.get("browser", "default")
        normalized_browser = browser.lower().strip()
        if normalized_browser not in SAFE_BROWSERS:
            raise ValueError(f"Browser '{browser}' is not in the safe approved list.")
            
        return {"query": cleaned_query, "browser": normalized_browser}

    def execute(self, args: Dict[str, Any]) -> Any:
        query = args["query"]
        browser = args["browser"]
        search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        launch_browser(browser, search_url)
        return f"Successfully executed web search for '{query}' in {browser} browser."


# --- Register Tools globally ---
registry.register(OpenApplicationTool())
registry.register(OpenWebsiteTool())
registry.register(OpenFolderTool())
registry.register(GetCpuUsageTool())
registry.register(GetRamUsageTool())
registry.register(GetDiskUsageTool())
registry.register(GetBatteryStatusTool())
registry.register(GetOsInfoTool())
registry.register(GetCurrentTimeDateTool())
registry.register(OpenBrowserTool())
registry.register(SearchWebTool())

# --- Register Internet & Live Retrieval Tools ---
from backend.ai.internet_tools import (
    GetLiveWeatherTool,
    SearchWebLiveTool,
    SearchYouTubeTool,
    FetchWebpageContentTool
)

registry.register(GetLiveWeatherTool())
registry.register(SearchWebLiveTool())
registry.register(SearchYouTubeTool())
registry.register(FetchWebpageContentTool())

# --- Register Memory & Persistence Tools (V5) ---
from backend.ai.memory_tools import (
    RememberFactTool,
    RecallMemoryTool,
    ManageUserPreferenceTool,
    ManageTasksTool,
    GetConversationHistoryTool
)

registry.register(RememberFactTool())
registry.register(RecallMemoryTool())
registry.register(ManageUserPreferenceTool())
registry.register(ManageTasksTool())
registry.register(GetConversationHistoryTool())


