"""Tests for one review-only repository fix-proposal workflow."""

from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

from fastapi import HTTPException


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from api.presenters import present_repository_fix_proposal_run
import main as main_module
from models.fix_proposal import RepositoryFixProposal, RepositoryFixProposalRun
from models.investigation import (
    RepositoryCommandEvidence,
    RepositoryInvestigationEvidence,
    RepositoryInvestigationRun,
    RepositoryOutcomeKind,
)
from models.repository import (
    PythonProjectSetup,
    RepositoryFileContent,
    RepositoryGenerationContext,
    RepositoryGenerationSelection,
    RepositoryTestPlan,
)
from workflows.repository_fix_proposal import RepositoryFixProposalWorkflow


class RepositoryFixProposalWorkflowTests(unittest.TestCase):
    """Protect the single investigation-to-proposal sequence."""

    def test_generates_one_proposal_without_applying_it(self) -> None:
        investigation = RepositoryFixProposalApiTests.make_investigation()
        investigation_workflow = Mock()
        investigation_workflow.run.return_value = investigation
        llm_service = Mock()
        llm_service.generate_repository_fix_proposal.return_value = (
            RepositoryFixProposal(
                revision="a" * 40,
                subdirectory=None,
                target_path="src/sample.py",
                summary="Use addition for this function.",
                patch=(
                    "--- a/src/sample.py\n"
                    "+++ b/src/sample.py\n"
                    "@@ -1,2 +1,2 @@\n"
                    " def add(a, b):\n"
                    "-    return a - b\n"
                    "+    return a + b\n"
                ),
            )
        )
        workflow = RepositoryFixProposalWorkflow(
            investigation_workflow,
            llm_service,
        )

        result = workflow.run(
            "https://github.com/example/sample",
            "main",
            None,
            "src/sample.py",
        )

        investigation_workflow.run.assert_called_once_with(
            "https://github.com/example/sample",
            "main",
            None,
            "src/sample.py",
        )
        llm_service.generate_repository_fix_proposal.assert_called_once()
        fix_context = llm_service.generate_repository_fix_proposal.call_args.args[0]
        self.assertEqual(fix_context.revision, "a" * 40)
        self.assertEqual(fix_context.target_path, "src/sample.py")
        self.assertEqual(result.investigation, investigation)
        self.assertTrue(result.proposal.approval_required)
        self.assertFalse(result.proposal.applied)

        response = present_repository_fix_proposal_run(result)
        self.assertEqual(response["proposal"]["revision"], "a" * 40)
        self.assertEqual(response["proposal"]["target_path"], "src/sample.py")
        self.assertTrue(response["proposal"]["validated"])
        self.assertTrue(response["proposal"]["approval_required"])
        self.assertFalse(response["proposal"]["applied"])

    def test_missing_preserved_context_stops_before_gemini(self) -> None:
        investigation = RepositoryFixProposalApiTests.make_investigation()
        investigation = RepositoryInvestigationRun(
            test_plan=investigation.test_plan,
            target_path=investigation.target_path,
            generated_tests=investigation.generated_tests,
            execution_results=investigation.execution_results,
            evidence=investigation.evidence,
            outcome=investigation.outcome,
            explanation=investigation.explanation,
        )
        investigation_workflow = Mock()
        investigation_workflow.run.return_value = investigation
        llm_service = Mock()
        workflow = RepositoryFixProposalWorkflow(
            investigation_workflow,
            llm_service,
        )

        with self.assertRaisesRegex(RuntimeError, "did not preserve"):
            workflow.run("https://github.com/example/sample")

        llm_service.generate_repository_fix_proposal.assert_not_called()

    def test_invalid_generated_patch_is_rejected_before_it_can_be_reviewed(self) -> None:
        investigation = RepositoryFixProposalApiTests.make_investigation()
        investigation_workflow = Mock()
        investigation_workflow.run.return_value = investigation
        llm_service = Mock()
        llm_service.generate_repository_fix_proposal.return_value = (
            RepositoryFixProposal(
                revision="a" * 40,
                subdirectory=None,
                target_path="src/sample.py",
                summary="Change an unrelated line.",
                patch=(
                    "--- a/src/sample.py\n"
                    "+++ b/src/sample.py\n"
                    "@@ -1,2 +1,2 @@\n"
                    " def different(a, b):\n"
                    "-    return a - b\n"
                    "+    return a + b\n"
                ),
            )
        )
        workflow = RepositoryFixProposalWorkflow(
            investigation_workflow,
            llm_service,
        )

        with self.assertRaisesRegex(RuntimeError, "failed validation"):
            workflow.run(
                "https://github.com/example/sample",
                "main",
                None,
                "src/sample.py",
            )


