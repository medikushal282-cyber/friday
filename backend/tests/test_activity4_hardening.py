import os
import sys
import unittest
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.workspace.manager import WorkspaceManager
from app.workspace.knowledge import get_knowledge_store
from app.workspace.tools import execute_action, validate_python_source, classify_failure
from app.workspace.artifact_cleaner import extract_and_validate_artifact
from app.graph.workflow import execute_run_task
from app.graph.nodes.executor import clean_python_code
from app.graph.nodes.orchestrator import build_dynamic_fallback_plan

class TestActivity4Hardening(unittest.TestCase):
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
            "hello_validation.py", "malformed.py", "fenced.py", "syntax_err.py",
            "missing_arg.py", "missing_fn.py", "sample_csv.csv", "employee_report.py",
            "department_report.json", "word_stats.py", "word_stats.json", "README.md",
            "friday_test.html", "styles.css", "valid_test.html", "app.css", "config.json",
            "fraiday_runtime_test.html", "sample.json", "data.csv", "script.js", "notes.md"
        ]:
            abs_path = os.path.join(self.root, fname)
            if os.path.exists(abs_path):
                try:
                    os.remove(abs_path)
                except Exception:
                    pass

    # A. VALID PYTHON
    def test_a_valid_python(self):
        content = 'print("Hello Fraiday")\n'
        valid, extracted, err = extract_and_validate_artifact("hello.py", content)
        self.assertTrue(valid)
        self.assertEqual(extracted, 'print("Hello Fraiday")\n')

    # B. FENCED PYTHON
    def test_b_fenced_python(self):
        content = '```python\nprint("Hello Fraiday")\n```'
        valid, extracted, err = extract_and_validate_artifact("fenced.py", content)
        self.assertTrue(valid)
        self.assertEqual(extracted, 'print("Hello Fraiday")')

    # C. PYTHON CONVERSATIONAL PREAMBLE
    def test_c_python_conversational_preamble(self):
        content = 'I will create the python script now.\nprint("Hello Fraiday")'
        valid, extracted, err = extract_and_validate_artifact("preamble.py", content)
        self.assertTrue(valid)
        self.assertEqual(extracted, 'print("Hello Fraiday")')

    # D. MALFORMED PYTHON
    def test_d_malformed_python(self):
        content = 'def invalid_func(:\n    print("bad")'
        valid, extracted, err = extract_and_validate_artifact("bad.py", content)
        self.assertFalse(valid)
        self.assertIn("Python syntax error", err)

    # E. VALID HTML
    def test_e_valid_html(self):
        content = '<!DOCTYPE html>\n<html><head><title>Test</title></head><body><h1>Hello</h1></body></html>'
        valid, extracted, err = extract_and_validate_artifact("index.html", content)
        self.assertTrue(valid)
        self.assertTrue(extracted.startswith("<!DOCTYPE html>"))

    # F. FENCED HTML
    def test_f_fenced_html(self):
        content = '```html\n<h1>Hello Fraiday</h1>\n```'
        valid, extracted, err = extract_and_validate_artifact("page.html", content)
        self.assertTrue(valid)
        self.assertEqual(extracted, '<h1>Hello Fraiday</h1>')

    # G. MALFORMED HTML
    def test_g_malformed_html(self):
        content = 'Let me start by inspecting the workspace for existing files.'
        valid, extracted, err = extract_and_validate_artifact("test.html", content)
        self.assertFalse(valid)
        self.assertIn("not valid HTML", err)

    # H. VALID CSS
    def test_h_valid_css(self):
        content = 'body {\n    margin: 0;\n    padding: 0;\n}'
        valid, extracted, err = extract_and_validate_artifact("style.css", content)
        self.assertTrue(valid)
        self.assertIn("margin: 0;", extracted)

    # I. FENCED CSS
    def test_i_fenced_css(self):
        content = '```css\nbody { color: red; }\n```'
        valid, extracted, err = extract_and_validate_artifact("app.css", content)
        self.assertTrue(valid)
        self.assertEqual(extracted, 'body { color: red; }')

    # J. CSS WITH CONVERSATIONAL PREAMBLE
    def test_j_css_conversational_preamble(self):
        content = 'I will create the stylesheet:\nbody { color: blue; }'
        valid, extracted, err = extract_and_validate_artifact("styles.css", content)
        self.assertTrue(valid)
        self.assertEqual(extracted, 'body { color: blue; }')

    # K. CSS WITH COMMENTS
    def test_k_css_with_comments(self):
        content = '/* Main Application Styles */\nbody {\n    font-size: 16px;\n}'
        valid, extracted, err = extract_and_validate_artifact("main.css", content)
        self.assertTrue(valid)
        self.assertIn("/* Main Application Styles */", extracted)

    # L. CSS WITH CUSTOM PROPERTIES
    def test_l_css_with_custom_properties(self):
        content = ':root {\n    --main-bg: #ffffff;\n}\nbody {\n    background-color: var(--main-bg);\n}'
        valid, extracted, err = extract_and_validate_artifact("theme.css", content)
        self.assertTrue(valid)
        self.assertIn("--main-bg", extracted)

    # M. CSS @MEDIA
    def test_m_css_media(self):
        content = '@media (max-width: 600px) {\n    body {\n        font-size: 12px;\n    }\n}'
        valid, extracted, err = extract_and_validate_artifact("responsive.css", content)
        self.assertTrue(valid)
        self.assertIn("@media", extracted)

    # N. CSS @KEYFRAMES
    def test_n_css_keyframes(self):
        content = '@keyframes spin {\n    from { transform: rotate(0deg); }\n    to { transform: rotate(360deg); }\n}'
        valid, extracted, err = extract_and_validate_artifact("anim.css", content)
        self.assertTrue(valid)
        self.assertIn("@keyframes spin", extracted)

    # O. HTML REJECTED AS CSS
    def test_o_html_rejected_as_css(self):
        content = '<!DOCTYPE html>\n<html><body>Hello</body></html>'
        valid, extracted, err = extract_and_validate_artifact("styles.css", content)
        self.assertFalse(valid)
        self.assertIn("embedded HTML", err)

    # P. MIXED HTML + CSS CORRUPTION REJECTED
    def test_p_mixed_html_css_corruption_rejected(self):
        content = """I cannot create the stylesheet.

<html>
<body>Hello</body>
</html>

body {
    margin: 0;
}"""
        valid, extracted, err = extract_and_validate_artifact("styles.css", content)
        self.assertFalse(valid)
        self.assertIn("embedded HTML", err)

    # Q. VALID JSON
    def test_q_valid_json(self):
        content = '{\n  "status": "ok",\n  "count": 1\n}'
        valid, extracted, err = extract_and_validate_artifact("sample.json", content)
        self.assertTrue(valid)
        self.assertIn('"status": "ok"', extracted)

    # R. INVALID JSON
    def test_r_invalid_json(self):
        content = '{\n  status: "ok"\n}'
        valid, extracted, err = extract_and_validate_artifact("bad.json", content)
        self.assertFalse(valid)
        self.assertIn("invalid JSON", err)

    # S. VALID CSV
    def test_s_valid_csv(self):
        content = 'name,age,city\nAlice,30,New York\nBob,25,San Francisco\n'
        valid, extracted, err = extract_and_validate_artifact("data.csv", content)
        self.assertTrue(valid)
        self.assertIn("Alice,30,New York", extracted)

    # T. CORRUPTED CSV
    def test_t_corrupted_csv(self):
        content = 'Here is the data file with no tabular commas anywhere in this sentence.'
        valid, extracted, err = extract_and_validate_artifact("data.csv", content)
        self.assertFalse(valid)
        self.assertIn("does not match CSV", err)

    # U. VALID JS
    def test_u_valid_js(self):
        content = 'console.log("Hello from JavaScript");\n'
        valid, extracted, err = extract_and_validate_artifact("script.js", content)
        self.assertTrue(valid)
        self.assertIn('console.log', extracted)

    # V. VALID MARKDOWN
    def test_v_valid_markdown(self):
        content = '# Fraiday Documentation\n\nThis is legitimate prose documentation.\n'
        valid, extracted, err = extract_and_validate_artifact("notes.md", content)
        self.assertTrue(valid)
        self.assertIn("# Fraiday Documentation", extracted)

    # W. UPDATE_FILE PRESERVES OLD FILE WHEN NEW ARTIFACT IS INVALID
    def test_w_update_file_preserves_old_file_when_invalid(self):
        target = "app.css"
        valid_initial = "body {\n    margin: 0;\n    background: #ffffff;\n}\n"

        # 1. Create valid initial CSS file
        create_res = execute_action({
            "tool": "create_file",
            "arguments": {"path": target, "content": valid_initial}
        })
        self.assertTrue(create_res["success"])

        # 2. Attempt update_file with corrupted HTML content
        corrupted_update = "<html><body>Corrupted HTML inside CSS update</body></html>"
        update_res = execute_action({
            "tool": "update_file",
            "arguments": {"path": target, "content": corrupted_update}
        })
        self.assertFalse(update_res["success"])
        self.assertEqual(update_res["error"]["code"], "ARTIFACT_EXTRACTION_ERROR")

        # 3. Read back file from disk and verify initial valid content is unchanged
        read_res = execute_action({
            "tool": "read_file",
            "arguments": {"path": target}
        })
        self.assertTrue(read_res["success"])
        self.assertEqual(read_res["content"], valid_initial)

if __name__ == "__main__":
    unittest.main()
