import os
import sys
import unittest
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.main import app
from backend.security.auth import device_auth
from backend.remote.laptop_agent import laptop_agent
from backend.ai.client import ai_client

class TestVersion7RemoteControl(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.headers = {"X-Jarvis-API-Key": "jarvis_secure_key_123"}

    def test_01_device_pairing_and_hmac_auth(self):
        """Test cryptographic token generation and HMAC-SHA256 signature verification."""
        device_id = "pixel_8_pro_demo"
        token = device_auth.generate_pairing_token(device_id, "Alex's Pixel Phone")
        self.assertTrue(len(token) > 20)
        self.assertTrue(device_auth.is_device_paired(device_id))

        # Test request signature verification
        payload = '{"action":"launch_app","app_name":"vscode"}'
        ts, sig = device_auth.create_signature(device_id, payload, secret=token)
        is_valid = device_auth.verify_request_signature(device_id, payload, ts, sig)
        self.assertTrue(is_valid, "HMAC-SHA256 signature should be verified successfully")

        # Test invalid signature rejection
        invalid = device_auth.verify_request_signature(device_id, payload, ts, "invalid_sig_123")
        self.assertFalse(invalid, "Tampered signature must be rejected")

    def test_02_remote_laptop_status_endpoint(self):
        """Test GET /api/remote/status endpoint for laptop power and online state."""
        response = self.client.get("/api/remote/status", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "online")
        laptop = data["laptop"]
        self.assertTrue(laptop["online"])
        self.assertIn("battery_percent", laptop)
        self.assertIn("cpu_percent", laptop)
        print(f" [PASS] Remote Laptop Telemetry: Battery {laptop['battery_percent']}%, Power: {laptop['battery_status']}")

    def test_03_remote_execute_endpoint(self):
        """Test POST /api/remote/execute endpoint for remote actions."""
        payload = {
            "action": "status"
        }
        response = self.client.post("/api/remote/execute", json=payload, headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertTrue(data["result"]["success"])

    def test_04_remote_screenshot_endpoint(self):
        """Test GET /api/remote/screenshot endpoint."""
        response = self.client.get("/api/remote/screenshot", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("image_base64", data)
        print(" [PASS] Screen snapshot captured successfully.")

    def test_05_websocket_mobile_connection(self):
        """Test WebSocket /ws/mobile bi-directional connection."""
        with self.client.websocket_connect("/ws/mobile?client_id=test_mobile") as ws:
            # First message received is initial laptop state
            init_msg = ws.receive_json()
            self.assertEqual(init_msg["type"], "laptop_state")

            # Send ping
            ws.send_json({"type": "ping", "payload": {"timestamp": 12345}})
            pong = ws.receive_json()
            self.assertEqual(pong["type"], "pong")

            # Request status
            ws.send_json({"type": "request_status", "payload": {}})
            status_msg = ws.receive_json()
            self.assertEqual(status_msg["type"], "laptop_state")
            print(" [PASS] WebSocket /ws/mobile bi-directional handshake verified.")

    def test_06_ai_agent_remote_query(self):
        """Test Groq LLM tool-calling for remote commands."""
        # Query: 'is my laptop on?'
        async def run_query():
            resp = await ai_client.generate_chat_response([
                {"role": "user", "content": "Jarvis, is my laptop on? Keep answer to 1 brief sentence."}
            ])
            return resp

        ans = asyncio.run(run_query())
        print(f" [PASS] AI Voice Response: '{ans}'")
        self.assertTrue(len(ans) > 5)

if __name__ == "__main__":
    unittest.main()
