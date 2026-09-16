"""Tests for deterministic inputs and scoring in the live LLM benchmark."""

from pathlib import Path
import sys
import unittest


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from scripts.benchmark_configured_llm import (
    build_dry_run_manifest,
    build_generation_context,
    evaluate_report,
)
from scripts.validate_recruiter_journey import (
    SCENARIOS,
    build_report,
    load_catalog,
)


class ConfiguredLLMBenchmarkTests(unittest.TestCase):
    """Keep benchmark context and catalog comparisons reproducible."""

    def setUp(self) -> None:
        self.catalog = load_catalog()
        self.examples = {
            example["id"]: example for example in self.catalog["examples"]
        }

    def test_builds_bounded_context_for_every_catalog_example(self) -> None:
        for scenario in SCENARIOS:
            with self.subTest(example=scenario.example_id):
                example = self.examples[scenario.example_id]
                context = build_generation_context(self.catalog, example)

                self.assertEqual(
                    context.selection.target_path,
                    example["target_path"],
                )
                self.assertEqual(context.revision, self.catalog["revision"])
                self.assertEqual(context.subdirectory, example["subdirectory"])
                self.assertEqual(
                    context.documentation_files[0].path,
                    example["behavior_source"]["path"],
                )
                self.assertGreater(context.total_bytes, 0)
                self.assertIsNotNone(context.test_plan)

    def test_catalog_aligned_reports_receive_passing_metadata_scores(self) -> None:
        for scenario in SCENARIOS:
            with self.subTest(example=scenario.example_id):
                example = self.examples[scenario.example_id]
                report = build_report(example, scenario)

                evaluation = evaluate_report(example, report)

                self.assertTrue(evaluation["categories_met"])
                self.assertTrue(evaluation["strategies_met"])
                self.assertTrue(evaluation["documentation_source_cited"])
                self.assertTrue(evaluation["assumptions_match_catalog"])

    def test_dry_run_discloses_payload_without_file_contents(self) -> None:
        manifest = build_dry_run_manifest()

        self.assertTrue(manifest["dry_run"])
        self.assertEqual(manifest["maximum_llm_calls"], 8)
        self.assertEqual(len(manifest["examples"]), 3)
        self.assertGreater(manifest["total_context_bytes"], 0)
        self.assertFalse(manifest["secrets_included"])
        self.assertFalse(manifest["patches_auto_approved_or_applied"])
        for example in manifest["examples"]:
            for file in example["files"]:
                self.assertEqual(set(file), {"path", "bytes"})


if __name__ == "__main__":
    unittest.main()
