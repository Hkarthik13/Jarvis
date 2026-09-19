import json
import asyncio
from fastapi import WebSocket, WebSocketDisconnect
from backend.utils.logger import logger
from backend.security.auth import device_auth
from backend.remote.laptop_agent import laptop_agent

class RemoteWebSocketHub:
    """
    Real-time bi-directional WebSocket hub connecting Mobile Controllers
    with the Laptop Control Agent.
    """
    def __init__(self):
        # Connected mobile websockets: {client_id: WebSocket}
        self._mobile_clients: dict[str, WebSocket] = {}
        # Connected laptop daemons: {daemon_id: WebSocket}
        self._laptop_daemons: dict[str, WebSocket] = {}

    async def register_mobile(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        self._mobile_clients[client_id] = websocket
        logger.info(f"[WSHub] Mobile controller connected: '{client_id}' (Total active: {len(self._mobile_clients)})")
        
        # Broadcast initial laptop state to mobile
        state = laptop_agent.get_status_summary()
        await websocket.send_json({
            "type": "laptop_state",
            "data": state
        })

    def unregister_mobile(self, client_id: str):
        if client_id in self._mobile_clients:
            del self._mobile_clients[client_id]
            logger.info(f"[WSHub] Mobile controller disconnected: '{client_id}'")

    async def handle_mobile_message(self, client_id: str, data: dict):
        """Processes remote control messages received from a mobile client."""
        msg_type = data.get("type")
        payload = data.get("payload", {})
        ws = self._mobile_clients.get(client_id)

        logger.info(f"[WSHub] Received '{msg_type}' from mobile '{client_id}'")

        if msg_type == "ping":
            if ws:
                await ws.send_json({"type": "pong", "timestamp": payload.get("timestamp")})

        elif msg_type == "execute_command":
            # Command execution: launch_app, lock_workstation, volume, screenshot
            action = payload.get("action")
            result = await self.execute_remote_action(action, payload)
            if ws:
                await ws.send_json({
                    "type": "command_result",
                    "action": action,
                    "result": result
                })

        elif msg_type == "request_status":
            state = laptop_agent.get_status_summary()
            if ws:
                await ws.send_json({
                    "type": "laptop_state",
                    "data": state
                })

        elif msg_type == "request_screenshot":
            snapshot = laptop_agent.capture_screenshot()
            if ws:
                await ws.send_json({
                    "type": "screenshot_result",
                    "data": snapshot
                })

    async def execute_remote_action(self, action: str, payload: dict) -> dict:
        """Executes a remote action directly via laptop agent."""
        if action == "launch_app":
            app_name = payload.get("app_name", "vscode")
            return laptop_agent.launch_app(app_name)

        elif action == "lock_workstation" or action == "lock_laptop":
            return laptop_agent.lock_workstation()

        elif action == "screenshot":
            return laptop_agent.capture_screenshot()

        elif action == "volume":
            vol_action = payload.get("volume_action", "toggle_mute")
            level = payload.get("level")
            return laptop_agent.control_volume(vol_action, level)

        elif action == "status":
            return {"success": True, "data": laptop_agent.get_status_summary()}

        return {"success": False, "error": f"Unknown remote action: '{action}'"}

    async def broadcast_to_mobile(self, message: dict):
        """Broadcasts a real-time event to all connected mobile clients."""
        for cid, ws in list(self._mobile_clients.items()):
            try:
                await ws.send_json(message)
            except Exception:
                self.unregister_mobile(cid)

# Global remote websocket hub instance
remote_hub = RemoteWebSocketHub()
