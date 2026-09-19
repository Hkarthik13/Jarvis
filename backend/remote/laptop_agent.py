import os
import subprocess
import platform
import psutil
import datetime
import base64
import io
from backend.utils.logger import logger

class LaptopExecutionAgent:
    """
    Direct system executor running on the laptop to perform remote actions
    commanded by mobile clients or the AI Agent.
    """

    def __init__(self):
        self.os_type = platform.system()

    SAFE_APPS = {
        "vscode": ["code"],
        "vs code": ["code"],
        "code": ["code"],
        "notepad": ["notepad.exe"],
        "calculator": ["calc.exe"],
        "calc": ["calc.exe"],
        "paint": ["mspaint.exe"],
        "terminal": ["wt.exe", "powershell.exe", "cmd.exe"],
        "cmd": ["cmd.exe"],
        "powershell": ["powershell.exe"],
        "explorer": ["explorer.exe"],
        "file explorer": ["explorer.exe"],
        "files": ["explorer.exe"],
        "chrome": ["chrome.exe", "google-chrome"],
        "edge": ["msedge.exe"],
        "browser": ["start", "http://google.com"],
        "spotify": ["spotify.exe"]
    }

    def _resolve_app_executable(self, key: str) -> str:
        """Finds the absolute path to common desktop applications on Windows."""
        local_app = os.environ.get("LOCALAPPDATA", "")
        app_data = os.environ.get("APPDATA", "")
        prog_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        prog_files_x86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")

        known_paths = {
            "vscode": [
                os.path.join(local_app, r"Programs\Microsoft VS Code\Code.exe"),
                os.path.join(prog_files, r"Microsoft VS Code\Code.exe"),
                os.path.join(local_app, r"Programs\Microsoft VS Code\bin\code.cmd"),
                "code"
            ],
            "chrome": [
                os.path.join(prog_files, r"Google\Chrome\Application\chrome.exe"),
                os.path.join(prog_files_x86, r"Google\Chrome\Application\chrome.exe"),
                "chrome"
            ],
            "edge": [
                os.path.join(prog_files_x86, r"Microsoft\Edge\Application\msedge.exe"),
                "msedge"
            ],
            "spotify": [
                os.path.join(app_data, r"Spotify\Spotify.exe"),
                "spotify"
            ],
            "notepad": ["notepad.exe"],
            "calc": ["calc.exe"],
            "calculator": ["calc.exe"],
            "paint": ["mspaint.exe"],
            "explorer": ["explorer.exe"],
            "terminal": ["wt.exe", "powershell.exe", "cmd.exe"]
        }

        for app_key, candidates in known_paths.items():
            if app_key in key or key in app_key:
                for candidate in candidates:
                    if os.path.isabs(candidate) and os.path.exists(candidate):
                        return candidate
                    elif not os.path.isabs(candidate):
                        return candidate

        return key

    def launch_app(self, app_name: str, path: str = None) -> dict:
        """Launches a desktop application on the laptop."""
        key = app_name.lower().strip()
        logger.info(f"[LaptopAgent] Remote action requested: Launch app '{app_name}' (path: {path})")

        try:
            exe = self._resolve_app_executable(key)
            # If path specified
            if path and os.path.exists(path):
                if os.path.isdir(path):
                    if key in ("vscode", "vs code", "code"):
                        subprocess.Popen(f'code "{path}"', shell=True)
                        return {"success": True, "message": f"Opened folder '{path}' in VS Code."}
                    else:
                        subprocess.Popen(f'explorer "{path}"', shell=True)
                        return {"success": True, "message": f"Opened directory '{path}'."}
                else:
                    subprocess.Popen(f'start "" "{path}"', shell=True)
                    return {"success": True, "message": f"Launched file at path: {path}"}

            if exe:
                subprocess.Popen(f'start "" "{exe}"', shell=True)
                return {"success": True, "message": f"Successfully launched {app_name} on your laptop."}
            else:
                subprocess.Popen(f'start {key}', shell=True)
                return {"success": True, "message": f"Sent launch signal for '{app_name}'."}
        except Exception as e:
            logger.error(f"[LaptopAgent] Error launching app '{app_name}': {e}")
            return {"success": False, "error": str(e)}

    def lock_workstation(self) -> dict:
        """Locks the Windows workstation instantly."""
        logger.info("[LaptopAgent] Remote action: Locking workstation...")
        try:
            if self.os_type == "Windows":
                subprocess.Popen("rundll32.exe user32.dll,LockWorkStation", shell=True)
                return {"success": True, "message": "Laptop workstation locked successfully."}
            else:
                return {"success": False, "error": f"Workstation lock not supported on {self.os_type}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def capture_screenshot(self, max_width: int = 800) -> dict:
        """
        Captures a live screenshot of the laptop display and returns a compressed Base64 JPEG.
        Uses PowerShell + .NET drawing as native zero-dependency on Windows, or Pillow if available.
        """
        logger.info("[LaptopAgent] Capturing screen snapshot...")
        try:
            # 1. Try PIL / Pillow
            try:
                from PIL import ImageGrab, Image
                screenshot = ImageGrab.grab()
                if screenshot.width > max_width:
                    ratio = max_width / float(screenshot.width)
                    new_height = int(float(screenshot.height) * ratio)
                    screenshot = screenshot.resize((max_width, new_height), Image.Resampling.LANCZOS)
                
                buffer = io.BytesIO()
                screenshot.save(buffer, format="JPEG", quality=70)
                encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
                return {
                    "success": True,
                    "image_base64": encoded,
                    "mime_type": "image/jpeg",
                    "width": screenshot.width,
                    "height": screenshot.height
                }
            except Exception as pil_err:
                logger.debug(f"[LaptopAgent] PIL screenshot fallback: {pil_err}")

            # 2. Native Windows PowerShell capture fallback
            try:
                ps_script = """
                Add-Type -AssemblyName System.Windows.Forms
                Add-Type -AssemblyName System.Drawing
                $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
                $bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
                $g = [System.Drawing.Graphics]::FromImage($bmp)
                $g.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
                $ms = New-Object System.IO.MemoryStream
                $bmp.Save($ms, [System.Drawing.Imaging.ImageFormat]::Jpeg)
                [Convert]::ToBase64String($ms.ToArray())
                """
                result = subprocess.check_output(["powershell", "-Command", ps_script], timeout=6).decode("utf-8").strip()
                if result:
                    return {
                        "success": True,
                        "image_base64": result,
                        "mime_type": "image/jpeg"
                    }
            except Exception as ps_err:
                logger.debug(f"[LaptopAgent] PowerShell screenshot fallback: {ps_err}")

            # 3. Fallback placeholder telemetry canvas (for headless/virtual desktop sessions)
            from PIL import Image, ImageDraw
            img = Image.new("RGB", (640, 360), color=(7, 11, 20))
            draw = ImageDraw.Draw(img)
            draw.text((20, 20), f"JARVIS Laptop Active: {platform.node()}", fill=(0, 240, 255))
            draw.text((20, 50), f"Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fill=(248, 250, 252))
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=70)
            return {
                "success": True,
                "image_base64": base64.b64encode(buffer.getvalue()).decode("utf-8"),
                "mime_type": "image/jpeg",
                "is_simulated": True
            }
        except Exception as e:
            logger.error(f"[LaptopAgent] Screenshot capture error: {e}")
            return {"success": False, "error": str(e)}

    def control_volume(self, action: str, level: int = None) -> dict:
        """Controls system volume or mute state on Windows."""
        logger.info(f"[LaptopAgent] Volume action: {action} (level: {level})")
        try:
            if self.os_type == "Windows":
                if action in ("mute", "unmute", "toggle_mute"):
                    # Send media mute key 0xAD (173)
                    subprocess.Popen("powershell -Command (New-Object -ComObject Wscript.Shell).SendKeys([char]173)", shell=True)
                    return {"success": True, "message": "Toggled audio mute state."}
                elif action in ("volume_up", "up", "increase"):
                    subprocess.Popen("powershell -Command 1..5 | ForEach-Object { (New-Object -ComObject Wscript.Shell).SendKeys([char]175) }", shell=True)
                    return {"success": True, "message": "Increased system volume."}
                elif action in ("volume_down", "down", "decrease"):
                    subprocess.Popen("powershell -Command 1..5 | ForEach-Object { (New-Object -ComObject Wscript.Shell).SendKeys([char]174) }", shell=True)
                    return {"success": True, "message": "Decreased system volume."}
                else:
                    return {"success": True, "message": f"Executed volume command '{action}'"}
            return {"success": False, "error": "Volume control only supported on Windows"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def media_control(self, action: str) -> dict:
        """Controls media playback (play/pause, next track, prev track) on Windows."""
        act = action.lower().strip()
        logger.info(f"[LaptopAgent] Media control action: {act}")
        try:
            if self.os_type == "Windows":
                if act in ("play_pause", "play", "pause", "toggle"):
                    # Media Play/Pause key 0xB3 (179)
                    subprocess.Popen("powershell -Command (New-Object -ComObject Wscript.Shell).SendKeys([char]179)", shell=True)
                    return {"success": True, "message": "Toggled media play/pause."}
                elif act in ("next", "next_track", "skip"):
                    # Media Next Track key 0xB0 (176)
                    subprocess.Popen("powershell -Command (New-Object -ComObject Wscript.Shell).SendKeys([char]176)", shell=True)
                    return {"success": True, "message": "Skipped to next media track."}
                elif act in ("prev", "previous", "prev_track", "back"):
                    # Media Previous Track key 0xB1 (177)
                    subprocess.Popen("powershell -Command (New-Object -ComObject Wscript.Shell).SendKeys([char]177)", shell=True)
                    return {"success": True, "message": "Returned to previous media track."}
                elif act in ("stop",):
                    # Media Stop key 0xB2 (178)
                    subprocess.Popen("powershell -Command (New-Object -ComObject Wscript.Shell).SendKeys([char]178)", shell=True)
                    return {"success": True, "message": "Stopped media playback."}
            return {"success": False, "error": f"Media action '{action}' not supported."}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def manage_clipboard(self, action: str, text: str = None) -> dict:
        """Reads or writes to Windows clipboard."""
        act = action.lower().strip()
        try:
            if self.os_type == "Windows":
                if act in ("get", "read", "copy_from"):
                    clip_text = subprocess.check_output(["powershell", "-Command", "Get-Clipboard"], timeout=3).decode("utf-8").strip()
                    return {"success": True, "content": clip_text}
                elif act in ("set", "write", "copy_to"):
                    safe_text = (text or "").replace('"', '`"')
                    subprocess.Popen(f'powershell -Command "Set-Clipboard -Value \\"{safe_text}\\""', shell=True)
                    return {"success": True, "message": "Copied text to clipboard."}
            return {"success": False, "error": "Clipboard operations only supported on Windows"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_status_summary(self) -> dict:
        """Returns live hardware state for 'is my laptop on?' queries."""
        battery = psutil.sensors_battery()
        cpu = psutil.cpu_percent(interval=0.05)
        ram = psutil.virtual_memory()

        return {
            "online": True,
            "laptop_name": platform.node(),
            "os": f"{platform.system()} {platform.release()}",
            "cpu_percent": cpu,
            "ram_percent": ram.percent,
            "battery_percent": battery.percent if battery else 100,
            "power_plugged": battery.power_plugged if battery else True,
            "battery_status": ("Charging" if battery.power_plugged else "On Battery") if battery else "AC Power",
            "timestamp": datetime.datetime.now().strftime("%I:%M %p")
        }

# Global laptop agent instance
laptop_agent = LaptopExecutionAgent()
