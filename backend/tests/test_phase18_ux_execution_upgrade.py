import os
import unittest
import asyncio
from app.workspace.manager import get_workspace_manager
from app.graph.nodes.validator import validator_node
from app.graph.nodes.executor import executor_node
from app.workspace.web_server import get_web_server_manager
from app.workspace.tools import tool_run_command
from app.workspace.runtime import detect_java, detect_cli_tool

class TestPhase18UXExecutionUpgrade(unittest.TestCase):
    def setUp(self):
        self.ws = get_workspace_manager()
        self.test_files = [
            "test_ecommerce.html", "test_ecommerce.css", "test_ecommerce.js",
            "test_incomplete.html", "test_hello.py", "test_hello.js",
            "test_missing_link.html", "test_missing.css"
        ]
        # Clean up test artifacts if existing
        for f in self.test_files:
            p = self.ws.resolve_path(f)
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

    def tearDown(self):
        for f in self.test_files:
            p = self.ws.resolve_path(f)
            if os.path.exists(p):
                try:
                    os.remove(p)
                except Exception:
                    pass

    def test_A_complete_website_generation_and_validation(self):
        """TEST A — COMPLETE WEBSITE: HTML, CSS, JS created, linked, and validated."""
        state = {
            "run_id": "test_run_a",
            "objective": "Create a responsive ecommerce website with HTML, CSS and JavaScript, including product cards, search, filtering and cart functionality.",
            "plan": [
                {"id": "step_1", "description": "Create HTML", "agent": "executor", "action": "CREATE_FILE", "target": "test_ecommerce.html", "arguments": {"path": "test_ecommerce.html"}, "status": "pending"},
                {"id": "step_2", "description": "Create CSS", "agent": "executor", "action": "CREATE_FILE", "target": "test_ecommerce.css", "arguments": {"path": "test_ecommerce.css"}, "status": "pending"},
                {"id": "step_3", "description": "Create JS", "agent": "executor", "action": "CREATE_FILE", "target": "test_ecommerce.js", "arguments": {"path": "test_ecommerce.js"}, "status": "pending"}
            ],
            "observations": [],
            "artifacts": []
        }

        # Execute step 1 (HTML)
        state_1 = asyncio.run(executor_node(state))
        # Execute step 2 (CSS)
        state_2 = asyncio.run(executor_node(state_1))
        # Execute step 3 (JS)
        state_3 = asyncio.run(executor_node(state_2))

        # Check files exist on disk
        self.assertTrue(os.path.exists(self.ws.resolve_path("test_ecommerce.html")))
        self.assertTrue(os.path.exists(self.ws.resolve_path("test_ecommerce.css")))
        self.assertTrue(os.path.exists(self.ws.resolve_path("test_ecommerce.js")))

        # Validate complete website
        val_state = asyncio.run(validator_node(state_3))
        val_result = val_state.get("validation_results", [])[-1]

        self.assertTrue(val_result.get("valid"), f"Validation failed: {val_result.get('reason')}")
        self.assertIn(val_result.get("status"), ["COMPLETE", "PASS", None])

    def test_B_incomplete_website_gate(self):
        """TEST B — BAD/INCOMPLETE WEBSITE: Minimal HTML fails validation & triggers recovery."""
        incomplete_path = self.ws.resolve_path("test_incomplete.html")
        with open(incomplete_path, "w", encoding="utf-8") as f:
            f.write("<!DOCTYPE html><html><head><title>Bad</title></head><body><h1>Hello</h1></body></html>")

        state = {
            "run_id": "test_run_b",
            "objective": "Create a complete responsive ecommerce website with product cards, search, filter and cart.",
            "plan": [],
            "observations": [],
            "artifacts": [{"path": "test_incomplete.html", "operation": "created"}]
        }

        val_state = asyncio.run(validator_node(state))
        val_result = val_state.get("validation_results", [])[-1]

        self.assertFalse(val_result.get("valid"))
        self.assertEqual(val_result.get("status"), "INCOMPLETE")
        self.assertEqual(val_state.get("current_step"), "recovery")

    def test_C_python_execution(self):
        """TEST C — PYTHON EXECUTION: Run hello.py and capture stdout & exit_code 0."""
        py_path = self.ws.resolve_path("test_hello.py")
        with open(py_path, "w", encoding="utf-8") as f:
            f.write("print('Hello from Fraiday')\n")

        py_exec = self.ws.get_python_executable()
        res = tool_run_command(f"{py_exec} test_hello.py")

        self.assertTrue(res.get("success"))
        self.assertEqual(res.get("exit_code"), 0)
        self.assertIn("Hello from Fraiday", res.get("stdout", ""))

    def test_D_javascript_execution(self):
        """TEST D — JAVASCRIPT EXECUTION: Standalone JS via Node.js."""
        js_path = self.ws.resolve_path("test_hello.js")
        with open(js_path, "w", encoding="utf-8") as f:
            f.write("console.log('Hello from Node');\n")

        node_info = detect_cli_tool("node")
        if node_info["available"]:
            res = tool_run_command("node test_hello.js")
            self.assertTrue(res.get("success"))
            self.assertEqual(res.get("exit_code"), 0)
            self.assertIn("Hello from Node", res.get("stdout", ""))
        else:
            self.assertFalse(node_info["available"])

    def test_E_java_execution(self):
        """TEST E — JAVA EXECUTION: Check JDK availability or report runtime unavailable."""
        java_info = detect_java()
        if java_info["available"] and java_info["compiler"]:
            java_path = self.ws.resolve_path("TestHello.java")
            with open(java_path, "w", encoding="utf-8") as f:
                f.write("public class TestHello { public static void main(String[] args) { System.out.println(\"Hello from Java\"); } }\n")
            
            res_compile = tool_run_command("javac TestHello.java")
            self.assertEqual(res_compile.get("exit_code"), 0)
            res_run = tool_run_command("java TestHello")
            self.assertEqual(res_run.get("exit_code"), 0)
            self.assertIn("Hello from Java", res_run.get("stdout", ""))

            # Cleanup
            for f in ["TestHello.java", "TestHello.class"]:
                p = self.ws.resolve_path(f)
                if os.path.exists(p): os.remove(p)
        else:
            # If Java is unavailable, runtime inspection reports false
            self.assertFalse(java_info["available"])

    def test_F_html_preview(self):
        """TEST F — HTML PREVIEW: Start static server and verify preview URL."""
        server_mgr = get_web_server_manager()
        start_res = server_mgr.start(self.ws.root_path, preferred_port=5520)

        self.assertTrue(start_res.get("success"))
        self.assertEqual(start_res.get("status"), "running")
        self.assertIn("http://localhost:", start_res.get("url", ""))

        status_res = server_mgr.get_status()
        self.assertEqual(status_res.get("status"), "running")

        stop_res = server_mgr.stop()
        self.assertTrue(stop_res.get("success"))
        self.assertEqual(stop_res.get("status"), "stopped")

    def test_G_cross_file_link_validation(self):
        """TEST G — CROSS-FILE LINK VALIDATION: Fail when stylesheet missing, pass when present."""
        html_path = self.ws.resolve_path("test_missing_link.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write("<!DOCTYPE html><html><head><link rel=\"stylesheet\" href=\"test_missing.css\"></head><body><h1>Link Test</h1></body></html>")

        # 1. Missing stylesheet should fail
        state_missing = {
            "run_id": "test_run_g1",
            "objective": "Build website page with stylesheet.",
            "plan": [],
            "observations": [],
            "artifacts": [{"path": "test_missing_link.html", "operation": "created"}]
        }
        val_1 = asyncio.run(validator_node(state_missing))
        res_1 = val_1.get("validation_results", [])[-1]
        self.assertFalse(res_1.get("valid"))
        self.assertEqual(res_1.get("status"), "INCOMPLETE")

        # 2. Add stylesheet -> should pass
        css_path = self.ws.resolve_path("test_missing.css")
        with open(css_path, "w", encoding="utf-8") as f:
            f.write("body { background: #000; color: #fff; font-family: sans-serif; }\nh1 { color: red; }\n")

        state_present = {
            "run_id": "test_run_g2",
            "objective": "Build website page with stylesheet.",
            "plan": [],
            "observations": [],
            "artifacts": [{"path": "test_missing_link.html", "operation": "created"}]
        }
        val_2 = asyncio.run(validator_node(state_present))
        res_2 = val_2.get("validation_results", [])[-1]
        self.assertTrue(res_2.get("valid"))

if __name__ == "__main__":
    unittest.main()
