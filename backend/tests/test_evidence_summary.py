"""Regression tests for the deterministic evidence summary."""

from dataclasses import replace
from pathlib import Path
import sys
import unittest


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from models.evidence_summary import EvidenceAssessment
from models.generated_test_report import (
    GeneratedTestCase,
    TestCaseCategory,
    TestDesignStrategy,
)
from services.evidence_summary import build_evidence_summary
from generated_report_factory import make_generated_test_report


def execution(
    return_code: int | None,
    *,
    timed_out: bool = False,
    skipped: bool = False,
) -> dict[str, object]:
    return {
        "return_code": return_code,
        "output": "",
        "timed_out": timed_out,
        "skipped": skipped,
    }


def coverage(untested: int) -> dict[str, object]:
    total = 4
    covered = total - untested
    return {
        "target_path": "src/sample.py",
        "available": True,
        "existing": {"covered_branches": 1, "total_branches": total, "percent": 25.0},
        "combined": {
            "covered_branches": covered,
            "total_branches": total,
            "percent": covered / total * 100,
        },
        "incremental_covered_branches": covered - 1,
        "untested_branches": untested,
        "unavailable_reason": None,
    }


class EvidenceSummaryTests(unittest.TestCase):
    """Ensure the summary stays factual, bounded, and non-authoritative."""

    def test_separates_failures_assumptions_and_untested_behavior(self) -> None:
        report = replace(
            make_generated_test_report(),
            assumptions=("Empty inputs are treated as invalid.",),
        )
        results = {
            "installation": execution(0),
            "existing_execution": execution(0),
            "generated_execution": execution(1),
            "branch_coverage": coverage(2),
        }

        summary = build_evidence_summary(report, results)

        self.assertEqual(summary.assessment, EvidenceAssessment.OBSERVED_FAILURES)
        self.assertIn("Existing repository suite passed.", summary.passed)
        self.assertIn("Generated focused suite failed with exit code 1.", summary.failed)
        self.assertEqual(summary.assumed, ("Empty inputs are treated as invalid.",))
        self.assertIn("2 of 4 selected-source branches remain untested.", summary.untested)
        self.assertIn("Generated suite contains no boundary case.", summary.untested)
        self.assertIn("Generated suite contains no gray-box case.", summary.untested)

    def test_complete_observed_evidence_never_becomes_a_correctness_claim(self) -> None:
        cases = tuple(
            GeneratedTestCase(
                test_name=f"test_{category.value}",
                category=category,
                strategy=(
                    TestDesignStrategy.BLACK_BOX
                    if index % 2 == 0
                    else TestDesignStrategy.GRAY_BOX
                ),
                expected_behavior="Documented behavior is observed.",
            )
            for index, category in enumerate(TestCaseCategory)
        )
        report = replace(make_generated_test_report(), cases=cases)
        results = {
            "installation": execution(0, skipped=True),
            "existing_execution": execution(0),
            "generated_execution": execution(0),
            "branch_coverage": coverage(0),
        }

        summary = build_evidence_summary(report, results)

        self.assertEqual(summary.assessment, EvidenceAssessment.NO_OBSERVED_FAILURES)
        self.assertFalse(summary.failed)
        self.assertFalse(summary.untested)
        self.assertIn("All 4 selected-source branches were executed.", summary.passed)

    def test_no_existing_tests_and_unavailable_coverage_are_untested(self) -> None:
        report = make_generated_test_report()
        results = {
            "installation": execution(0),
            "existing_execution": execution(5),
            "generated_execution": execution(0),
            "branch_coverage": {
                "available": False,
                "unavailable_reason": "Coverage was unavailable for this runner.",
            },
        }

        summary = build_evidence_summary(report, results)

        self.assertEqual(summary.assessment, EvidenceAssessment.INCOMPLETE)
        self.assertIn("Existing repository suite collected no tests.", summary.untested)
        self.assertIn("Coverage was unavailable for this runner.", summary.untested)

