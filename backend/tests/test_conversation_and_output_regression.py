import os
import sys
import unittest
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.workspace.manager import WorkspaceManager
from app.workspace.tools import execute_action
from app.graph.workflow import execute_run_task
from app.api.runs import CONVERSATIONS_DB, RUNS_DB, create_run, RunRequest

class TestConversationAndOutputRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("GROQ_API_KEY", "dummy_groq_key_for_unit_tests")
        cls.ws = WorkspaceManager()
        cls.root = cls.ws.root_path

    def setUp(self):
        CONVERSATIONS_DB.clear()
        RUNS_DB.clear()
        for fname in ["hello.py", "hello_output_test.py", "script_a.py", "script_b.py", "ecommerce_index.html"]:
            abs_path = os.path.join(self.root, fname)
            if os.path.exists(abs_path):
                try:
                    os.remove(abs_path)
                except Exception:
                    pass

    def tearDown(self):
        for fname in ["hello.py", "hello_output_test.py", "script_a.py", "script_b.py", "ecommerce_index.html"]:
            abs_path = os.path.join(self.root, fname)
            if os.path.exists(abs_path):
                try:
                    os.remove(abs_path)
                except Exception:
                    pass

    # TEST 1 — OUTPUT
    def test_1_execution_output_capture(self):
        async def _test():
            run_id = "test_output_cap_001"
            objective = "Create hello_output_test.py that prints Hello from Fraiday Output Test."
            runs_db = {run_id: {"run_id": run_id, "objective": objective, "status": "pending", "state": {}}}

            await execute_run_task(run_id, objective, runs_db)
            
            state = runs_db[run_id]["state"]
            self.assertEqual(runs_db[run_id]["status"], "completed")

            proc_obs = [o for o in state.get("observations", []) if "hello_output_test" in str(o.get("target", "")) or "hello_output_test" in str(o.get("command", ""))]
            self.assertGreater(len(proc_obs), 0)
            
            last_proc = proc_obs[-1]
            self.assertEqual(last_proc.get("exit_code"), 0)
            self.assertTrue(len(last_proc.get("stdout", "").strip()) > 0)
            self.assertEqual(last_proc.get("stderr", ""), "")

            list_obs = [o for o in state.get("observations", []) if o.get("action") == "LIST_DIRECTORY"]
            if list_obs:
                self.assertEqual(list_obs[0].get("stdout", ""), "")
                self.assertNotEqual(last_proc.get("stdout", ""), list_obs[0].get("stdout", ""))

        asyncio.run(_test())

    # TEST 2 — SAME CONVERSATION FOLLOW-UP
    def test_2_same_conversation_follow_up(self):
        async def _test():
            res1 = await create_run(RunRequest(objective="Create hello.py that prints Hello."))
            conv_id = res1["conversation_id"]
            run_id1 = res1["run_id"]

            await asyncio.sleep(2.5)

            res2 = await create_run(RunRequest(objective="Modify it so it prints Hello from the updated script.", conversation_id=conv_id))
            run_id2 = res2["run_id"]
            self.assertEqual(res2["conversation_id"], conv_id)
            self.assertNotEqual(run_id1, run_id2)

            await asyncio.sleep(2.5)

            conv_data = CONVERSATIONS_DB[conv_id]
            user_msgs = [m for m in conv_data["messages"] if m["role"] == "user"]
            self.assertEqual(len(user_msgs), 2)
            self.assertEqual(user_msgs[0]["content"], "Create hello.py that prints Hello.")
            self.assertIn("Modify it", user_msgs[1]["content"])

            state2 = RUNS_DB[run_id2]["state"]
            state1 = RUNS_DB[run_id1]["state"]
            self.assertNotEqual(state2.get("plan"), state1.get("plan"))

        asyncio.run(_test())

    # TEST 3 — NEW CONVERSATION ISOLATION
    def test_3_new_conversation_isolation(self):
        async def _test():
            res1 = await create_run(RunRequest(objective="Create hello.py that prints Hello from Conv A."))
            conv_a = res1["conversation_id"]
            
            await asyncio.sleep(2.5)

            res2 = await create_run(RunRequest(objective="Create a file named ecommerce_index.html with basic HTML markup."))
            conv_b = res2["conversation_id"]
            run_b = res2["run_id"]

            self.assertNotEqual(conv_a, conv_b)

            await asyncio.sleep(2.5)

            state_b = RUNS_DB[run_b]["state"]
            artifacts_b = [a.get("path") for a in state_b.get("artifacts", [])]
            self.assertNotIn("hello.py", artifacts_b)

        asyncio.run(_test())

    # TEST 4 — MULTIPLE COMMAND OUTPUTS
    def test_4_multiple_command_outputs(self):
        async def _test():
            execute_action({"tool": "create_file", "arguments": {"path": "script_a.py", "content": "print('Output A')\n"}})
            execute_action({"tool": "create_file", "arguments": {"path": "script_b.py", "content": "print('Output B')\n"}})

            run_id = "test_multi_cmd_004"
            objective = "Execute script_a.py and execute script_b.py"
            runs_db = {run_id: {"run_id": run_id, "objective": objective, "status": "pending", "state": {}}}

            await execute_run_task(run_id, objective, runs_db)
            state = runs_db[run_id]["state"]

            proc_obs = [o for o in state.get("observations", []) if o.get("action") == "RUN_COMMAND" or o.get("tool") == "run_command" or "exit_code" in o]
            self.assertGreaterEqual(len(proc_obs), 1)

            for o in proc_obs:
                self.assertIn("stdout", o)
                self.assertIn("exit_code", o)
                self.assertEqual(o["exit_code"], 0)

        asyncio.run(_test())

if __name__ == "__main__":
    unittest.main()
