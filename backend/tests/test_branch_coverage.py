"""Regression tests for bounded branch-coverage evidence."""

import json
from pathlib import Path
import sys
import unittest


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from models.coverage import BranchCoverageRun
from models.execution import TestExecutionResult
from services.branch_coverage import (
    COVERAGE_SENTINEL,
    extract_branch_coverage,
    present_branch_coverage,
    summarize_branch_coverage,
)


class BranchCoverageTests(unittest.TestCase):
    """Keep coverage parsing separate from coverage arithmetic."""

    def test_extracts_trusted_metadata_without_showing_it_as_test_output(self) -> None:
        payload = {
            "target_path": "src/sample.py",
            "total_branches": 2,
            "executed_branches": [[3, 4]],
        }
        result = extract_branch_coverage(
            TestExecutionResult(
                return_code=0,
                output=f"1 passed\n{COVERAGE_SENTINEL}{json.dumps(payload)}\n",
            ),
            "src/sample.py",
        )

        self.assertEqual(result.output, "1 passed\n")
        self.assertEqual(result.branch_coverage.executed_branches, {(3, 4)})
        self.assertEqual(result.branch_coverage.total_branches, 2)

    def test_invalid_metadata_is_not_treated_as_coverage(self) -> None:
        result = extract_branch_coverage(
            TestExecutionResult(
                return_code=0,
                output=f"passed\n{COVERAGE_SENTINEL}{{\"target_path\":\"other.py\"}}\n",
            ),
            "src/sample.py",
        )

        self.assertEqual(result.output, "passed\n")
        self.assertIsNone(result.branch_coverage)

    def test_reports_existing_combined_incremental_and_untested_branches(self) -> None:
        existing = TestExecutionResult(
            return_code=0,
            output="existing passed",
            branch_coverage=BranchCoverageRun(
                target_path="src/sample.py",
                total_branches=3,
                executed_branches=frozenset({(3, 4)}),
            ),
        )
        generated = TestExecutionResult(
            return_code=0,
            output="generated passed",
            branch_coverage=BranchCoverageRun(
                target_path="src/sample.py",
                total_branches=3,
                executed_branches=frozenset({(3, 6)}),
            ),
        )

        summary = summarize_branch_coverage(
            "src/sample.py",
            existing,
            generated,
            test_runner="pytest",
        )
        payload = present_branch_coverage(summary)

        self.assertTrue(payload["available"])
        self.assertEqual(payload["existing"]["covered_branches"], 1)
        self.assertEqual(payload["existing"]["percent"], 33.3)
        self.assertEqual(payload["combined"]["covered_branches"], 2)
        self.assertEqual(payload["combined"]["percent"], 66.7)
        self.assertEqual(payload["incremental_covered_branches"], 1)
        self.assertEqual(payload["untested_branches"], 1)

    def test_tox_and_mismatched_static_branch_sets_are_explicitly_unavailable(self) -> None:
        existing = TestExecutionResult(
            return_code=0,
            output="passed",
            branch_coverage=BranchCoverageRun(
                "src/sample.py", 1, frozenset({(1, 2)})
            ),
        )
        generated = TestExecutionResult(
            return_code=0,
            output="passed",
            branch_coverage=BranchCoverageRun(
                "src/sample.py", 2, frozenset({(1, 3)})
            ),
        )

        tox = summarize_branch_coverage(
            "src/sample.py", existing, generated, test_runner="tox"
        )
        mismatch = summarize_branch_coverage(
            "src/sample.py", existing, generated, test_runner="pytest"
        )

        self.assertFalse(tox.available)
        self.assertIn("tox", tox.unavailable_reason)
        self.assertFalse(mismatch.available)
        self.assertIn("same selected source", mismatch.unavailable_reason)
