"""Tests for disposable approved-fix application without test execution."""

from contextlib import nullcontext
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from models.fix_proposal import RepositoryApprovedFix
from services.repository_preparer import PreparedRepository
from workflows.repository_fix_application import RepositoryFixApplicationWorkflow


SOURCE = "def add(a, b):\n    return a - b\n"
PATCH = (
    "--- a/packages/sample/src/sample.py\n"
    "+++ b/packages/sample/src/sample.py\n"
    "@@ -1,2 +1,2 @@\n"
    " def add(a, b):\n"
    "-    return a - b\n"
    "+    return a + b\n"
)


class RepositoryFixApplicationWorkflowTests(unittest.TestCase):
    """Ensure approved patches cannot affect prepared or host repository files."""

    def test_applies_an_exact_patch_only_inside_a_disposable_copy(self) -> None:
        with tempfile.TemporaryDirectory() as repository_directory:
            project_path = Path(repository_directory) / "packages" / "sample"
            source_path = project_path / "src" / "sample.py"
            source_path.parent.mkdir(parents=True)
            source_path.write_text(SOURCE, encoding="utf-8")
            preparer = Mock()
            preparer.prepare.return_value = nullcontext(
                PreparedRepository(
                    path=project_path,
                    file_count=1,
                    total_bytes=len(SOURCE.encode("utf-8")),
                    skipped_entries=0,
                )
            )
            workflow = RepositoryFixApplicationWorkflow(preparer)
            approved_fix = RepositoryApprovedFix(
                revision="a" * 40,
                subdirectory="packages/sample",
                target_path="packages/sample/src/sample.py",
                patch=PATCH,
            )

            with workflow.apply("https://github.com/example/sample", approved_fix) as result:
                disposable_source = result.path / "src" / "sample.py"
                self.assertEqual(
                    disposable_source.read_text(encoding="utf-8"),
                    "def add(a, b):\n    return a + b\n",
                )
                self.assertTrue(result.path.is_dir())
                disposable_path = result.path

            self.assertEqual(source_path.read_text(encoding="utf-8"), SOURCE)
            self.assertFalse(disposable_path.exists())
            preparer.prepare.assert_called_once_with(
                "https://github.com/example/sample",
                "a" * 40,
                "packages/sample",
            )

    def test_rejects_a_patch_that_does_not_match_the_pinned_source(self) -> None:
        with tempfile.TemporaryDirectory() as repository_directory:
            project_path = Path(repository_directory)
            source_path = project_path / "src" / "sample.py"
            source_path.parent.mkdir()
            source_path.write_text(SOURCE, encoding="utf-8")
            preparer = Mock()
            preparer.prepare.return_value = nullcontext(
                PreparedRepository(
                    path=project_path,
                    file_count=1,
                    total_bytes=len(SOURCE.encode("utf-8")),
                    skipped_entries=0,
                )
            )
            workflow = RepositoryFixApplicationWorkflow(preparer)
            approved_fix = RepositoryApprovedFix(
                revision="a" * 40,
                subdirectory=None,
                target_path="src/sample.py",
                patch=PATCH.replace("packages/sample/", "").replace(
                    "-    return a - b",
                    "-    return a * b",
                ),
            )

            with self.assertRaisesRegex(ValueError, "does not match"):
                with workflow.apply("https://github.com/example/sample", approved_fix):
                    self.fail("An invalid patch must not yield a workspace.")

            self.assertEqual(source_path.read_text(encoding="utf-8"), SOURCE)

    def test_rejects_symbolic_link_targets_in_the_disposable_copy(self) -> None:
        with tempfile.TemporaryDirectory() as repository_directory:
            project_path = Path(repository_directory)
            target = project_path / "src" / "sample.py"
            target.parent.mkdir()
            target.symlink_to("outside.py")
            preparer = Mock()
            preparer.prepare.return_value = nullcontext(
                PreparedRepository(
                    path=project_path,
                    file_count=1,
                    total_bytes=0,
                    skipped_entries=1,
                )
            )
            workflow = RepositoryFixApplicationWorkflow(preparer)
            approved_fix = RepositoryApprovedFix(
                revision="a" * 40,
                subdirectory=None,
                target_path="src/sample.py",
                patch=PATCH.replace("packages/sample/", ""),
            )

            with self.assertRaisesRegex(ValueError, "symbolic links"):
                with workflow.apply("https://github.com/example/sample", approved_fix):
                    self.fail("A symbolic-link target must not yield a workspace.")


if __name__ == "__main__":
    unittest.main()
