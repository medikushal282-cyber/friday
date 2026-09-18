import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.workspace.manager import WorkspaceManager, PathSecurityError
from app.workspace.policy import check_command_policy, POLICY_SAFE, POLICY_APPROVAL_REQUIRED, POLICY_DENIED

class TestWorkspaceSecurity(unittest.TestCase):
    def setUp(self):
        self.ws = WorkspaceManager()
        self.root = self.ws.root_path

    def test_normal_relative_path(self):
        resolved = self.ws.resolve_path("test.txt")
        self.assertEqual(resolved, os.path.join(self.root, "test.txt"))

    def test_nested_path(self):
        resolved = self.ws.resolve_path("sub/nested/file.py")
        self.assertEqual(resolved, os.path.join(self.root, "sub", "nested", "file.py"))

    def test_dot_dot_traversal(self):
        with self.assertRaises(PathSecurityError):
            self.ws.resolve_path("../outside.txt")
        with self.assertRaises(PathSecurityError):
            self.ws.resolve_path("sub/../../outside.txt")
        with self.assertRaises(PathSecurityError):
            self.ws.resolve_path("a/b/c/../../../../escape.txt")

    def test_absolute_outside_path(self):
        with self.assertRaises(PathSecurityError):
            self.ws.resolve_path("C:\\Windows\\System32\\calc.exe")
        with self.assertRaises(PathSecurityError):
            self.ws.resolve_path("C:\\Program Files\\outside.txt")

    def test_windows_path_traversal(self):
        with self.assertRaises(PathSecurityError):
            self.ws.resolve_path("D:\\outside\\file.txt")
        with self.assertRaises(PathSecurityError):
            self.ws.resolve_path("..\\..\\windows\\system32")

    def test_file_operations_containment(self):
        # Write file inside workspace
        write_res = self.ws.write_file("tmp_test_file.txt", "hello fraiday")
        self.assertTrue(write_res["success"])
        
        # Read file
        read_res = self.ws.read_file("tmp_test_file.txt")
        self.assertTrue(read_res["success"])
        self.assertEqual(read_res["content"], "hello fraiday")
        
        # Delete file
        del_res = self.ws.delete_file("tmp_test_file.txt")
        self.assertTrue(del_res["success"])

        # Attempt to write outside
        with self.assertRaises(PathSecurityError):
            self.ws.write_file("../forbidden.txt", "evil")

    def test_command_policy(self):
        self.assertEqual(check_command_policy("python test.py")[0], POLICY_SAFE)
        self.assertEqual(check_command_policy("py test.py")[0], POLICY_SAFE)
        self.assertEqual(check_command_policy("git status")[0], POLICY_SAFE)
        self.assertEqual(check_command_policy("pip install requests")[0], POLICY_APPROVAL_REQUIRED)
        self.assertEqual(check_command_policy("del /f /s *")[0], POLICY_APPROVAL_REQUIRED)
        self.assertEqual(check_command_policy("format C:")[0], POLICY_DENIED)
        self.assertEqual(check_command_policy("shutdown /s")[0], POLICY_DENIED)

if __name__ == "__main__":
    unittest.main()
