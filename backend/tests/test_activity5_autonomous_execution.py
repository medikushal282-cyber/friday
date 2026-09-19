import os
import sys
import unittest
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.workspace.manager import WorkspaceManager
from app.workspace.tools import execute_action, classify_failure, validate_python_source
from app.workspace.artifact_cleaner import extract_and_validate_artifact
from app.graph.workflow import execute_run_task
from app.graph.controller import (
    MAX_AUTONOMOUS_ITERATIONS,
    MAX_REPLANS,
    MAX_RECOVERY_ATTEMPTS,
    create_structured_observation,
    detect_plan_obsolescence,
    evaluate_next_decision,
    DECISION_CONTINUE,
    DECISION_RECOVER,
    DECISION_REPLAN,
    DECISION_VALIDATE,
    DECISION_WAIT_FOR_APPROVAL,
    DECISION_COMPLETE,
    DECISION_FAIL
)
from app.graph.nodes.orchestrator import build_dynamic_fallback_plan

class TestActivity5AutonomousExecution(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("GROQ_API_KEY", "dummy_groq_key_for_unit_tests")
        cls.ws = WorkspaceManager()
        cls.root = cls.ws.root_path

    def tearDown(self):
        for fname in [
            "hello.py", "sample_csv.csv", "employees.csv", "employee_report.py",
            "department_report.json", "README_employee_report.md", "notes.txt",
            "test_script.py", "delete_me.txt"
        ]:
            abs_path = os.path.join(self.root, fname)
            if os.path.exists(abs_path):
                try:
                    os.remove(abs_path)
                except Exception:
                    pass

    # A. SUCCESSFUL MULTI-STEP EXECUTION
    def test_a_successful_multistep_execution(self):
        run_id = "test_a_multi"
        obj = 'Create a script named hello.py that prints "Hello Fraiday" and execute it.'
        runs_db = {run_id: {"run_id": run_id, "objective": obj, "status": "pending", "state": {}}}

        asyncio.run(execute_run_task(run_id, obj, runs_db))
        self.assertEqual(runs_db[run_id]["status"], "completed")

    # B. OBSERVATION AFTER TOOL CALL
    def test_b_observation_after_tool_call(self):
        obs = create_structured_observation("LIST_DIRECTORY", ".", True, {"entries": [{"name": "a.txt"}]}, "step_1")
        self.assertEqual(obs["action"], "LIST_DIRECTORY")
        self.assertTrue(obs["success"])
        self.assertIn("a.txt", obs["summary"])
        self.assertEqual(obs["step_id"], "step_1")

    # C. SUCCESSFUL COMPLETION
    def test_c_successful_completion(self):
        run_id = "test_c_comp"
        obj = 'Create notes.txt with runtime notes.'
        runs_db = {run_id: {"run_id": run_id, "objective": obj, "status": "pending", "state": {}}}

        asyncio.run(execute_run_task(run_id, obj, runs_db))
        self.assertEqual(runs_db[run_id]["status"], "completed")
        self.assertTrue(os.path.exists(os.path.join(self.root, "notes.txt")))

    # D. SYNTAX-ERROR RECOVERY
    def test_d_syntax_error_recovery(self):
        kind = classify_failure(1, "", "SyntaxError: invalid syntax (line 1)")
        self.assertEqual(kind, "syntax_error")

        state = {
            "autonomous_iteration_count": 1,
            "replan_count": 0,
            "recovery_attempts": 0,
            "observations": [{"success": False, "kind": "syntax_error", "stderr": "SyntaxError: invalid syntax"}]
        }
        dec, reason = evaluate_next_decision(state)
        self.assertEqual(dec, DECISION_RECOVER)

    # E. MISSING-FILE RECOVERY
    def test_e_missing_file_recovery(self):
        kind = classify_failure(1, "", "FileNotFoundError: [Errno 2] No such file: 'data.csv'")
        self.assertEqual(kind, "missing_file")

    # F. MISSING-ARGUMENT RECOVERY
    def test_f_missing_argument_recovery(self):
        kind = classify_failure(2, "", "usage: script.py [-h] input output\nerror: required: input, output")
        self.assertEqual(kind, "missing_arguments")

    # G. VALIDATION FAILURE RECOVERY
    def test_g_validation_failure_recovery(self):
        kind = classify_failure(1, "bad output", "failed objective requirement validation: missing expected text")
        self.assertEqual(kind, "validation_error")

    # H. STALE-PLAN DETECTION
    def test_h_stale_plan_detection(self):
        plan = [
            {"id": "step_1", "action": "LIST_DIRECTORY", "status": "completed"},
            {"id": "step_2", "action": "CREATE_FILE", "target": "sample_csv.csv", "status": "pending"}
        ]
        observations = [
            {"action": "LIST_DIRECTORY", "entries": ["sample_csv.csv"], "success": True}
        ]
        is_obsolete, obs_step_id, reason = detect_plan_obsolescence(plan, observations)
        self.assertTrue(is_obsolete)
        self.assertEqual(obs_step_id, "step_2")

    # I. RE-PLANNING
    def test_i_replanning(self):
        state = {
            "autonomous_iteration_count": 2,
            "replan_count": 0,
            "recovery_attempts": 0,
            "plan": [
                {"id": "step_1", "action": "LIST_DIRECTORY", "status": "completed"},
                {"id": "step_2", "action": "CREATE_FILE", "target": "employees.csv", "status": "pending"}
            ],
            "observations": [{"action": "LIST_DIRECTORY", "entries": ["employees.csv"], "success": True}]
        }
        dec, reason = evaluate_next_decision(state)
        self.assertEqual(dec, DECISION_REPLAN)

    # J. COMPLETED STEPS PRESERVED AFTER RE-PLAN
    def test_j_completed_steps_preserved_after_replan(self):
        plan = [
            {"id": "step_1", "action": "LIST_DIRECTORY", "status": "completed"},
            {"id": "step_2", "action": "CREATE_FILE", "target": "employees.csv", "status": "skipped"}
        ]
        preserved = [s for s in plan if s.get("status") in ["completed", "skipped"]]
        self.assertEqual(len(preserved), 2)
        self.assertEqual(preserved[0]["status"], "completed")
        self.assertEqual(preserved[1]["status"], "skipped")

    # K. OBSOLETE STEPS MARKED SKIPPED/REPLACED
    def test_k_obsolete_steps_marked_skipped(self):
        plan = [
            {"id": "step_1", "action": "LIST_DIRECTORY", "status": "completed"},
            {"id": "step_2", "action": "CREATE_FILE", "target": "sample_csv.csv", "status": "pending"}
        ]
        observations = [
            {"action": "LIST_DIRECTORY", "entries": ["sample_csv.csv"], "success": True}
        ]
        is_obsolete, obs_step_id, reason = detect_plan_obsolescence(plan, observations)
        for s in plan:
            if s["id"] == obs_step_id:
                s["status"] = "skipped"
                s["reason"] = reason

        self.assertEqual(plan[1]["status"], "skipped")

    # L. MAX AUTONOMOUS ITERATIONS
    def test_l_max_autonomous_iterations(self):
        state = {
            "autonomous_iteration_count": MAX_AUTONOMOUS_ITERATIONS,
            "replan_count": 0,
            "recovery_attempts": 0,
            "observations": []
        }
        dec, reason = evaluate_next_decision(state)
        self.assertEqual(dec, DECISION_FAIL)
        self.assertIn("Safety limit reached", reason)

    # M. MAX RE-PLANS
    def test_m_max_replans(self):
        state = {
            "autonomous_iteration_count": 5,
            "replan_count": MAX_REPLANS,
            "recovery_attempts": MAX_RECOVERY_ATTEMPTS,
            "observations": [{"success": False, "kind": "syntax_error"}]
        }
        dec, reason = evaluate_next_decision(state)
        self.assertEqual(dec, DECISION_FAIL)

    # N. MAX RECOVERY ATTEMPTS
    def test_n_max_recovery_attempts(self):
        state = {
            "autonomous_iteration_count": 4,
            "replan_count": 0,
            "recovery_attempts": MAX_RECOVERY_ATTEMPTS,
            "observations": [{"success": False, "kind": "syntax_error"}]
        }
        dec, reason = evaluate_next_decision(state)
        self.assertEqual(dec, DECISION_REPLAN)

    # O. APPROVAL-REQUIRED PAUSE
    def test_o_approval_required_pause(self):
        state = {
            "autonomous_iteration_count": 1,
            "approval_required": True,
            "observations": []
        }
        dec, reason = evaluate_next_decision(state)
        self.assertEqual(dec, DECISION_WAIT_FOR_APPROVAL)

    # P. FINAL VALIDATION REQUIRED
    def test_p_final_validation_required(self):
        state = {
            "autonomous_iteration_count": 3,
            "plan": [{"id": "step_1", "status": "completed"}],
            "observations": [{"action": "RUN_COMMAND", "success": True}],
            "validation_results": []
        }
        dec, reason = evaluate_next_decision(state)
        self.assertEqual(dec, DECISION_VALIDATE)

    # Q. NO INFINITE LOOP
    def test_q_no_infinite_loop(self):
        state = {
            "autonomous_iteration_count": MAX_AUTONOMOUS_ITERATIONS + 1,
            "replan_count": 10,
            "recovery_attempts": 10,
            "observations": []
        }
        dec, reason = evaluate_next_decision(state)
        self.assertEqual(dec, DECISION_FAIL)

    # R. STRUCTURED FAILURE CLASSIFICATION PRESERVED
    def test_r_structured_failure_classification_preserved(self):
        obs = create_structured_observation(
            action="RUN_COMMAND",
            target="report.py",
            success=False,
            exit_code=1,
            stderr="SyntaxError: invalid syntax",
            failure_type="syntax_error"
        )
        self.assertEqual(obs["kind"], "syntax_error")
        self.assertFalse(obs["success"])

    # S. RUNTIME ERROR CLASSIFICATION (NameError / AttributeError / TypeError)
    def test_s_runtime_error_classification(self):
        kind1 = classify_failure(1, "", "NameError: name 'insight' is not defined")
        self.assertEqual(kind1, "runtime_error")

        kind2 = classify_failure(1, "", "TypeError: unsupported operand type(s)")
        self.assertEqual(kind2, "runtime_error")

        kind3 = classify_failure(1, "", "AttributeError: 'str' object has no attribute 'foo'")
        self.assertEqual(kind3, "runtime_error")

    # T. REJECT CORRUPTED MODEL PREAMBLE IN PYTHON ARTIFACT
    def test_t_reject_corrupted_model_preamble(self):
        corrupted_path = os.path.join(self.root, "corrupted_test.py")
        with open(corrupted_path, "w", encoding="utf-8") as f:
            f.write("insight NameError: name 'insight' is not defined\nprint('hello')\n")

        val = validate_python_source("corrupted_test.py")
        self.assertFalse(val["valid"])
        self.assertEqual(val["kind"], "syntax_error")
        if os.path.exists(corrupted_path):
            os.remove(corrupted_path)

    # U. RUNTIME ARTIFACT REPAIR RECOVERY FLOW
    def test_u_runtime_artifact_repair(self):
        target_name = "autonomy_recovery_test.py"
        target_path = os.path.join(self.root, target_name)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write("insight NameError: name 'insight' is not defined\nprint('recovered')\n")

        run_id = "test_u_repair"
        obj = f"Create a script named {target_name} that prints recovered."
        runs_db = {run_id: {"run_id": run_id, "objective": obj, "status": "pending", "state": {}}}

        asyncio.run(execute_run_task(run_id, obj, runs_db))
        self.assertEqual(runs_db[run_id]["status"], "completed")

        with open(target_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("insight NameError", content)

    # PHASE 14 DETERMINISTIC TESTS (TESTS 1 - 12)
    def test_phase14_1_create_basic_html_file(self):
        run_id = "test_p14_1"
        obj = "can u generate a basic html file"
        runs_db = {run_id: {"run_id": run_id, "objective": obj, "status": "pending", "state": {}}}
        asyncio.run(execute_run_task(run_id, obj, runs_db))
        self.assertEqual(runs_db[run_id]["status"], "completed")
        self.assertTrue(os.path.exists(os.path.join(self.root, "index.html")))

    def test_phase14_2_html_with_heading_and_button(self):
        run_id = "test_p14_2"
        obj = "Create a basic HTML page named index.html with a heading and button."
        runs_db = {run_id: {"run_id": run_id, "objective": obj, "status": "pending", "state": {}}}
        asyncio.run(execute_run_task(run_id, obj, runs_db))
        self.assertEqual(runs_db[run_id]["status"], "completed")
        html_p = os.path.join(self.root, "index.html")
        self.assertTrue(os.path.exists(html_p))
        with open(html_p, "r", encoding="utf-8") as f:
            c = f.read().lower()
        self.assertTrue("h1" in c or "head" in c)
        self.assertTrue("button" in c)

    def test_phase14_3_html_and_css_linked(self):
        run_id = "test_p14_3"
        obj = "Create an HTML page named index.html and a stylesheet named styles.css. Link the stylesheet from the HTML."
        runs_db = {run_id: {"run_id": run_id, "objective": obj, "status": "pending", "state": {}}}
        asyncio.run(execute_run_task(run_id, obj, runs_db))
        self.assertEqual(runs_db[run_id]["status"], "completed")
        self.assertTrue(os.path.exists(os.path.join(self.root, "index.html")))
        self.assertTrue(os.path.exists(os.path.join(self.root, "styles.css")))

    def test_phase14_4_python_script_and_run(self):
        run_id = "test_p14_4"
        obj = "Create a Python script named hello.py that prints Hello Fraiday, run it, and verify the output."
        runs_db = {run_id: {"run_id": run_id, "objective": obj, "status": "pending", "state": {}}}
        asyncio.run(execute_run_task(run_id, obj, runs_db))
        self.assertEqual(runs_db[run_id]["status"], "completed")

    def test_phase14_5_json_config_file(self):
        run_id = "test_p14_5"
        obj = "Create a JSON file named config.json containing name Fraiday and version 1."
        runs_db = {run_id: {"run_id": run_id, "objective": obj, "status": "pending", "state": {}}}
        asyncio.run(execute_run_task(run_id, obj, runs_db))
        self.assertEqual(runs_db[run_id]["status"], "completed")
        self.assertTrue(os.path.exists(os.path.join(self.root, "config.json")))

    def test_phase14_6_readme_markdown(self):
        run_id = "test_p14_6"
        obj = "Create README.md explaining how to run the generated project."
        runs_db = {run_id: {"run_id": run_id, "objective": obj, "status": "pending", "state": {}}}
        asyncio.run(execute_run_task(run_id, obj, runs_db))
        self.assertEqual(runs_db[run_id]["status"], "completed")
        self.assertTrue(os.path.exists(os.path.join(self.root, "README.md")))

    def test_phase14_7_js_script_and_run(self):
        run_id = "test_p14_7"
        obj = "Create a JavaScript file named hello.js that prints Hello Fraiday and execute it using an available runtime."
        runs_db = {run_id: {"run_id": run_id, "objective": obj, "status": "pending", "state": {}}}
        asyncio.run(execute_run_task(run_id, obj, runs_db))
        self.assertEqual(runs_db[run_id]["status"], "completed")
        self.assertTrue(os.path.exists(os.path.join(self.root, "hello.js")))

    def test_phase14_8_corrupted_model_response(self):
        raw_corrupt = "Let me start by inspecting...\n<tool_call>\n...\n</tool_call>\n<!DOCTYPE html><html><body><h1>Clean</h1></body></html>"
        valid, clean, err = extract_and_validate_artifact("test.html", raw_corrupt)
        self.assertTrue(valid)
        self.assertNotIn("<tool_call>", clean)
        self.assertIn("Clean", clean)

    def test_phase14_9_runtime_nameerror(self):
        target_name = "test_nameerror.py"
        target_p = os.path.join(self.root, target_name)
        with open(target_p, "w", encoding="utf-8") as f:
            f.write("insight NameError\nprint('fixed')\n")
        run_id = "test_p14_9"
        obj = f"Create a script named {target_name} that prints fixed."
        runs_db = {run_id: {"run_id": run_id, "objective": obj, "status": "pending", "state": {}}}
        asyncio.run(execute_run_task(run_id, obj, runs_db))
        self.assertEqual(runs_db[run_id]["status"], "completed")

    def test_phase14_10_incomplete_plan_repair(self):
        from app.graph.nodes.orchestrator import validate_and_repair_plan
        bad_plan = [{"id": "step_1", "action": "LIST_DIRECTORY", "target": "."}]
        repaired = validate_and_repair_plan(bad_plan, "Create a basic HTML file.", [])
        work_actions = {"CREATE_FILE", "UPDATE_FILE", "RUN_COMMAND", "DELETE_FILE"}
        self.assertTrue(any(s.get("action", "").upper() in work_actions for s in repaired))

    def test_phase14_11_pure_inspection_task(self):
        run_id = "test_p14_11"
        obj = "List the files in the workspace."
        runs_db = {run_id: {"run_id": run_id, "objective": obj, "status": "pending", "state": {}}}
        asyncio.run(execute_run_task(run_id, obj, runs_db))
        self.assertEqual(runs_db[run_id]["status"], "completed")

    def test_phase14_12_destructive_request(self):
        del_path = os.path.join(self.root, "temporary_test.txt")
        with open(del_path, "w", encoding="utf-8") as f:
            f.write("delete target\n")
        run_id = "test_p14_12"
        obj = "Delete temporary_test.txt."
        runs_db = {run_id: {"run_id": run_id, "objective": obj, "status": "pending", "state": {}}}
        asyncio.run(execute_run_task(run_id, obj, runs_db))
        self.assertEqual(runs_db[run_id]["state"].get("approval_required"), True)

    def test_context_not_stolen_on_new_creation(self):
        from app.graph.nodes.orchestrator import determine_target_filename
        fake_context = [
            {"objective": "Create autonomy_recovery_test.py", "artifacts": [{"path": "autonomy_recovery_test.py"}]}
        ]
        target = determine_target_filename("create a python file to print hello world", fake_context)
        self.assertNotEqual(target, "autonomy_recovery_test.py")
        self.assertIn("hello", target)

if __name__ == "__main__":
    unittest.main()

