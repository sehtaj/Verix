"""Regression tests for the deterministic verification-journey catalog."""

from pathlib import Path
import sys
import unittest


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from scripts.validate_verification_journey import (
    REPOSITORY_DIRECTORY,
    SCENARIOS,
    build_report,
    load_catalog,
)
from services.repository_fix_validation import apply_repository_fix_patch


class VerificationJourneyValidationTests(unittest.TestCase):
    """Keep validation artifacts aligned with every pinned example contract."""

    def test_scenarios_cover_the_complete_catalog(self) -> None:
        catalog = load_catalog()

        self.assertEqual(
            {scenario.example_id for scenario in SCENARIOS},
            {example["id"] for example in catalog["examples"]},
        )

    def test_reports_cover_required_categories_and_strategies(self) -> None:
        catalog = load_catalog()
        examples = {example["id"]: example for example in catalog["examples"]}

        for scenario in SCENARIOS:
            with self.subTest(example=scenario.example_id):
                report = build_report(examples[scenario.example_id], scenario)

                self.assertEqual(len(report.cases), 4)
                self.assertEqual(
                    {case.category.value for case in report.cases},
                    {"normal", "boundary", "invalid_input", "error_handling"},
                )
                self.assertEqual(
                    {case.strategy.value for case in report.cases},
                    {"black_box", "gray_box"},
                )
                self.assertEqual(report.assumptions, ())
                self.assertTrue(report.sources[0].excerpt)

    def test_every_reviewed_patch_matches_and_changes_only_its_target(self) -> None:
        catalog = load_catalog()
        examples = {example["id"]: example for example in catalog["examples"]}

        for scenario in SCENARIOS:
            with self.subTest(example=scenario.example_id):
                example = examples[scenario.example_id]
                source_path = REPOSITORY_DIRECTORY / example["target_path"]
                source = source_path.read_text(encoding="utf-8")

                patched = apply_repository_fix_patch(
                    target_path=example["target_path"],
                    patch=scenario.patch,
                    source_content=source,
                )

                self.assertNotEqual(patched, source)
                self.assertEqual(source_path.read_text(encoding="utf-8"), source)


if __name__ == "__main__":
    unittest.main()
