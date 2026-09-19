import os
import sys
import socket
import uvicorn

# Reconfigure stdout/stderr for UTF-8 on Windows terminals
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from backend.config import settings

def get_local_ip():
    """Find the local LAN IP address of this machine."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def main():
    local_ip = get_local_ip()
    print("=" * 70)
    print("        [⚡] JARVIS AI SYSTEM - VERSION 10.0 (ADVANCED UNIFIED) [⚡]        ")
    print("=" * 70)
    print(f"  [+] FastAPI Gateway:               http://0.0.0.0:8000")
    print(f"  [+] Local Laptop Web Access:       http://localhost:8000")
    print(f"  [+] Flutter Mobile / LAN IP:       http://{local_ip}:8000")
    print(f"  [+] AI Brain Model (Groq):         {settings.llm_model}")
    print(f"  [+] Voice Engine (Edge-TTS):       {settings.tts_voice}")
    print(f"  [+] Memory & RAG Vault:            Active (SQLite + Vector Store)")
    print(f"  [+] Windows Laptop Agent:          Active (App/Media/Security Control)")
    print(f"  [+] Automation Engine:             Active (Multi-Action Workflows)")
    print("=" * 70)
    print(f"  [Mobile] Flutter Mobile App Configuration (Settings):")
    print(f"     Server URL: http://{local_ip}:8000")
    print(f"     API Key:    {settings.jarvis_api_key}")
    print("=" * 70)
    print("\nStarting Unified JARVIS Gateway Server on Port 8000...\n")

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()
