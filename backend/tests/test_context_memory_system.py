import os
import sys
import unittest
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.workspace.manager import WorkspaceManager, PathSecurityError
from app.workspace.tools import execute_action
from app.graph.workflow import execute_run_task

class TestContextMemorySystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("GROQ_API_KEY", "dummy_groq_key_for_unit_tests")
        cls.ws = WorkspaceManager()
        cls.root = cls.ws.root_path

    def tearDown(self):
        # Clean up test files created during context tests
        for fname in ["context_test.py", "numbers.py", "calculator.py"]:
            abs_path = os.path.join(self.root, fname)
            if os.path.exists(abs_path):
                try:
                    os.remove(abs_path)
                except Exception:
                    pass

    # TEST 1 — SAME RUN CONTEXT
    def test_1_same_run_context(self):
        run_id = "test_run_ctx_001"
        objective = "Create context_test.py that prints Hello Fraiday."
        runs_db = {run_id: {"run_id": run_id, "objective": objective, "status": "pending", "state": {}}}

        asyncio.run(execute_run_task(run_id, objective, runs_db))

        state = runs_db[run_id]["state"]
        status = runs_db[run_id]["status"]

        self.assertEqual(status, "completed")
        self.assertGreater(len(state.get("tool_calls", [])), 0)
        self.assertGreater(len(state.get("observations", [])), 0)
        self.assertTrue(state.get("validation_results", [{}])[-1].get("valid"))

        # Verify file created on disk
        abs_path = os.path.join(self.root, "context_test.py")
        self.assertTrue(os.path.exists(abs_path))
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Hello Fraiday", content)

    # TEST 2 — FOLLOW-UP CONTEXT
    def test_2_follow_up_context(self):
        # Turn 1: Create initial file
        run_id1 = "test_run_ctx_002a"
        obj1 = "Create context_test.py that prints Hello Fraiday."
        runs_db = {run_id1: {"run_id": run_id1, "objective": obj1, "status": "pending", "state": {}}}
        asyncio.run(execute_run_task(run_id1, obj1, runs_db))
        state1 = runs_db[run_id1]["state"]

        # Turn 1 summary stored in context
        turn1_context = [{
            "run_id": run_id1,
            "objective": obj1,
            "artifacts": state1.get("artifacts", []),
            "observations": state1.get("observations", []),
            "validation": state1.get("validation_results", [])
        }]

        # Turn 2: Follow-up instruction using pronoun "it"
        run_id2 = "test_run_ctx_002b"
        obj2 = "Update it to print Hello Fraiday 2."
        runs_db[run_id2] = {"run_id": run_id2, "objective": obj2, "status": "pending", "state": {}}

        asyncio.run(execute_run_task(run_id2, obj2, runs_db, recent_context=turn1_context))

        state2 = runs_db[run_id2]["state"]
        self.assertEqual(runs_db[run_id2]["status"], "completed")

        # Verify update_file action was recorded
        update_calls = [c for c in state2.get("tool_calls", []) if c.get("action", {}).get("tool") == "update_file"]
        self.assertGreater(len(update_calls), 0)

        # Verify file content updated on disk
        abs_path = os.path.join(self.root, "context_test.py")
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("Hello Fraiday 2", content)

        # Verify process stdout contains Hello Fraiday 2
        proc_obs = next(o for o in reversed(state2.get("observations", [])) if "exit_code" in o)
        self.assertEqual(proc_obs.get("exit_code"), 0)
        self.assertIn("Hello Fraiday 2", proc_obs.get("stdout", ""))

    # TEST 3 — MULTI-STEP CONTEXT IN SINGLE RUN
    def test_3_multi_step_context(self):
        run_id = "test_run_ctx_003"
        objective = "Create numbers.py that prints numbers 1 through 5, run it, then update it to print 1 through 10."
        runs_db = {run_id: {"run_id": run_id, "objective": objective, "status": "pending", "state": {}}}

        asyncio.run(execute_run_task(run_id, objective, runs_db))

        state = runs_db[run_id]["state"]
        self.assertEqual(runs_db[run_id]["status"], "completed")

        # Verify both create and update operations recorded
        tools_used = [c.get("action", {}).get("tool") for c in state.get("tool_calls", [])]
        self.assertIn("create_file", tools_used)
        self.assertIn("update_file", tools_used)
        self.assertIn("run_command", tools_used)

        # Verify final execution stdout contains 10
        proc_obs = next(o for o in reversed(state.get("observations", [])) if "exit_code" in o)
        self.assertEqual(proc_obs.get("exit_code"), 0)
        self.assertIn("10", proc_obs.get("stdout", ""))

    # TEST 4 — SECURITY WITH CONTEXT
    def test_4_security_containment_with_context(self):
        # Attempt to pass context path referencing outside workspace
        action = {"tool": "read_file", "arguments": {"path": "../../../outside.txt"}}
        res = execute_action(action)
        self.assertFalse(res["success"])
        self.assertEqual(res["error"]["code"], "PATH_SECURITY_ERROR")

    # TEST 5 — REGRESSION (Activity 1 functionality preserved)
    def test_5_activity1_regression(self):
        # Verify basic tool execution continues to pass cleanly
        res_create = execute_action({"tool": "create_file", "arguments": {"path": "calculator.py", "content": "print('calc')\n"}})
        self.assertTrue(res_create["success"])

        res_update = execute_action({"tool": "update_file", "arguments": {"path": "calculator.py", "content": "print('calc v2')\n"}})
        self.assertTrue(res_update["success"])

        res_run = execute_action({"tool": "run_command", "arguments": {"command": "python calculator.py"}})
        self.assertTrue(res_run["success"])
        self.assertIn("calc v2", res_run["result"]["stdout"])


if __name__ == "__main__":
    unittest.main()
