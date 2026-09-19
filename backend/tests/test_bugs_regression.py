import os
import sys
import unittest
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.workspace.manager import WorkspaceManager
from app.workspace.knowledge import get_knowledge_store
from app.graph.workflow import execute_run_task
from app.graph.nodes.validator import validator_node

class TestBugsRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("GROQ_API_KEY", "dummy_groq_key_for_unit_tests")
        cls.ws = WorkspaceManager()
        cls.root = cls.ws.root_path
        cls.kb = get_knowledge_store()

    def setUp(self):
        self.kb.clear()

    def tearDown(self):
        for fname in ["context_test.py", "csv_to_json.py", "csv_to_json_again.py", "unrelated.py"]:
            abs_path = os.path.join(self.root, fname)
            if os.path.exists(abs_path):
                try:
                    os.remove(abs_path)
                except Exception:
                    pass

    # BUG 1 TESTS: Grounded Validator & Objective Requirements
    def test_bug1_validator_fails_incorrect_output(self):
        # State where objective requires "Hello from Fraiday" but process output was "1\n2\n3\n4\n5\n"
        state = {
            "run_id": "test_bug1_fail",
            "objective": "Create context_test.py that prints 'Hello from Fraiday'.",
            "observations": [
                {
                    "tool": "run_command",
                    "exit_code": 0,
                    "stdout": "1\n2\n3\n4\n5\n"
                }
            ],
            "plan": []
        }
        res_state = asyncio.run(validator_node(state))
        val_res = res_state["validation_results"][-1]
        self.assertFalse(val_res["valid"])
        self.assertIn("failed objective requirement validation", val_res["reason"])

    def test_bug1_context_test_outputs_correct_text(self):
        run_id = "test_bug1_context_flow"
        objective = "Create a file named context_test.py that prints 'Hello from Fraiday'. Then modify that same file so it prints 'Hello from Fraiday Context'."
        runs_db = {run_id: {"run_id": run_id, "objective": objective, "status": "pending", "state": {}}}

        asyncio.run(execute_run_task(run_id, objective, runs_db))
        
        state = runs_db[run_id]["state"]
        self.assertEqual(runs_db[run_id]["status"], "completed")
        self.assertTrue(state.get("validation_results", [{}])[-1].get("valid"))

        # Verify exact string output recorded in observations
        stdouts = [o.get("stdout", "") for o in state.get("observations", []) if "stdout" in o]
        combined_output = "\n".join(stdouts)
        self.assertIn("Hello from Fraiday", combined_output)
        self.assertIn("Hello from Fraiday Context", combined_output)

    # BUG 2 TESTS: Cross-Run Knowledge Reuse
    def test_bug2_cross_run_knowledge_reuse(self):
        # RUN 1: Explicit research request (Research CSV to JSON)
        run_id1 = "test_bug2_run1"
        obj1 = "Create a Python script named csv_to_json.py that converts CSV data to JSON using Python's standard library. Research the correct CSV-to-JSON approach first, then create and run the script."
        runs_db1 = {run_id1: {"run_id": run_id1, "objective": obj1, "status": "pending", "state": {}}}

        asyncio.run(execute_run_task(run_id1, obj1, runs_db1))
        state1 = runs_db1[run_id1]["state"]

        # Verify research stored in persistent KnowledgeStore
        kb_findings = self.kb.load_findings()
        self.assertGreater(len(kb_findings), 0)
        saved = kb_findings[-1]
        self.assertIn("DictReader", saved.get("finding", "") + saved.get("relevance", ""))
        self.assertTrue(bool(saved.get("source")))

        # RUN 2: Implicit knowledge requirement (no explicit research request)
        run_id2 = "test_bug2_run2"
        obj2 = "Create a Python script named csv_to_json_again.py that converts CSV data to JSON using Python's standard library."
        runs_db2 = {run_id2: {"run_id": run_id2, "objective": obj2, "status": "pending", "state": {}}}

        asyncio.run(execute_run_task(run_id2, obj2, runs_db2))
        state2 = runs_db2[run_id2]["state"]

        # Verify RUN 2 reused knowledge without fresh research calls
        res_list2 = state2.get("research", [])
        self.assertGreater(len(res_list2), 0)
        reused = res_list2[0]
        self.assertTrue(reused.get("reused", False))
        self.assertEqual(reused.get("status"), "accepted")
        self.assertTrue(bool(reused.get("source")))

    def test_bug2_unrelated_objective_no_false_reuse(self):
        # Seed KnowledgeStore with CSV finding
        self.kb.save_finding({
            "query": "Python CSV to JSON standard library conversion",
            "finding": "Use csv.DictReader to read CSV file rows into dictionaries, then json.dumps() to serialize formatted JSON.",
            "source": "Python 3 Standard Library Documentation",
            "relevance": "Provides exact standard library pattern."
        })

        # Run unrelated simple objective
        run_id = "test_bug2_unrelated"
        obj = "Create a Python script named unrelated.py that prints Hello Fraiday."
        runs_db = {run_id: {"run_id": run_id, "objective": obj, "status": "pending", "state": {}}}

        asyncio.run(execute_run_task(run_id, obj, runs_db))
        state = runs_db[run_id]["state"]

        res_list = state.get("research", [])
        if res_list:
            self.assertFalse(res_list[0].get("reused", False))

    def test_bug2_explicit_research_request_triggers_research(self):
        # Seed KnowledgeStore with existing finding
        self.kb.save_finding({
            "query": "Python CSV to JSON standard library conversion",
            "finding": "Old finding content",
            "source": "Python Documentation",
            "relevance": "Existing finding"
        })

        # Run objective with explicit research request
        run_id = "test_bug2_explicit"
        obj = "Research the correct CSV-to-JSON approach first, then create csv_to_json.py."
        runs_db = {run_id: {"run_id": run_id, "objective": obj, "status": "pending", "state": {}}}

        asyncio.run(execute_run_task(run_id, obj, runs_db))
        state = runs_db[run_id]["state"]

        # Should perform research and NOT blindly reuse without research step
        res_list = state.get("research", [])
        self.assertGreater(len(res_list), 0)
        first_finding = res_list[0]
        self.assertEqual(first_finding.get("status"), "accepted")

if __name__ == "__main__":
    unittest.main()
