"""Tests for narrow temporary-workspace cleanup."""

import os
from pathlib import Path
import sys
import tempfile
import unittest


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from services.temporary_workspaces import TemporaryWorkspaceManager


class TemporaryWorkspaceManagerTests(unittest.TestCase):
    """Remove stale Verix directories without touching unrelated temporary data."""

    def test_context_removes_created_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_root:
            manager = TemporaryWorkspaceManager(root=Path(temporary_root) / "owned")

            with manager.create("repository-run-") as workspace:
                self.assertTrue(workspace.is_dir())
                created_path = workspace

            self.assertFalse(created_path.exists())

    def test_sweep_removes_only_stale_known_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_root:
            root = Path(temporary_root) / "owned"
            manager = TemporaryWorkspaceManager(
                root=root,
                stale_after_seconds=60,
                clock=lambda: 1_000,
            )
            root.mkdir()
            stale_owned = root / "repository-run-stale"
            recent_owned = root / "pasted-code-recent"
            unrelated = root / "someone-elses-data"
            stale_owned.mkdir()
            recent_owned.mkdir()
            unrelated.mkdir()
            os.utime(stale_owned, (900, 900))
            os.utime(recent_owned, (990, 990))
            os.utime(unrelated, (900, 900))

            removed = manager.cleanup_stale()

            self.assertEqual(removed, 1)
            self.assertFalse(stale_owned.exists())
            self.assertTrue(recent_owned.exists())
            self.assertTrue(unrelated.exists())


if __name__ == "__main__":
    unittest.main()
