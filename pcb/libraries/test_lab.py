"""Tests for lab.py (the path of the lab directory). Run: make pcb-test (stdlib unittest, KiCad image python3)."""
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lab  # noqa: E402


class TestLab(unittest.TestCase):
    def _config(self, root, text):
        os.makedirs(os.path.join(root, "pcb", "config"))
        with open(os.path.join(root, "pcb", "config", "lab.toml"), "w") as fh:
            fh.write(text)

    def test_pointer_is_read_from_lab_toml(self):
        with tempfile.TemporaryDirectory() as root:
            self._config(root, 'dir = "docs/somelab"  # lab directory\n')
            self.assertEqual(lab.read_pointer(root), os.path.join(root, "docs", "somelab"))

    def test_missing_pointer_fails(self):
        with tempfile.TemporaryDirectory() as root:
            self._config(root, 'other = "x"\n')
            with self.assertRaises(RuntimeError):
                lab.read_pointer(root)

    def test_claude_md_is_not_read(self):
        """A script must not parse CLAUDE.md (skill project-context): only pcb/config/lab.toml counts."""
        with tempfile.TemporaryDirectory() as root:
            os.makedirs(os.path.join(root, ".claude"))
            with open(os.path.join(root, ".claude", "CLAUDE.md"), "w") as fh:
                fh.write("lab: docs/claudelab/\n")
            self._config(root, 'dir = "docs/tomllab"\n')
            self.assertEqual(lab.read_pointer(root), os.path.join(root, "docs", "tomllab"))

    def test_dir_must_be_a_string(self):
        with tempfile.TemporaryDirectory() as root:
            self._config(root, "dir = 5\n")
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
