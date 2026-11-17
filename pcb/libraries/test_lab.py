"""Tests for lab.py (the path of the lab directory). Run: make pcb-test (stdlib unittest, KiCad image python3)."""
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lab  # noqa: E402


class TestLab(unittest.TestCase):
    def test_pointer_is_read_from_claude_md(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, ".claude"))
            with open(os.path.join(root, ".claude", "CLAUDE.md"), "w") as fh:
                fh.write("project: x\nlab: docs/somelab/  # lab config\nnext: y\n")
            self.assertEqual(lab.read_pointer(root), os.path.join(root, "docs", "somelab"))

    def test_missing_pointer_fails(self):
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, ".claude"))
            with open(os.path.join(root, ".claude", "CLAUDE.md"), "w") as fh:
                fh.write("project: x\n")
            with self.assertRaises(RuntimeError):
                lab.read_pointer(root)

    def test_env_overrides_pointer(self):
        with mock.patch.dict(os.environ, {"LAB_DIR": "/some/other/lab"}):
            self.assertEqual(lab.lab_dir(), "/some/other/lab")

    def test_repo_pointer_names_an_existing_lab_file(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("LAB_DIR", None)
            self.assertTrue(os.path.isfile(lab.limits_file()), lab.limits_file())
            self.assertEqual(os.path.basename(lab.limits_file()), "milling.toml")


if __name__ == "__main__":
    unittest.main()
