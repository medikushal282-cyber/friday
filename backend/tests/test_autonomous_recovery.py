import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

import asyncio
import unittest
from unittest.mock import patch, MagicMock

from app.graph.nodes.validator import validator_node
from app.graph.nodes.recovery import recovery_node
from app.graph.workflow import execute_run_task
from app.workspace.tools import execute_tool
from app.workspace.manager import get_workspace_manager


class TestAutonomousRecovery(unittest.TestCase):
    def setUp(self):
        self.ws = get_workspace_manager()

    def tearDown(self):
        for fname in ["test_broken_prog.py", "test_unrepairable.py", "test_disk_target.py"]:
            full_path = self.ws.resolve_path(fname)
            if os.path.exists(full_path):
                try:
                    os.remove(full_path)
                except Exception:
                    pass

    def test_3_successful_program_recovery_not_entered(self):
        """Test 3: Successful program -> recovery is not entered."""
        async def run():
            state = {
                "run_id": "test_success_run",
                "objective": "calculate factorial and print 120",
                "observations": [{
                    "filename": "factorial.py",
                    "command": "python factorial.py",
                    "stdout": "120",
                    "stderr": "",
                    "exit_code": 0,
                    "tool": "run_command"
                }],
                "validation_results": [],
                "approval_required": False,
                "recovery_mode": False,
                "retry_count": 0,
                "max_retries": 3,
            }
            res = await validator_node(state)
            last_val = res["validation_results"][-1]
            self.assertTrue(last_val["valid"])
            self.assertEqual(res["current_step"], "end")
            self.assertFalse(res.get("recovery_mode", False))
        asyncio.run(run())

    def test_4_validator_failure_correctly_routes_to_recovery(self):
        """Test 4: Validator failure correctly routes to recovery."""
        async def run():
            state = {
                "run_id": "test_fail_route_run",
                "objective": "calculate factorial and print 120",
                "observations": [{
                    "filename": "factorial.py",
                    "command": "python factorial.py",
                    "stdout": "",
                    "stderr": "NameError: name 'factrial' is not defined",
                    "exit_code": 1,
                    "tool": "run_command"
                }],
                "validation_results": [],
                "approval_required": False,
                "retry_count": 0,
                "max_retries": 3,
            }
            res = await validator_node(state)
            last_val = res["validation_results"][-1]
            self.assertFalse(last_val["valid"])
            self.assertEqual(res["current_step"], "recovery")
        asyncio.run(run())

    def test_5_recovery_updates_actual_workspace_file(self):
        """Test 5: Recovery updates the actual workspace file."""
        async def run():
            fname = "test_disk_target.py"
            broken_code = "print('broken version')\n"
            fixed_code = "print('repaired version')\n"

            # 1. Create broken file on disk
            execute_tool("create_file", path=fname, content=broken_code)

            state = {
                "run_id": "test_disk_run",
                "objective": "print repaired version",
                "observations": [{
                    "filename": fname,
                    "command": f"python {fname}",
                    "stdout": "broken version",
                    "stderr": "Error: unexpected output",
                    "exit_code": 1
                }],
                "validation_results": [{"valid": False, "reason": "Expected repaired version"}],
                "retry_count": 0,
                "max_retries": 3,
                "artifacts": [],
                "approval_required": False
            }

            # 2. Mock Groq returning the fixed code
            with patch("app.graph.nodes.recovery.call_groq", return_value=fixed_code):
                res = await recovery_node(state)

            # 3. Verify the file on disk was physically updated
            read_res = execute_tool("read_file", path=fname)
            self.assertTrue(read_res.get("success"))
            self.assertIn("repaired version", read_res.get("content"))
            self.assertEqual(res["current_step"], "validator")
            self.assertTrue(res.get("recovery_mode"))
            self.assertEqual(res.get("retry_count"), 1)
        asyncio.run(run())

    def test_6_final_observation_from_corrected_execution(self):
        """Test 6: Final observation comes from the corrected execution."""
        async def run():
            fname = "test_broken_prog.py"
            broken_code = "prnt(120)\n"
            fixed_code = "print(120)\n"

            execute_tool("create_file", path=fname, content=broken_code)

            state = {
                "run_id": "test_obs_run",
                "objective": "print 120",
                "observations": [{
                    "filename": fname,
                    "command": f"python {fname}",
                    "stdout": "",
                    "stderr": "NameError: name 'prnt' is not defined",
                    "exit_code": 1
                }],
                "validation_results": [{"valid": False, "reason": "NameError: name 'prnt' is not defined"}],
                "retry_count": 0,
                "max_retries": 3,
                "artifacts": [],
                "approval_required": False
            }

            with patch("app.graph.nodes.recovery.call_groq", return_value=fixed_code):
                res = await recovery_node(state)

            new_obs = res["observations"][-1]
            self.assertEqual(new_obs["filename"], fname)
            self.assertEqual(new_obs["exit_code"], 0)
            self.assertIn("120", new_obs["stdout"])
            self.assertEqual(new_obs["recovery_attempt"], 1)
        asyncio.run(run())

    def test_1_broken_program_recovery_success(self):
        """Test 1: Broken program -> recovery -> success lifecycle."""
        async def run():
            fname = "test_broken_prog.py"
            broken_code = "def factorial(n):\n    if n <= 1: return 1\n    return n * factrial(n - 1)\nprint(factorial(5))\n"
            fixed_code = "def factorial(n):\n    if n <= 1: return 1\n    return n * factorial(n - 1)\nprint(factorial(5))\n"

            execute_tool("create_file", path=fname, content=broken_code)

            RUNS_DB = {
                "run_lifecycle": {
                    "run_id": "run_lifecycle",
                    "objective": f"Create a Python program {fname} that is supposed to print 120, but intentionally generate a NameError bug and let recovery fix it.",
                    "status": "pending",
                    "state": {}
                }
            }

            with patch("app.graph.nodes.recovery.call_groq", return_value=fixed_code):
                await execute_run_task("run_lifecycle", RUNS_DB["run_lifecycle"]["objective"], RUNS_DB)

            final_run = RUNS_DB["run_lifecycle"]
            self.assertEqual(final_run["status"], "completed")
            final_state = final_run["state"]
            self.assertTrue(final_state["validation_results"][-1]["valid"])
            self.assertEqual(final_state["validation_results"][-1]["exit_code"], 0)
            self.assertIn("120", final_state["observations"][-1]["stdout"])
            self.assertEqual(final_state["retry_count"], 1)
        asyncio.run(run())

    def test_2_broken_program_unrepairable_exhausted(self):
        """Test 2: Broken program that cannot be repaired -> stops at max retries."""
        async def run():
            fname = "test_unrepairable.py"
            broken_code = "raise RuntimeError('Permanent fatal error')\n"

            execute_tool("create_file", path=fname, content=broken_code)

            RUNS_DB = {
                "run_unrepairable": {
                    "run_id": "run_unrepairable",
                    "objective": f"Create a Python program {fname} that prints 120 with an intentional error and fix it.",
                    "status": "pending",
                    "state": {}
                }
            }

            # Mock Groq to continuously return broken code that raises RuntimeError
            with patch("app.graph.nodes.recovery.call_groq", return_value=broken_code):
                await execute_run_task("run_unrepairable", RUNS_DB["run_unrepairable"]["objective"], RUNS_DB)

            final_run = RUNS_DB["run_unrepairable"]
            self.assertEqual(final_run["status"], "failed")
            final_state = final_run["state"]
            self.assertTrue(final_state.get("recovery_exhausted"))
            self.assertEqual(final_state.get("retry_count"), 3)
            self.assertFalse(final_state["validation_results"][-1]["valid"])
        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
