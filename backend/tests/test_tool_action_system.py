import os
import sys
import unittest
import asyncio
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.workspace.manager import WorkspaceManager, PathSecurityError
from app.workspace.tools import (
    execute_action,
    execute_tool,
    validate_action_schema,
    tool_list_directory,
    tool_read_file,
    tool_create_file,
    tool_update_file,
    tool_delete_file,
    tool_run_command,
    tool_inspect_runtime
)
from app.graph.nodes.executor import executor_node

class TestToolActionSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("GROQ_API_KEY", "dummy_groq_key_for_unit_tests")
        cls.ws = WorkspaceManager()
        cls.root = cls.ws.root_path
        cls.test_file = "test_tool_action_file.py"
        cls.abs_test_file = os.path.join(cls.root, cls.test_file)

    def tearDown(self):
        if os.path.exists(self.abs_test_file):
            try:
                os.remove(self.abs_test_file)
            except Exception:
                pass

    # TEST 1: list_directory works
    def test_1_list_directory(self):
        action = {"tool": "list_directory", "arguments": {"path": "."}}
        res = execute_action(action)
        self.assertTrue(res["success"])
        self.assertEqual(res["tool"], "list_directory")
        self.assertIsNotNone(res["result"])
        self.assertIn("entries", res["result"])
        self.assertIsNone(res["error"])

    # TEST 2: read_file works
    def test_2_read_file(self):
        # First write a file directly to test read
        with open(self.abs_test_file, "w", encoding="utf-8") as f:
            f.write("print('hello tool system')\n")

        action = {"tool": "read_file", "arguments": {"path": self.test_file}}
        res = execute_action(action)
        self.assertTrue(res["success"])
        self.assertEqual(res["tool"], "read_file")
        self.assertIsNotNone(res["result"])
        self.assertIn("print('hello tool system')", res["result"]["content"])
        self.assertIsNone(res["error"])

    # TEST 3: create_file creates a real file
    def test_3_create_file(self):
        content = "print('created by tool action')\n"
        action = {
            "tool": "create_file",
            "arguments": {
                "path": self.test_file,
                "content": content
            }
        }
        res = execute_action(action)
        self.assertTrue(res["success"])
        self.assertEqual(res["tool"], "create_file")
        self.assertTrue(os.path.exists(self.abs_test_file))
        
        with open(self.abs_test_file, "r", encoding="utf-8") as f:
            read_back = f.read()
        self.assertEqual(read_back, content)

    # TEST 4: update_file modifies the real file
    def test_4_update_file(self):
        # Create initial file
        execute_action({"tool": "create_file", "arguments": {"path": self.test_file, "content": "initial\n"}})
        
        # Update file
        updated_content = "initial\nupdated_content_line\n"
        action = {
            "tool": "update_file",
            "arguments": {
                "path": self.test_file,
                "content": updated_content
            }
        }
        res = execute_action(action)
        self.assertTrue(res["success"])
        self.assertEqual(res["tool"], "update_file")
        self.assertIn("+1 / -0 lines", res["result"]["diff"])
        
        with open(self.abs_test_file, "r", encoding="utf-8") as f:
            read_back = f.read()
        self.assertEqual(read_back, updated_content)

    # TEST 5: run_command executes a permitted command
    def test_5_run_command(self):
        cmd = 'python -c "print(\'tool command success\')"'
        action = {
            "tool": "run_command",
            "arguments": {
                "command": cmd
            }
        }
        res = execute_action(action)
        self.assertTrue(res["success"])
        self.assertEqual(res["tool"], "run_command")
        self.assertEqual(res["result"]["exit_code"], 0)
        self.assertIn("tool command success", res["result"]["stdout"])

    # TEST 6: invalid/outside-workspace paths are rejected
    def test_6_security_outside_workspace_rejected(self):
        action_traversal = {"tool": "read_file", "arguments": {"path": "../../../outside.txt"}}
        res = execute_action(action_traversal)
        self.assertFalse(res["success"])
        self.assertIsNotNone(res["error"])
        self.assertEqual(res["error"]["code"], "PATH_SECURITY_ERROR")

        action_abs = {"tool": "create_file", "arguments": {"path": "C:\\Windows\\evil.txt", "content": "bad"}}
        res_abs = execute_action(action_abs)
        self.assertFalse(res_abs["success"])
        self.assertIsNotNone(res_abs["error"])
        self.assertEqual(res_abs["error"]["code"], "PATH_SECURITY_ERROR")

    # TEST 7: tool failure produces a structured failure result
    def test_7_tool_failure_structured(self):
        # 1. Non-existent file read
        res_missing = execute_action({"tool": "read_file", "arguments": {"path": "non_existent_file_9999.py"}})
        self.assertFalse(res_missing["success"])
        self.assertEqual(res_missing["tool"], "read_file")
        self.assertIsNone(res_missing["result"])
        self.assertEqual(res_missing["error"]["code"], "FILE_NOT_FOUND")
        self.assertIn("does not exist", res_missing["error"]["message"])

        # 2. Denied command
        res_denied = execute_action({"tool": "run_command", "arguments": {"command": "format C:"}})
        self.assertFalse(res_denied["success"])
        self.assertEqual(res_denied["tool"], "run_command")
        self.assertEqual(res_denied["error"]["code"], "COMMAND_DENIED")

    # TEST 8: an agent run can execute at least one real tool and receive the result
    def test_8_agent_node_tool_execution(self):
        state = {
            "run_id": "test_run_001",
            "objective": "Create test_tool_action_file.py with print('agent tool exec'), run it, and verify output.",
            "workspace": {"root_path": self.root},
            "conversation_context": [],
            "plan": [
                {"id": "step_1", "agent": "executor", "action": "create_file", "description": "Create test file"},
                {"id": "step_2", "agent": "executor", "action": "run_command", "description": "Run test file"}
            ],
            "current_step": "executor",
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
            return await executor_node(state)

        updated_state = asyncio.run(run_node())
        self.assertGreater(len(updated_state.get("tool_calls", [])), 0)
        first_tool_call = updated_state["tool_calls"][0]
        self.assertIn("action", first_tool_call)
        self.assertIn("result", first_tool_call)
        self.assertTrue(first_tool_call["result"]["success"])

    # TEST 9: existing run/SSE behavior still works
    def test_9_existing_execute_tool_compatibility(self):
        # Verify legacy signature execute_tool("read_file", path=...) still works seamlessly
        with open(self.abs_test_file, "w", encoding="utf-8") as f:
            f.write("legacy compat\n")

        res = execute_tool("read_file", path=self.test_file)
        self.assertTrue(res["success"])
        self.assertEqual(res["path"], self.test_file)
        self.assertEqual(res["content"], "legacy compat\n")


if __name__ == "__main__":
    unittest.main()
