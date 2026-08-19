"""Deterministic tests for Gemini repository test generation."""

from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from services.github_service import (
    RepositoryFileContent,
    RepositoryGenerationContext,
    RepositoryGenerationSelection,
)
from services.llm_service import GeminiLLMService, MODEL_NAME
from models.investigation import (
    RepositoryInvestigationEvidence,
    RepositoryCommandEvidence,
    RepositoryOutcomeKind,
)
from services.llm_service import MAX_INVESTIGATION_EXPLANATION_CHARACTERS


class RepositoryLLMServiceTests(unittest.TestCase):
    """Protect the repository prompt-to-Gemini generation boundary."""

    @staticmethod
    def make_context() -> RepositoryGenerationContext:
        source_content = "def add(a, b):\n    return a + b\n"
        return RepositoryGenerationContext(
            selection=RepositoryGenerationSelection(
                target_path="src/sample.py",
                related_test_paths=[],
                configuration_paths=[],
                is_truncated=False,
            ),
            source_file=RepositoryFileContent(
                path="src/sample.py",
                content=source_content,
                byte_count=len(source_content.encode("utf-8")),
            ),
            test_files=[],
            configuration_files=[],
            skipped_paths=[],
            total_bytes=len(source_content.encode("utf-8")),
        )

    @staticmethod
    def make_service(response_text: str | None) -> GeminiLLMService:
        service = GeminiLLMService.__new__(GeminiLLMService)
        service.client = Mock()
        service.client.models.generate_content.return_value = SimpleNamespace(
            text=response_text
        )
        return service

    def test_generate_repository_tests_sends_bounded_context_prompt(self) -> None:
        generated_tests = (
            "from sample import add\n\n"
            "def test_add():\n    assert add(2, 3) == 5\n"
        )
        service = self.make_service(generated_tests)

        result = service.generate_repository_tests(self.make_context())

        self.assertEqual(result, generated_tests)
        service.client.models.generate_content.assert_called_once()
        call = service.client.models.generate_content.call_args
        self.assertEqual(call.kwargs["model"], MODEL_NAME)
        prompt = call.kwargs["contents"]
        self.assertIn("Selected target: src/sample.py", prompt)
        self.assertIn("def add(a, b)", prompt)
        self.assertIn("Return only the complete pytest module", prompt)

    def test_generate_repository_tests_rejects_an_empty_gemini_response(self) -> None:
        service = self.make_service("   \n")

        with self.assertRaisesRegex(RuntimeError, "empty response"):
            service.generate_repository_tests(self.make_context())

    def test_gemini_request_failures_are_normalized_to_runtime_errors(self) -> None:
        service = self.make_service("unused")
        service.client.models.generate_content.side_effect = Exception("unavailable")

        with self.assertRaisesRegex(RuntimeError, "could not generate"):
            service.generate_repository_tests(self.make_context())

    def test_existing_pasted_code_generation_still_uses_main_module_prompt(self) -> None:
        generated_tests = "from main import add\n"
        service = self.make_service(generated_tests)

        result = service.generate_tests("def add(a, b): return a + b")

        self.assertEqual(result, generated_tests)
        call = service.client.models.generate_content.call_args
        self.assertEqual(call.kwargs["model"], MODEL_NAME)
        self.assertIn("available as main.py", call.kwargs["contents"])
        self.assertIn("def add(a, b)", call.kwargs["contents"])

    def test_invalid_context_is_rejected_before_calling_gemini(self) -> None:
        service = self.make_service("unused")
        context = self.make_context()
        context.source_file = None

        with self.assertRaisesRegex(ValueError, "source file is required"):
            service.generate_repository_tests(context)

        service.client.models.generate_content.assert_not_called()

    def test_generates_an_evidence_grounded_repository_explanation(self) -> None:
        service = self.make_service("The existing suite has one failing test.\n")

        explanation = service.generate_repository_investigation(
            outcome=RepositoryOutcomeKind.EXISTING_TESTS_FAILED,
            evidence=self.make_investigation_evidence(),
        )

        self.assertEqual(explanation, "The existing suite has one failing test.")
        call = service.client.models.generate_content.call_args
        self.assertEqual(call.kwargs["model"], MODEL_NAME)
        self.assertIn("existing_tests_failed", call.kwargs["contents"])
        self.assertIn("existing failure output", call.kwargs["contents"])
        self.assertIn("do not reclassify it", call.kwargs["contents"])

    def test_bounds_an_overlong_repository_explanation(self) -> None:
        service = self.make_service("x" * (MAX_INVESTIGATION_EXPLANATION_CHARACTERS + 1))

        explanation = service.generate_repository_investigation(
            outcome=RepositoryOutcomeKind.EXISTING_TESTS_FAILED,
            evidence=self.make_investigation_evidence(),
        )

        self.assertEqual(len(explanation), MAX_INVESTIGATION_EXPLANATION_CHARACTERS)
        self.assertTrue(explanation.endswith("..."))

    @staticmethod
    def make_investigation_evidence() -> RepositoryInvestigationEvidence:
        return RepositoryInvestigationEvidence(
            test_runner="pytest",
            installation=RepositoryCommandEvidence(
                return_code=0,
                timed_out=False,
                skipped=False,
                output_excerpt="installation complete",
                output_truncated=False,
            ),
            existing_execution=RepositoryCommandEvidence(
                return_code=1,
                timed_out=False,
                skipped=False,
                output_excerpt="existing failure output",
                output_truncated=False,
            ),
            generated_execution=None,
        )


if __name__ == "__main__":
    unittest.main()
