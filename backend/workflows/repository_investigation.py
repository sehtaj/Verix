"""Coordinate one bounded repository test investigation without retries."""

from models.execution import TestExecutionResult
from models.investigation import RepositoryInvestigationRun
from services.github_service import GitHubRepositoryService
from services.llm_service import GeminiLLMService
from services.repository_investigation import (
    build_repository_investigation_evidence,
    classify_repository_outcome,
)
from workflows.repository_execution import RepositoryExecutionWorkflow


class RepositoryInvestigationWorkflow:
    """Run the planned repository investigation sequence exactly once."""

    def __init__(
        self,
        github_service: GitHubRepositoryService,
        llm_service: GeminiLLMService,
        execution_workflow: RepositoryExecutionWorkflow,
    ) -> None:
        self.github_service = github_service
        self.llm_service = llm_service
        self.execution_workflow = execution_workflow

    def run(
        self,
        repository_url: str,
        reference: str | None = None,
        subdirectory: str | None = None,
        target_path: str | None = None,
    ) -> RepositoryInvestigationRun:
        """Plan, generate, execute, classify, and explain a repository once."""
        if target_path is not None:
            generation_context = self.github_service.fetch_generation_context(
                repository_url,
                reference,
                subdirectory,
                target_path,
            )
        elif subdirectory is not None:
            generation_context = self.github_service.fetch_generation_context(
                repository_url, reference, subdirectory
            )
        elif reference is not None:
            generation_context = self.github_service.fetch_generation_context(
                repository_url, reference
            )
        else:
            generation_context = self.github_service.fetch_generation_context(
                repository_url
            )
        target_path = generation_context.selection.target_path
        test_plan = generation_context.test_plan
        if (
            target_path is None
            or generation_context.source_file is None
            or test_plan is None
        ):
            raise ValueError(
                "Repository has no Python source file available for test generation."
            )

        generated_tests = self.llm_service.generate_repository_tests(
            generation_context
        )
        self.execution_workflow.validate_generated_tests(generated_tests)

        revision = generation_context.revision
        execution_results = (
            self.execution_workflow.run_existing_and_generated_tests(
                repository_url,
                target_path,
                generated_tests,
                revision,
                subdirectory,
            )
            if subdirectory is not None
            else (
                self.execution_workflow.run_existing_and_generated_tests(
                    repository_url,
                    target_path,
                    generated_tests,
                    revision,
                )
                if revision is not None
                else self.execution_workflow.run_existing_and_generated_tests(
                    repository_url,
                    target_path,
                    generated_tests,
                )
            )
        )
        evidence = build_repository_investigation_evidence(
            test_runner=str(execution_results["test_runner"]),
            installation=_as_execution_result(execution_results["installation"]),
            existing_execution=_as_execution_result(
                execution_results["existing_execution"]
            ),
            generated_execution=_as_execution_result(
                execution_results["generated_execution"]
            ),
        )
        outcome = classify_repository_outcome(evidence)
        explanation = self.llm_service.generate_repository_investigation(
            outcome=outcome,
            evidence=evidence,
        )

        return RepositoryInvestigationRun(
            test_plan=test_plan,
            target_path=target_path,
            generated_tests=generated_tests,
            execution_results=execution_results,
            evidence=evidence,
            outcome=outcome,
            explanation=explanation,
        )


def _as_execution_result(payload: object) -> TestExecutionResult:
    """Convert the established workflow response shape into domain evidence."""
    if not isinstance(payload, dict):
        raise RuntimeError("Repository execution returned invalid result data.")

    return TestExecutionResult(
        return_code=payload["return_code"],
        output=payload["output"],
        timed_out=payload["timed_out"],
        skipped=payload["skipped"],
    )
