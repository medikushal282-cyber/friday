import os
import sys
import unittest
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.workspace.manager import WorkspaceManager
from app.graph.nodes.researcher import researcher_node, detect_knowledge_gap
from app.graph.workflow import execute_run_task

class TestAutonomousResearcher(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("GROQ_API_KEY", "dummy_groq_key_for_unit_tests")
        cls.ws = WorkspaceManager()
        cls.root = cls.ws.root_path

    def tearDown(self):
        for fname in ["csv_to_json.py", "data.csv"]:
            abs_path = os.path.join(self.root, fname)
            if os.path.exists(abs_path):
                try:
                    os.remove(abs_path)
                except Exception:
                    pass

    # TEST 1 — KNOWLEDGE GAP DETECTION & NO UNNECESSARY RESEARCH
    def test_1_knowledge_gap_detection(self):
        # Complex objective requiring research -> gap detected
        complex_obj = "Create a Python script that converts a CSV file to JSON using Python's standard library. Research the correct CSV-to-JSON approach first, then create and run the script."
        self.assertTrue(detect_knowledge_gap(complex_obj))

        # Simple objective -> no gap detected
        simple_obj = "Create a Python script that prints Hello Fraiday."
        self.assertFalse(detect_knowledge_gap(simple_obj))

    # TEST 2 — RESEARCHER NODE ON COMPLEX OBJECTIVE
    def test_2_researcher_node_complex_objective(self):
        run_id = "test_run_res_001"
        obj = "Create a Python script that converts a CSV file to JSON using Python's standard library. Research the correct CSV-to-JSON approach first, then create and run the script."
        state = {
            "run_id": run_id,
            "objective": obj,
            "workspace": {"root_path": self.root},
            "conversation_context": [],
            "plan": [{"id": "step_1", "agent": "researcher", "description": "Research CSV to JSON", "status": "pending"}],
            "current_step": "researcher",
            "research": [],
            "tool_calls": [],
            "observations": [],
            "artifacts": [],
            "validation_results": [],
            "status": "running",
            "error": None,
            "retry_count": 0,
            "approval_required": False
        }

        async def run_node():
            return await researcher_node(state)

        updated_state = asyncio.run(run_node())
        research_findings = updated_state.get("research", [])

        self.assertGreater(len(research_findings), 0)
        finding = research_findings[0]
        self.assertEqual(finding.get("status"), "accepted")
        self.assertIn("query", finding)
        self.assertIn("finding", finding)
        self.assertIn("source", finding)
        self.assertIn("relevance", finding)

    # TEST 3 — RESEARCHER NODE ON SIMPLE OBJECTIVE (NO UNNECESSARY RESEARCH)
    def test_3_researcher_node_simple_objective(self):
        run_id = "test_run_res_002"
        obj = "Create a Python script that prints Hello Fraiday."
        state = {
            "run_id": run_id,
            "objective": obj,
            "workspace": {"root_path": self.root},
            "conversation_context": [],
            "plan": [{"id": "step_1", "agent": "researcher", "description": "Inspect context", "status": "pending"}],
            "current_step": "researcher",
            "research": [],
            "tool_calls": [],
            "observations": [],
            "artifacts": [],
            "validation_results": [],
            "status": "running",
            "error": None,
            "retry_count": 0,
            "approval_required": False
        }

        async def run_node():
            return await researcher_node(state)

        updated_state = asyncio.run(run_node())
        research = updated_state.get("research", [])

        self.assertGreater(len(research), 0)
        self.assertFalse(research[0].get("needed", True))

    # TEST 4 — FULL WORKFLOW END-TO-END WITH RESEARCH
    def test_4_full_workflow_with_research(self):
        run_id = "test_run_res_003"
        obj = "Create a Python script that converts a CSV file to JSON using Python's standard library. Research the correct CSV-to-JSON approach first, then create and run the script."
        runs_db = {run_id: {"run_id": run_id, "objective": obj, "status": "pending", "state": {}}}

        asyncio.run(execute_run_task(run_id, obj, runs_db))

        state = runs_db[run_id]["state"]
        self.assertEqual(runs_db[run_id]["status"], "completed")

        # Verify research finding was accepted and stored in context
        research = state.get("research", [])
        self.assertGreater(len(research), 0)
        self.assertEqual(research[0].get("status"), "accepted")

        # Verify script created and executed
        proc_obs = next(o for o in reversed(state.get("observations", [])) if "exit_code" in o)
        self.assertEqual(proc_obs.get("exit_code"), 0)
        self.assertIn("Alice", proc_obs.get("stdout", ""))


if __name__ == "__main__":
    unittest.main()
