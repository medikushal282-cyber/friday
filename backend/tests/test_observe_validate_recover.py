import os
import sys
import unittest
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.workspace.manager import WorkspaceManager
from app.workspace.knowledge import get_knowledge_store
from app.workspace.tools import execute_action
from app.graph.workflow import execute_run_task
from app.graph.nodes.recovery import recovery_node

class TestObserveValidateRecover(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("GROQ_API_KEY", "dummy_groq_key_for_unit_tests")
        cls.ws = WorkspaceManager()
        cls.root = cls.ws.root_path
        cls.kb = get_knowledge_store()

    def setUp(self):
        self.kb.clear()

    def tearDown(self):
        for fname in ["csv_to_json_again.py", "sample.csv", "unrecoverable.py", "context_test.py"]:
            abs_path = os.path.join(self.root, fname)
            if os.path.exists(abs_path):
                try:
                    os.remove(abs_path)
                except Exception:
                    pass

    # 1. TEST FAILED COMMAND CAPTURED & RECOVERY TRIGGERED
    def test_1_failed_command_captured_and_recovery_triggered(self):
        run_id = "test_rec_001"
        objective = "Create a Python script named csv_to_json_again.py that converts CSV data to JSON using Python's standard library."
        runs_db = {run_id: {"run_id": run_id, "objective": objective, "status": "pending", "state": {}}}

        # Seed KB with CSV finding
        self.kb.save_finding({
            "query": "Python CSV to JSON standard library conversion",
            "finding": "Use csv.DictReader to read CSV file rows into dictionaries, then json.dumps() to serialize formatted JSON.",
            "source": "Python 3 Standard Library Documentation",
            "relevance": "Standard library pattern."
        })

        asyncio.run(execute_run_task(run_id, objective, runs_db))

        state = runs_db[run_id]["state"]
        self.assertEqual(runs_db[run_id]["status"], "completed")

        # Verify failed tool observation captured before recovery
        obs_list = state.get("observations", [])
        self.assertGreater(len(obs_list), 0)

        # Verify sample.csv was created during recovery
        sample_path = os.path.join(self.root, "sample.csv")
        self.assertTrue(os.path.exists(sample_path))

        # Verify script updated and stdout contains JSON
        stdouts = [o.get("stdout", "") for o in obs_list if "stdout" in o]
        combined_stdout = "\n".join(stdouts)
        self.assertIn("Alice", combined_stdout)
        self.assertIn("New York", combined_stdout)

        # Verify validation passed
        self.assertTrue(state.get("validation_results", [{}])[-1].get("valid"))

    # 2. TEST RECOVERY DOES NOT REPEAT BLINDLY
    def test_2_recovery_modifies_workspace_state(self):
        # Create a failing script initially
        script_path = os.path.join(self.root, "csv_to_json_again.py")
        with open(script_path, "w", encoding="utf-8") as f:
            f.write("import sys; print('usage: missing csv file'); sys.exit(1)\n")

        state = {
            "run_id": "test_rec_002",
            "objective": "Create a Python script named csv_to_json_again.py that converts CSV data to JSON using Python's standard library.",
            "validation_results": [{"valid": False, "reason": "Process exited with non-zero exit code (1)."}],
            "observations": [{
                "tool": "run_command",
                "filename": "csv_to_json_again.py",
                "exit_code": 1,
                "stderr": "usage: missing csv file",
                "stdout": ""
            }],
            "recovery_attempts": 0
        }

        # Run recovery node directly
        res_state = asyncio.run(recovery_node(state))

        # Verify recovery modified workspace file
        self.assertEqual(res_state["current_step"], "executor")
        self.assertEqual(res_state["recovery_attempts"], 1)

        with open(script_path, "r", encoding="utf-8") as f:
            new_content = f.read()
        self.assertIn("csv.DictReader", new_content)

    # 3. TEST MAXIMUM RECOVERY ATTEMPTS ENFORCED
    def test_3_maximum_recovery_attempts_enforced(self):
        state = {
            "run_id": "test_rec_003",
            "objective": "Unrecoverable failing objective",
            "validation_results": [{"valid": False, "reason": "Persistent error"}],
            "observations": [{"exit_code": 1, "stderr": "fatal error"}],
            "recovery_attempts": 2
        }

        res_state = asyncio.run(recovery_node(state))

        self.assertEqual(res_state["status"], "failed")
        self.assertEqual(res_state["current_step"], "end")

    # 4. TEST ORIGINAL OBJECTIVE PRESERVED
    def test_4_original_objective_preserved(self):
        run_id = "test_rec_004"
        objective = "Create a Python script named csv_to_json_again.py that converts CSV data to JSON using Python's standard library."
        runs_db = {run_id: {"run_id": run_id, "objective": objective, "status": "pending", "state": {}}}

        asyncio.run(execute_run_task(run_id, objective, runs_db))

        state = runs_db[run_id]["state"]
        self.assertEqual(state["objective"], objective)

    # 5. TEST EXISTING CONTEXT AND KB STILL PASS
    def test_5_existing_context_and_kb_still_pass(self):
        # KB Reuse
        self.kb.save_finding({
            "query": "Python CSV to JSON",
            "finding": "Use csv.DictReader and json.dumps",
            "source": "Python Docs",
            "relevance": "Standard pattern"
        })

        run_id = "test_rec_005"
        obj = "Create a Python script named csv_to_json_again.py that converts CSV data to JSON using Python's standard library."
        runs_db = {run_id: {"run_id": run_id, "objective": obj, "status": "pending", "state": {}}}

        asyncio.run(execute_run_task(run_id, obj, runs_db))
        state = runs_db[run_id]["state"]

        self.assertEqual(runs_db[run_id]["status"], "completed")
        self.assertTrue(state.get("research", [{}])[0].get("reused"))

if __name__ == "__main__":
    unittest.main()
