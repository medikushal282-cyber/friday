import os
import sys
import unittest
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.workspace.manager import WorkspaceManager
from app.workspace.knowledge import get_knowledge_store
from app.graph.workflow import execute_run_task
from app.graph.nodes.orchestrator import orchestrator_node, build_dynamic_fallback_plan
from app.graph.nodes.executor import executor_node

class TestPlanningAutonomousExecution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("GROQ_API_KEY", "dummy_groq_key_for_unit_tests")
        cls.ws = WorkspaceManager()
        cls.root = cls.ws.root_path
        cls.kb = get_knowledge_store()

    def setUp(self):
        self.kb.clear()

    def tearDown(self):
        for fname in [
            "employees.csv", "employee_report.py", "department_report.json",
            "notes.txt", "word_stats.py", "word_stats.json",
            "README.md", "sample.csv", "context_test.py", "main.py"
        ]:
            abs_path = os.path.join(self.root, fname)
            if os.path.exists(abs_path):
                try:
                    os.remove(abs_path)
                except Exception:
                    pass

    # 1. DYNAMIC PLAN GENERATION
    def test_1_dynamic_plan_generation_different_objectives(self):
        obj1 = "Create employees.csv, author employee_report.py, run it to write department_report.json, and create README.md."
        obj2 = "Create notes.txt, author word_stats.py, run it to write word_stats.json, and create README.md."

        plan1 = build_dynamic_fallback_plan(obj1, [])
        plan2 = build_dynamic_fallback_plan(obj2, [])

        targets1 = [s["target"] for s in plan1]
        targets2 = [s["target"] for s in plan2]

        self.assertIn("employees.csv", targets1)
        self.assertIn("employee_report.py", targets1)
        self.assertIn("notes.txt", targets2)
        self.assertIn("word_stats.py", targets2)

    # 2. PLAN STEP STRUCTURE
    def test_2_plan_step_structure(self):
        obj = "Create notes.txt and word_stats.py."
        plan = build_dynamic_fallback_plan(obj, [])
        for step in plan:
            self.assertIn("id", step)
            self.assertIn("description", step)
            self.assertIn("status", step)
            self.assertIn("action", step)
            self.assertIn("agent", step)
            self.assertIn("depends_on", step)

    # 3. DEPENDENCY ORDERING
    def test_3_dependency_ordering(self):
        obj = "Create employees.csv and employee_report.py."
        plan = build_dynamic_fallback_plan(obj, [])
        
        # Verify step_2 (employees.csv) depends on step_1
        step_map = {s["id"]: s for s in plan}
        step_2 = step_map["step_2"]
        self.assertIn("step_1", step_2["depends_on"])

    # 4. MULTI-STEP AUTONOMOUS EXECUTION
    def test_4_multi_step_autonomous_execution(self):
        run_id = "test_auto_exec_001"
        obj = "Create a script named main.py that prints Hello Fraiday."
        runs_db = {run_id: {"run_id": run_id, "objective": obj, "status": "pending", "state": {}}}

        asyncio.run(execute_run_task(run_id, obj, runs_db))

        state = runs_db[run_id]["state"]
        self.assertEqual(runs_db[run_id]["status"], "completed")

        # Verify multiple steps completed automatically
        completed_steps = [s for s in state.get("plan", []) if s.get("status") == "completed"]
        self.assertGreaterEqual(len(completed_steps), 2)

    # 5. CONTEXT PROPAGATION
    def test_5_context_propagation(self):
        run_id = "test_context_prop"
        obj = "Create notes.txt and word_stats.py."
        state = {
            "run_id": run_id,
            "objective": obj,
            "plan": [
                {"id": "step_1", "description": "List dir", "agent": "executor", "action": "LIST_DIRECTORY", "target": ".", "depends_on": [], "status": "pending"},
                {"id": "step_2", "description": "Create notes.txt", "agent": "executor", "action": "CREATE_FILE", "target": "notes.txt", "depends_on": ["step_1"], "status": "pending"}
            ],
            "observations": [],
            "artifacts": []
        }

        res_state = asyncio.run(executor_node(state))
        
        # Verify observations populated for step 1 and step 2
        obs_tools = [o.get("tool") for o in res_state.get("observations", [])]
        self.assertIn("list_directory", obs_tools)
        self.assertTrue(os.path.exists(os.path.join(self.root, "notes.txt")))

    # 6. KNOWLEDGE PROPAGATION (ACTIVITY 3 INTEGRATION)
    def test_6_knowledge_propagation(self):
        self.kb.save_finding({
            "query": "Python CSV to JSON",
            "finding": "Use csv.DictReader and json.dumps",
            "source": "Python 3 Docs",
            "relevance": "Standard pattern"
        })

        run_id = "test_kb_prop"
        obj = "Create a script named csv_to_json.py that converts CSV to JSON using Python standard library."
        runs_db = {run_id: {"run_id": run_id, "objective": obj, "status": "pending", "state": {}}}

        asyncio.run(execute_run_task(run_id, obj, runs_db))

        state = runs_db[run_id]["state"]
        res_list = state.get("research", [])
        self.assertGreater(len(res_list), 0)
        self.assertEqual(res_list[0].get("source"), "Python 3 Docs")

    # 7. ARTIFACT TRACKING
    def test_7_artifact_tracking(self):
        run_id = "test_artifact_tracking"
        obj = "Create notes.txt and README.md."
        runs_db = {run_id: {"run_id": run_id, "objective": obj, "status": "pending", "state": {}}}

        asyncio.run(execute_run_task(run_id, obj, runs_db))

        state = runs_db[run_id]["state"]
        artifacts = [a.get("path") for a in state.get("artifacts", [])]
        self.assertIn("README.md", artifacts)

if __name__ == "__main__":
    unittest.main()
