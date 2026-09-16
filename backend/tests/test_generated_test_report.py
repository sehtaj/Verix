"""Tests for grounded generated-test provenance validation."""

import json
from pathlib import Path
import sys
import unittest


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from models.repository import (
    RepositoryFileContent,
    RepositoryGenerationContext,
    RepositoryGenerationSelection,
)
from services.generated_test_report import parse_generated_test_report


class GeneratedTestReportTests(unittest.TestCase):
    """Reject provenance that is not present in the bounded context."""

    @staticmethod
    def make_context() -> RepositoryGenerationContext:
        source = "def classify(value):\n    return value > 0\n"
        documentation = "Values greater than zero are positive.\n"
        return RepositoryGenerationContext(
            selection=RepositoryGenerationSelection(
                target_path="src/classifier.py",
                related_test_paths=[],
                configuration_paths=[],
                is_truncated=False,
                documentation_paths=["README.md"],
            ),
            source_file=RepositoryFileContent(
                path="src/classifier.py",
                content=source,
                byte_count=len(source.encode()),
            ),
            test_files=[],
            configuration_files=[],
            skipped_paths=[],
            total_bytes=len(source.encode()) + len(documentation.encode()),
            documentation_files=[
                RepositoryFileContent(
                    path="README.md",
                    content=documentation,
                    byte_count=len(documentation.encode()),
                )
            ],
        )

    @staticmethod
    def make_payload() -> dict[str, object]:
        return {
            "tests": "def test_positive():\n    assert True\n",
            "sources": [
                {
                    "kind": "documentation",
                    "path": "README.md",
                    "excerpt": "greater than zero",
                }
            ],
            "assumptions": ["Non-integer inputs are outside this focused run."],
            "cases": [
                {
                    "test_name": "test_positive",
                    "category": "normal",
                    "strategy": "black_box",
                    "expected_behavior": "Positive values are classified as positive.",
                }
            ],
        }

    def test_accepts_grounded_sources_and_explicit_assumptions(self) -> None:
        report = parse_generated_test_report(
            json.dumps(self.make_payload()), self.make_context(), "gemini-test"
        )

        self.assertEqual(report.model, "gemini-test")
        self.assertEqual(report.sources[0].path, "README.md")
        self.assertIn("Non-integer", report.assumptions[0])
        self.assertEqual(report.cases[0].category.value, "normal")

    def test_rejects_a_source_or_excerpt_outside_bounded_context(self) -> None:
        for path, excerpt in (
            ("MISSING.md", "greater than zero"),
            ("README.md", "fabricated contract"),
        ):
            with self.subTest(path=path, excerpt=excerpt):
                payload = self.make_payload()
                payload["sources"][0] = {
                    "kind": "documentation",
                    "path": path,
                    "excerpt": excerpt,
                }
                with self.assertRaisesRegex(
                    RuntimeError, "invalid generated-test report"
                ):
                    parse_generated_test_report(
                        json.dumps(payload), self.make_context(), "gemini-test"
                    )

    def test_requires_at_least_one_source_and_one_pytest_function(self) -> None:
        payload = self.make_payload()
        payload["sources"] = []
        with self.assertRaisesRegex(RuntimeError, "invalid generated-test report"):
            parse_generated_test_report(
                json.dumps(payload), self.make_context(), "gemini-test"
            )

        payload = self.make_payload()
        payload["tests"] = "VALUE = 1\n"
        with self.assertRaisesRegex(RuntimeError, "invalid generated-test report"):
            parse_generated_test_report(
                json.dumps(payload), self.make_context(), "gemini-test"
            )

    def test_requires_exactly_one_valid_classification_per_test(self) -> None:
        payload = self.make_payload()
        payload["cases"] = []
        with self.assertRaisesRegex(RuntimeError, "invalid generated-test report"):
            parse_generated_test_report(
                json.dumps(payload), self.make_context(), "gemini-test"
            )

        payload = self.make_payload()
        payload["cases"][0]["category"] = "performance"
        with self.assertRaisesRegex(RuntimeError, "invalid generated-test report"):
            parse_generated_test_report(
                json.dumps(payload), self.make_context(), "gemini-test"
            )

        payload = self.make_payload()
        payload["tests"] += "\n\ndef test_zero():\n    assert True\n"
        with self.assertRaisesRegex(RuntimeError, "invalid generated-test report"):
            parse_generated_test_report(
                json.dumps(payload), self.make_context(), "gemini-test"
            )

if __name__ == "__main__":
    unittest.main()