class RepositoryFixProposalApiTests(unittest.TestCase):
    """Protect deterministic API coordination and safe public errors."""

    def test_endpoint_preserves_targeting_and_returns_review_only_patch(self) -> None:
        investigation = self.make_investigation()
        proposal = RepositoryFixProposal(
            revision="a" * 40,
            subdirectory=None,
            target_path="src/sample.py",
            summary="Use addition for this function.",
            patch=(
                "--- a/src/sample.py\n"
                "+++ b/src/sample.py\n"
                "@@ -1,2 +1,2 @@\n"
                " def add(a, b):\n"
                "-    return a - b\n"
                "+    return a + b\n"
            ),
        )
        workflow = Mock()
        workflow.run.return_value = RepositoryFixProposalRun(
            investigation=investigation,
            proposal=proposal,
        )

        with (
            patch.object(main_module, "llm_service", Mock()),
            patch.object(
                main_module,
                "RepositoryFixProposalWorkflow",
                return_value=workflow,
            ),
        ):
            response = main_module.propose_repository_fix(
                main_module.RepositoryFixProposalRequest(
                    url="https://github.com/example/sample",
                    reference="feature/v0.11",
                    target_path="src/sample.py",
                )
            )

        workflow.run.assert_called_once_with(
            "https://github.com/example/sample",
            "feature/v0.11",
            None,
            "src/sample.py",
        )
        self.assertEqual(response["proposal"]["revision"], "a" * 40)
        self.assertTrue(response["proposal"]["validated"])
        self.assertTrue(response["proposal"]["approval_required"])
        self.assertFalse(response["proposal"]["applied"])

    def test_endpoint_requires_gemini_configuration(self) -> None:
        with (
            patch.object(main_module, "llm_service", None),
            self.assertRaises(HTTPException) as raised,
        ):
            main_module.propose_repository_fix(
                main_module.RepositoryFixProposalRequest(
                    url="https://github.com/example/sample",
                    target_path="src/sample.py",
                )
            )

        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(raised.exception.detail, "LLM service is not configured.")

    def test_endpoint_maps_expected_failures_to_safe_statuses(self) -> None:
        failures = (
            (ValueError("Tests passed; no fix is justified."), 422),
            (RuntimeError("sensitive Gemini detail"), 502),
        )

        for failure, expected_status in failures:
            with self.subTest(failure=type(failure).__name__):
                workflow = Mock()
                workflow.run.side_effect = failure
                with (
                    patch.object(main_module, "llm_service", Mock()),
                    patch.object(
                        main_module,
                        "RepositoryFixProposalWorkflow",
                        return_value=workflow,
                    ),
                    self.assertRaises(HTTPException) as raised,
                ):
                    main_module.propose_repository_fix(
                        main_module.RepositoryFixProposalRequest(
                            url="https://github.com/example/sample",
                            target_path="src/sample.py",
                        )
                    )

                self.assertEqual(raised.exception.status_code, expected_status)
                if expected_status == 422:
                    self.assertIn("no fix is justified", raised.exception.detail)
                else:
                    self.assertEqual(
                        raised.exception.detail,
                        "Unable to propose a repository fix. Please try again.",
                    )

    @classmethod
    def make_investigation(cls) -> RepositoryInvestigationRun:
        source = "def add(a, b):\n    return a - b\n"
        generated_tests = "def test_add():\n    assert add(2, 3) == 5\n"
        context = RepositoryGenerationContext(
            selection=RepositoryGenerationSelection(
                target_path="src/sample.py",
                related_test_paths=[],
                configuration_paths=[],
                is_truncated=False,
            ),
            source_file=RepositoryFileContent(
                path="src/sample.py",
                content=source,
                byte_count=len(source.encode("utf-8")),
            ),
            test_files=[],
            configuration_files=[],
            skipped_paths=[],
            total_bytes=len(source.encode("utf-8")),
            revision="a" * 40,
        )
        return RepositoryInvestigationRun(
            test_plan=RepositoryTestPlan(
                setup=PythonProjectSetup(
                    is_python_project=True,
                    project_tool=None,
                    test_runner="pytest",
                    configuration_files=[],
                ),
                source_paths=["src/sample.py"],
                test_paths=[],
                steps=[],
                is_truncated=False,
            ),
            target_path="src/sample.py",
            generated_tests=generated_tests,
            execution_results={},
            evidence=RepositoryInvestigationEvidence(
                test_runner="pytest",
                installation=cls.command_evidence(return_code=0),
                existing_execution=cls.command_evidence(return_code=0),
                generated_execution=cls.command_evidence(
                    return_code=1,
                    output="assert -1 == 5",
                ),
            ),
            outcome=RepositoryOutcomeKind.GENERATED_TESTS_FAILED,
            explanation="The generated addition test failed.",
            generation_context=context,
        )

    @staticmethod
    def command_evidence(
        *,
        return_code: int | None,
        output: str = "",
    ) -> RepositoryCommandEvidence:
        return RepositoryCommandEvidence(
            return_code=return_code,
            timed_out=False,
            skipped=False,
            output_excerpt=output,
            output_truncated=False,
        )


if __name__ == "__main__":
    unittest.main()
