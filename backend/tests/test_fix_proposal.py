"""Tests for the approval-gated repository fix proposal contract."""

from dataclasses import FrozenInstanceError
from pathlib import Path
import sys
import unittest


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from models.fix_proposal import (
    MAX_FIX_PATCH_BYTES,
    MAX_FIX_SUMMARY_CHARACTERS,
    RepositoryFixProposal,
)


class RepositoryFixProposalTests(unittest.TestCase):
    """Keep every proposal review-only until a later approved workflow exists."""

    def test_proposal_always_requires_approval_and_is_not_applied(self) -> None:
        proposal = RepositoryFixProposal(
            revision="a" * 40,
            subdirectory="packages/sample",
            target_path="packages/sample/src/sample.py",
            summary="Handle an empty input.",
            patch="--- a/src/sample.py\n+++ b/src/sample.py\n",
        )

        self.assertTrue(proposal.approval_required)
        self.assertFalse(proposal.applied)

        with self.assertRaises(FrozenInstanceError):
            proposal.applied = True  # type: ignore[misc]

    def test_callers_cannot_override_the_approval_state(self) -> None:
        with self.assertRaises(TypeError):
            RepositoryFixProposal(
                revision="a" * 40,
                subdirectory=None,
                target_path="src/sample.py",
                summary="Handle an empty input.",
                patch="--- a/src/sample.py\n+++ b/src/sample.py\n",
                approval_required=False,  # type: ignore[call-arg]
            )

    def test_contract_defines_bounded_text_limits(self) -> None:
        self.assertEqual(MAX_FIX_SUMMARY_CHARACTERS, 1_000)
        self.assertEqual(MAX_FIX_PATCH_BYTES, 128 * 1024)

    def test_rejects_unpinned_empty_or_oversized_proposals(self) -> None:
        valid_values = {
            "revision": "a" * 40,
            "subdirectory": None,
            "target_path": "src/sample.py",
            "summary": "Handle an empty input.",
            "patch": "--- a/src/sample.py\n+++ b/src/sample.py\n",
        }

        invalid_overrides = (
            {"revision": "main"},
            {"summary": "   "},
            {"summary": "x" * (MAX_FIX_SUMMARY_CHARACTERS + 1)},
            {"patch": ""},
            {"patch": "valid\x00hidden"},
            {"patch": "x" * (MAX_FIX_PATCH_BYTES + 1)},
        )

        for override in invalid_overrides:
            with self.subTest(override=override):
                with self.assertRaises(ValueError):
                    RepositoryFixProposal(**(valid_values | override))

    def test_rejects_unsafe_or_out_of_scope_proposal_targets(self) -> None:
        invalid_targets = (
            "README.md",
            "../sample.py",
            ".verix-venv/site.py",
            "packages/other/sample.py",
        )

        for target_path in invalid_targets:
            with self.subTest(target_path=target_path):
                with self.assertRaises(ValueError):
                    RepositoryFixProposal(
                        revision="a" * 40,
                        subdirectory="packages/sample",
                        target_path=target_path,
                        summary="Handle an empty input.",
                        patch="--- a/src/sample.py\n+++ b/src/sample.py\n",
                    )


if __name__ == "__main__":
    unittest.main()
