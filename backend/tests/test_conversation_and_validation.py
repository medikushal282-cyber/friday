import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
import unittest

from app.graph.nodes.orchestrator import detect_objective_type
from app.graph.nodes.validator import validator_node
from app.graph.workflow import execute_run_task

class TestConversationalGating(unittest.TestCase):
    def test_hi_is_conversation(self):
        for inp in ["hi", "hello", "hey", "thanks", "thank you", "good morning", "good afternoon", "what's up", "whats up", "how are you"]:
            self.assertEqual(detect_objective_type(inp), "conversation", msg=f"Failed for {inp!r}")

    def test_create_not_conversation(self):
        self.assertEqual(detect_objective_type("Create a Python script that prints hello"), "create")
        self.assertEqual(detect_objective_type("Create a Python script that prints 1 to 10"), "create")

    def test_research_not_conversation(self):
        self.assertEqual(detect_objective_type("Find the current stable Python version"), "research")

    def test_hi_no_workspace_mutation(self):
        async def run():
            RUNS_DB = {}
            run_id = "run_test_hi"
            RUNS_DB[run_id] = {"run_id": run_id, "objective": "hi", "status": "pending", "state": {}}
            await execute_run_task(run_id, "hi", RUNS_DB, [], lambda x: None)
            state = RUNS_DB[run_id]["state"]
            self.assertEqual(state.get("objective_type"), "conversation")
            self.assertEqual(len(state.get("observations", [])), 0)
            self.assertEqual(len(state.get("artifacts", [])), 0)
            self.assertEqual(len(state.get("validation_results", [])), 0)
            self.assertEqual(state.get("current_step"), "end")
            self.assertIn("response", state)
        asyncio.run(run())

    def test_hello_execution_still_works_via_mock(self):
        # Ensure create objective still enters pipeline (no conversation block)
        async def run():
            RUNS_DB = {}
            run_id = "run_test_create"
            # We mock Groq by allowing fallback plan; we just check orchestrator classification
            from app.graph.nodes.orchestrator import orchestrator_node
            state = {"run_id": run_id, "objective": "Create a Python script that prints hello", "workspace": {}, "conversation_context": [], "plan": [], "current_step": "orchestrator", "research": [], "tool_calls": [], "observations": [], "artifacts": [], "validation_results": [], "status": "started", "error": None, "retry_count": 0, "max_retries": 3, "recovery_history": [], "knowledge_matches": [], "knowledge_sources": [], "recovery_mode": False, "approval_required": False, "approval_status": "none", "approval_request": None}
            res = await orchestrator_node(state)
            self.assertEqual(res.get("objective_type"), "create")
            self.assertEqual(res.get("current_step"), "researcher")
            self.assertGreater(len(res.get("plan", [])), 0)
        asyncio.run(run())

class TestValidatorInvariant(unittest.TestCase):
    def test_exit_code_1_is_failure(self):
        async def run():
            state = {"run_id": "test", "objective": "run broken", "observations": [{"exit_code": 1, "stdout": "", "stderr": "TypeError: exec() arg 1 must be a string", "tool": "run_command"}], "validation_results": [], "approval_required": False}
            res = await validator_node(state)
            r = res["validation_results"][-1]
            self.assertFalse(r["valid"])
            self.assertEqual(r["exit_code"], 1)
            self.assertIn("TypeError", r["reason"])
            self.assertIn("stderr", r)
        asyncio.run(run())

    def test_exit_code_0_with_stdout_is_success(self):
        async def run():
            state = {"run_id": "test", "objective": "print hello", "observations": [{"exit_code": 0, "stdout": "hello", "stderr": "", "tool": "run_command"}], "validation_results": [], "approval_required": False}
            res = await validator_node(state)
            self.assertTrue(res["validation_results"][-1]["valid"])
        asyncio.run(run())

    def test_exit_code_missing_is_failure(self):
        async def run():
            state = {"run_id": "test", "objective": "run", "observations": [{"stdout": "something", "stderr": "", "tool": "run_command"}], "validation_results": [], "approval_required": False}
            res = await validator_node(state)
            self.assertFalse(res["validation_results"][-1]["valid"])
        asyncio.run(run())

    def test_stderr_included_on_failure(self):
        async def run():
            state = {"run_id": "test", "objective": "hi", "observations": [{"exit_code": 1, "stdout": "", "stderr": "Traceback: File \"main.py\", line 2, in <module> exec(code) TypeError: exec() arg 1 must be a string", "tool": "run_command"}], "validation_results": [], "approval_required": False}
            res = await validator_node(state)
            r = res["validation_results"][-1]
            self.assertFalse(r["valid"])
            self.assertEqual(r["exit_code"], 1)
            self.assertIn("TypeError", r["stderr"])
        asyncio.run(run())

if __name__ == "__main__":
    unittest.main()
