import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import unittest
from unittest.mock import patch
import asyncio

from app.api.runs import build_continuation_context
from app.graph.nodes.executor import executor_node


class TestContinuationContext(unittest.TestCase):
    def test_context_contains_previous_run_material_and_new_objective(self):
        previous = {
            "run_id": "run_previous",
            "objective": "Create factorial.py",
            "state": {
                "plan": [{"id": "step_1", "action": "create_file"}],
                "observations": [{"filename": "factorial.py", "stdout": "120\n"}],
                "artifacts": [{"type": "file", "path": "factorial.py", "operation": "created"}],
                "workspace": {"root_path": "D:\\projects\\Friday\\friday"},
            },
        }

        context = build_continuation_context(previous, "Also print factorial(6).")

        self.assertEqual(context["previous_run_id"], "run_previous")
        self.assertEqual(context["objective"], "Also print factorial(6).")
        self.assertEqual(context["previous_objective"], "Create factorial.py")
        self.assertEqual(context["artifacts"][0]["path"], "factorial.py")
        self.assertEqual(context["observations"][0]["stdout"], "120\n")
        self.assertEqual(context["workspace"]["root_path"], "D:\\projects\\Friday\\friday")

    def test_continuation_reads_existing_file_before_update(self):
        events = []
        calls = []

        async def capture(*args, **kwargs):
            events.append(args[1])

        def fake_tool(tool, **kwargs):
            calls.append(tool)
            if tool == "read_file":
                return {"success": True, "content": "print(120)\n"}
            if tool == "update_file":
                return {"success": True, "lines": 2, "diff": "updated"}
            return {"success": True, "stdout": "120\n720\n", "stderr": "", "exit_code": 0, "duration": 0.01, "command": "python factorial.py"}

        async def run():
            state = {
                "run_id": "run_continuation",
                "objective": "Also print factorial(6).",
                "workspace": {},
                "conversation_context": [{"artifacts": [{"path": "factorial.py"}]}],
                "plan": [
                    {"id": "step_1", "agent": "executor", "action": "update_file"},
                    {"id": "step_2", "agent": "executor", "action": "run_command"},
                ],
                "observations": [], "artifacts": [], "continuation_mode": True,
            }
            with patch("app.graph.nodes.executor.emit", capture), patch("app.graph.nodes.executor.execute_tool", fake_tool), patch("app.graph.nodes.executor.call_groq", return_value="print(120)\nprint(720)\n"):
                await executor_node(state)

        asyncio.run(run())
        self.assertEqual(calls[:3], ["read_file", "update_file", "run_command"])
        self.assertLess(events.index("file_read"), events.index("file_updated"))


if __name__ == "__main__":
    unittest.main()
