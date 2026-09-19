import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from backend.main import app
from backend.automation.engine import workflow_engine
from backend.automation.models import (
    WorkflowCreateRequest,
    WorkflowStep,
    WorkflowTriggerRequest
)
from backend.ai.registry import registry
from backend.config import settings

class TestVersion8Automation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        cls.headers = {"X-Jarvis-API-Key": settings.jarvis_api_key or "jarvis_secure_key_123"}

    def test_01_preset_workflows_loaded(self):
        """Verify that preset routines are loaded properly."""
        workflows = workflow_engine.list_workflows()
        wf_ids = [w.workflow_id for w in workflows]
        
        self.assertIn("start_work", wf_ids)
        self.assertIn("prepare_interview", wf_ids)
        self.assertIn("focus_mode", wf_ids)
        self.assertIn("relax_mode", wf_ids)
        self.assertIn("lockdown", wf_ids)

        start_work = workflow_engine.get_workflow("start_work")
        self.assertIsNotNone(start_work)
        self.assertEqual(start_work.name, "Start Workday")
        self.assertGreaterEqual(len(start_work.steps), 5)
        self.assertTrue(start_work.is_preset)

        prepare_interview = workflow_engine.get_workflow("prepare_interview")
        self.assertIsNotNone(prepare_interview)
        self.assertEqual(prepare_interview.name, "Prepare Interview Environment")
        self.assertGreaterEqual(len(prepare_interview.steps), 4)

    def test_02_trigger_matching(self):
        """Verify that voice and text trigger phrases match the correct workflows."""
        # Test "I'm starting work"
        match_1 = workflow_engine.match_trigger("Jarvis, I'm starting work")
        self.assertIsNotNone(match_1)
        self.assertEqual(match_1.workflow_id, "start_work")

        # Test "Prepare my interview environment"
        match_2 = workflow_engine.match_trigger("Jarvis, prepare my interview environment please")
        self.assertIsNotNone(match_2)
        self.assertEqual(match_2.workflow_id, "prepare_interview")

        # Test "Focus mode"
        match_3 = workflow_engine.match_trigger("Jarvis, enter focus mode")
        self.assertIsNotNone(match_3)
        self.assertEqual(match_3.workflow_id, "focus_mode")

        # Test "Relax mode"
        match_4 = workflow_engine.match_trigger("Time for relax mode")
        self.assertIsNotNone(match_4)
        self.assertEqual(match_4.workflow_id, "relax_mode")

    def test_03_custom_workflow_crud(self):
        """Verify creating, executing, and deleting a custom workflow."""
        custom_id = "test_custom_routine"
        steps = [
            WorkflowStep(
                step_id="t1",
                action_type="memory_update",
                title="Set Test Status",
                parameters={"key": "test_status", "value": "Running Custom Test", "category": "test"}
            ),
            WorkflowStep(
                step_id="t2",
                action_type="voice_speak",
                title="Spoken Test",
                parameters={"text": "Custom test routine executed."}
            )
        ]
        req = WorkflowCreateRequest(
            workflow_id=custom_id,
            name="Custom Test Routine",
            description="A test routine for verification",
            trigger_phrases=["run custom test", "test custom routine"],
            icon="🧪",
            steps=steps
        )
        
        # Create
        created = workflow_engine.create_or_update_workflow(req)
        self.assertEqual(created.workflow_id, custom_id)
        self.assertEqual(len(created.steps), 2)

        # Match trigger
        matched = workflow_engine.match_trigger("Jarvis, run custom test")
        self.assertIsNotNone(matched)
        self.assertEqual(matched.workflow_id, custom_id)

        # Execute
        res = workflow_engine.execute_workflow(custom_id)
        self.assertTrue(res.success)
        self.assertEqual(len(res.step_results), 2)
        self.assertIn("Custom test routine executed.", res.spoken_response)

        # Delete
        deleted = workflow_engine.delete_workflow(custom_id)
        self.assertTrue(deleted)
        self.assertIsNone(workflow_engine.get_workflow(custom_id))

    def test_04_ai_tools_registered(self):
        """Verify that workflow tools are registered in the global AI registry."""
        tool_names = list(registry._tools.keys())
        self.assertIn("run_automation_workflow", tool_names)
        self.assertIn("list_available_workflows", tool_names)
        self.assertIn("create_automation_workflow", tool_names)

        # Test listing tool execution
        list_tool = registry.get_tool("list_available_workflows")
        res = list_tool.execute({})
        self.assertIn("start_work", res)
        self.assertIn("prepare_interview", res)

        # Test run workflow tool
        run_tool = registry.get_tool("run_automation_workflow")
        run_res = run_tool.execute({"workflow_name_or_id": "focus_mode"})
        self.assertIn("Deep Focus Mode", run_res)

    def test_05_rest_api_workflows(self):
        """Verify REST API endpoints for Version 8 Workflows."""
        # 1. GET /api/workflows
        resp = self.client.get("/api/workflows", headers=self.headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        wfs = data["workflows"]
        ids = [w["workflow_id"] for w in wfs]
        self.assertIn("start_work", ids)
        self.assertIn("prepare_interview", ids)

        # 2. GET /api/workflows/start_work
        resp_detail = self.client.get("/api/workflows/start_work", headers=self.headers)
        self.assertEqual(resp_detail.status_code, 200)
        detail = resp_detail.json()["workflow"]
        self.assertEqual(detail["name"], "Start Workday")

        # 3. POST /api/workflows/trigger
        resp_trig = self.client.post("/api/workflows/trigger", json={"trigger": "Jarvis, I am starting work"}, headers=self.headers)
        self.assertEqual(resp_trig.status_code, 200)
        trig_res = resp_trig.json()
        self.assertEqual(trig_res["workflow_id"], "start_work")
        self.assertTrue(trig_res["success"])

        # 4. POST /api/workflows/focus_mode/run
        resp_run = self.client.post("/api/workflows/focus_mode/run", headers=self.headers)
        self.assertEqual(resp_run.status_code, 200)
        run_res = resp_run.json()
        self.assertEqual(run_res["workflow_id"], "focus_mode")
        self.assertTrue(run_res["success"])


if __name__ == "__main__":
    unittest.main()
