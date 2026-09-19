import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestKnowledgeQuality(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        os.environ["FRAIDAY_KB_PATH"] = self.tmp.name
        from app.knowledge.store import _connect
        _connect().close()

    def tearDown(self):
        os.environ.pop("FRAIDAY_KB_PATH", None)
        try:
            os.unlink(self.tmp.name)
        except FileNotFoundError:
            pass

    def test_unrelated_python_homepage_is_not_a_strong_match(self):
        from app.knowledge.store import add_knowledge, search_knowledge

        add_knowledge(
            "Python documentation",
            "The Python homepage contains links to documentation and downloads.",
            title="Python documentation",
            url="https://www.python.org/",
            source_type="official",
            confidence=0.98,
            relevance=1.0,
        )

        matches = search_knowledge("What is Python's current stable version?")

        self.assertEqual(matches, [])

    def test_focused_record_is_reusable(self):
        from app.knowledge.store import add_knowledge, search_knowledge

        add_knowledge(
            "current stable Python version",
            "Python 3.x.y is the current stable release.",
            title="Python Releases for Windows",
            url="https://www.python.org/downloads/",
            source_type="official",
            confidence=0.98,
            relevance=0.98,
        )

        matches = search_knowledge("What is Python's current stable version?")

        self.assertEqual(len(matches), 1)
        self.assertGreaterEqual(matches[0]["score"], 0.5)


if __name__ == "__main__":
    unittest.main()
