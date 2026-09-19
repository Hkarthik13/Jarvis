import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.main import app
from backend.config import settings
from backend.core.gateway import jarvis_gateway

class TestVersion10Gateway(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.headers = {"X-Jarvis-API-Key": settings.jarvis_api_key or "jarvis_secure_key_123"}

    def test_01_system_overview_diagnostics(self):
        """Test GET /api/gateway/system-summary for unified health and metrics."""
        resp = self.client.get("/api/gateway/system-summary", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["version"], "10.0.0")
        self.assertEqual(data["status"], "online")
        self.assertIn("cpu_percent", data["hardware"])
        self.assertIn("ram_percent", data["hardware"])
        self.assertIn("battery", data["hardware"])
        self.assertTrue(data["subsystems"]["memory_sqlite"])
        self.assertTrue(data["subsystems"]["automation_engine"])
        self.assertGreater(data["counts"]["registered_tools"], 10)
        self.assertGreater(data["counts"]["workflows"], 3)

    def test_02_gateway_interact_workflow_trigger(self):
        """Test POST /api/gateway/interact when natural workflow trigger is invoked."""
        payload = {
            "text": "Jarvis, I am starting work",
            "session_id": "test_gateway",
            "synthesize_voice": False
        }
        resp = self.client.post("/api/gateway/interact", json=payload, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["query"], "Jarvis, I am starting work")
        self.assertEqual(data["workflow_triggered"], "Start Workday")
        self.assertIn("workflow:start_work", data["tools_executed"])
        self.assertTrue(len(data["response_text"]) > 10)

    def test_03_gateway_interact_rag_query(self):
        """Test POST /api/gateway/interact querying personal knowledge base."""
        payload = {
            "text": "What technologies are used in the AI Resume Analyzer project?",
            "session_id": "test_gateway",
            "synthesize_voice": False
        }
        resp = self.client.post("/api/gateway/interact", json=payload, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["query"], "What technologies are used in the AI Resume Analyzer project?")
        self.assertGreater(len(data["citations"]), 0)
        self.assertTrue(any("ai_resume_analyzer" in c["filename"].lower() for c in data["citations"]))

    def test_04_gateway_empty_query_fallback(self):
        """Test gateway handling of empty or blank interaction input."""
        payload = {"text": "  ", "session_id": "test_gateway"}
        resp = self.client.post("/api/gateway/interact", json=payload, headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("assist", data["response_text"].lower())


if __name__ == "__main__":
    unittest.main()
