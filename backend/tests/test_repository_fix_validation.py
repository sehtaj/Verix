"""Tests for safe in-memory repository fix patch validation."""

from pathlib import Path
import sys
import unittest


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from models.fix_proposal import RepositoryFixProposal
from services.repository_fix_validation import validate_repository_fix_proposal


SOURCE = "def add(a, b):\n    return a - b\n"


class RepositoryFixValidationTests(unittest.TestCase):
    """Require one applicable diff that leaves valid Python."""

    def test_accepts_one_exact_source_patch_without_writing_a_file(self) -> None:
        proposal = self.make_proposal(
            "--- a/src/sample.py\n"
            "+++ b/src/sample.py\n"
            "@@ -1,2 +1,2 @@\n"
            " def add(a, b):\n"
            "-    return a - b\n"
            "+    return a + b\n"
        )

        patched_content = validate_repository_fix_proposal(proposal, SOURCE)

        self.assertEqual(patched_content, "def add(a, b):\n    return a + b\n")
        self.assertTrue(proposal.approval_required)
        self.assertFalse(proposal.applied)

    def test_rejects_other_files_new_files_and_multiple_file_diffs(self) -> None:
        invalid_patches = (
            "--- a/tests/test_sample.py\n+++ b/tests/test_sample.py\n@@ -1 +1 @@\n-old\n+new\n",
            "--- /dev/null\n+++ b/src/sample.py\n@@ -0,0 +1 @@\n+VALUE = 1\n",
            (
                "--- a/src/sample.py\n+++ b/src/sample.py\n"
                "@@ -1,2 +1,2 @@\n def add(a, b):\n-    return a - b\n+    return a + b\n"
                "--- a/setup.py\n+++ b/setup.py\n@@ -1 +1 @@\n-old\n+new\n"
            ),
        )

        for patch in invalid_patches:
            with self.subTest(patch=patch):
                with self.assertRaises(ValueError):
                    validate_repository_fix_proposal(
                        self.make_proposal(patch),
                        SOURCE,
                    )

    def test_rejects_mismatched_counts_source_and_empty_changes(self) -> None:
        invalid_patches = (
            "--- a/src/sample.py\n+++ b/src/sample.py\n@@ -1,3 +1,2 @@\n def add(a, b):\n-    return a - b\n+    return a + b\n",
            "--- a/src/sample.py\n+++ b/src/sample.py\n@@ -1,2 +2,2 @@\n def add(a, b):\n-    return a - b\n+    return a + b\n",
            "--- a/src/sample.py\n+++ b/src/sample.py\n@@ -1,2 +1,2 @@\n def other():\n-    return a - b\n+    return a + b\n",
            "--- a/src/sample.py\n+++ b/src/sample.py\n@@ -1,2 +1,2 @@\n def add(a, b):\n     return a - b\n",
            "--- a/src/sample.py\n+++ b/src/sample.py\n@@ -2 +2 @@\n-    return a - b\n+    return a - b\n",
        )

        for patch in invalid_patches:
            with self.subTest(patch=patch):
                with self.assertRaises(ValueError):
                    validate_repository_fix_proposal(
                        self.make_proposal(patch),
                        SOURCE,
                    )

    def test_rejects_patch_that_produces_invalid_python(self) -> None:
        proposal = self.make_proposal(
            "--- a/src/sample.py\n"
            "+++ b/src/sample.py\n"
            "@@ -1,2 +1,2 @@\n"
            "-def add(a, b):\n"
            "+def add(a, b)\n"
            "     return a - b\n"
        )

        with self.assertRaisesRegex(ValueError, "invalid Python"):
            validate_repository_fix_proposal(proposal, SOURCE)

    @staticmethod
    def make_proposal(patch: str) -> RepositoryFixProposal:
        return RepositoryFixProposal(
            revision="a" * 40,
            subdirectory=None,
            target_path="src/sample.py",
            summary="Correct the selected function.",
            patch=patch,
        )


if __name__ == "__main__":
    unittest.main()
