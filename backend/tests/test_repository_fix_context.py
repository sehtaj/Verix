"""Tests for bounded, failure-focused repository fix context selection."""

from dataclasses import replace
from pathlib import Path
import sys
import unittest


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from models.fix_proposal import MAX_FIX_CONTEXT_BYTES
from models.investigation import (
    RepositoryCommandEvidence,
    RepositoryInvestigationEvidence,
    RepositoryInvestigationRun,
    RepositoryOutcomeKind,
)
from models.repository import (
    RepositoryConfigurationFile,
    RepositoryFileContent,
    RepositoryGenerationContext,
    RepositoryGenerationSelection,
)
from services.repository_fix_context import (
    GENERATED_TEST_PATH,
    select_repository_fix_context,
)


class RepositoryFixContextSelectionTests(unittest.TestCase):
    """Protect the small evidence set allowed into a future fix prompt."""

    def test_generated_failure_selects_generated_test_and_its_evidence(self) -> None:
        context = self.make_generation_context()
        investigation = self.make_investigation(
            RepositoryOutcomeKind.GENERATED_TESTS_FAILED
        )

        result = select_repository_fix_context(context, investigation)

        self.assertEqual(result.revision, "a" * 40)
        self.assertEqual(result.target_path, "src/sample.py")
        self.assertEqual(result.outcome, RepositoryOutcomeKind.GENERATED_TESTS_FAILED)
        self.assertEqual(len(result.test_files), 1)
        self.assertEqual(result.test_files[0].path, GENERATED_TEST_PATH)
        self.assertEqual(result.test_files[0].content, investigation.generated_tests)
        self.assertEqual(
            result.failure_evidence,
            investigation.evidence.generated_execution,
        )
        self.assertEqual(len(result.configuration_files), 2)
        self.assertIn("requirements.txt", result.skipped_paths)
        self.assertLessEqual(result.total_bytes, MAX_FIX_CONTEXT_BYTES)

    def test_existing_failure_selects_one_related_test_and_existing_evidence(self) -> None:
        context = self.make_generation_context()
        investigation = self.make_investigation(
            RepositoryOutcomeKind.EXISTING_TESTS_FAILED
        )

        result = select_repository_fix_context(context, investigation)

        self.assertEqual(
            [file.path for file in result.test_files],
            ["tests/test_sample.py"],
        )
        self.assertEqual(
            result.failure_evidence,
            investigation.evidence.existing_execution,
        )
        self.assertIn("tests/test_other.py", result.skipped_paths)

    def test_rejects_outcomes_that_do_not_justify_a_source_change(self) -> None:
        context = self.make_generation_context()

        for outcome in (
            RepositoryOutcomeKind.SETUP_FAILED,
            RepositoryOutcomeKind.NO_EXISTING_TESTS,
            RepositoryOutcomeKind.TESTS_PASSED,
        ):
            with self.subTest(outcome=outcome):
                with self.assertRaisesRegex(ValueError, "does not justify"):
                    select_repository_fix_context(
                        context,
                        self.make_investigation(outcome),
                    )

    def test_rejects_unpinned_mismatched_or_incomplete_failure_context(self) -> None:
        context = self.make_generation_context()
        investigation = self.make_investigation(
            RepositoryOutcomeKind.GENERATED_TESTS_FAILED
        )

        context.revision = "main"
        with self.assertRaisesRegex(ValueError, "pinned commit"):
            select_repository_fix_context(context, investigation)

        context.revision = "a" * 40
        with self.assertRaisesRegex(ValueError, "does not match"):
            select_repository_fix_context(
                context,
                replace(investigation, target_path="src/other.py"),
            )

        with self.assertRaisesRegex(ValueError, "evidence is missing"):
            select_repository_fix_context(
                context,
                replace(
                    investigation,
                    evidence=RepositoryInvestigationEvidence(
                        test_runner="pytest",
                        installation=self.command_evidence(return_code=0),
                        existing_execution=self.command_evidence(return_code=0),
                        generated_execution=None,
                    ),
                ),
            )

        with self.assertRaisesRegex(ValueError, "inconsistent"):
            select_repository_fix_context(
                context,
                replace(
                    investigation,
                    evidence=RepositoryInvestigationEvidence(
                        test_runner="pytest",
                        installation=self.command_evidence(return_code=0),
                        existing_execution=self.command_evidence(return_code=0),
                        generated_execution=self.command_evidence(return_code=0),
                    ),
                ),
            )

    @staticmethod
    def make_generation_context() -> RepositoryGenerationContext:
        source_content = "def add(a, b):\n    return a + b\n"
        first_test = "def test_add():\n    assert True\n"
        second_test = "def test_other():\n    assert True\n"
        return RepositoryGenerationContext(
            selection=RepositoryGenerationSelection(
                target_path="src/sample.py",
                related_test_paths=["tests/test_sample.py", "tests/test_other.py"],
                configuration_paths=[
                    "pyproject.toml",
                    "tox.ini",
                    "requirements.txt",
                ],
                is_truncated=False,
            ),
            source_file=RepositoryFileContent(
                path="src/sample.py",
                content=source_content,
                byte_count=len(source_content.encode("utf-8")),
            ),
            test_files=[
                RepositoryFileContent(
                    path="tests/test_sample.py",
                    content=first_test,
                    byte_count=len(first_test.encode("utf-8")),
                ),
                RepositoryFileContent(
                    path="tests/test_other.py",
                    content=second_test,
                    byte_count=len(second_test.encode("utf-8")),
                ),
            ],
            configuration_files=[
                RepositoryConfigurationFile(
                    path="pyproject.toml",
                    content="[tool.pytest.ini_options]\n",
                ),
                RepositoryConfigurationFile(
                    path="tox.ini",
                    content="[tox]\nenvlist = py\n",
                ),
                RepositoryConfigurationFile(
                    path="requirements.txt",
                    content="pytest\n",
                ),
            ],
            skipped_paths=[],
            total_bytes=0,
            revision="a" * 40,
        )

    @classmethod
    def make_investigation(
        cls,
        outcome: RepositoryOutcomeKind,
    ) -> RepositoryInvestigationRun:
        generated_tests = "def test_generated():\n    assert False\n"
        return RepositoryInvestigationRun(
            test_plan=None,  # type: ignore[arg-type]
            target_path="src/sample.py",
            generated_tests=generated_tests,
            execution_results={},
            evidence=RepositoryInvestigationEvidence(
                test_runner="pytest",
                installation=cls.command_evidence(return_code=0),
                existing_execution=cls.command_evidence(
                    return_code=(
                        1
                        if outcome == RepositoryOutcomeKind.EXISTING_TESTS_FAILED
                        else 0
                    ),
                    timed_out=outcome == RepositoryOutcomeKind.EXISTING_TESTS_TIMED_OUT,
                    output="existing failure",
                ),
                generated_execution=cls.command_evidence(
                    return_code=(
                        1
                        if outcome == RepositoryOutcomeKind.GENERATED_TESTS_FAILED
                        else 0
                    ),
                    timed_out=outcome == RepositoryOutcomeKind.GENERATED_TESTS_TIMED_OUT,
                    output="generated failure",
                ),
            ),
            outcome=outcome,
            explanation="The selected test exposed a source behavior problem.",
        )

    @staticmethod
    def command_evidence(
        *,
        return_code: int | None,
        timed_out: bool = False,
        output: str = "",
    ) -> RepositoryCommandEvidence:
        return RepositoryCommandEvidence(
            return_code=return_code,
            timed_out=timed_out,
            skipped=False,
            output_excerpt=output,
            output_truncated=False,
        )


if __name__ == "__main__":
    unittest.main()
