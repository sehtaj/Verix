"""Run repository tests against one approved patch in a disposable workspace."""

from dataclasses import dataclass

from models.execution import TestExecutionResult
from models.fix_proposal import RepositoryApprovedFix
from services.docker_runner import DockerTestRunner
from workflows.repository_fix_application import RepositoryFixApplicationWorkflow


@dataclass(frozen=True)
class RepositoryFixVerificationRun:
    """Internal facts from testing one patched temporary repository copy."""

    test_runner: str
    installation: TestExecutionResult
    existing_execution: TestExecutionResult
    exposing_execution: TestExecutionResult


class RepositoryFixVerificationWorkflow:
    """Apply one approved patch, then run the repository's selected test suite."""

    def __init__(
        self,
        application_workflow: RepositoryFixApplicationWorkflow,
        test_runner: DockerTestRunner,
    ) -> None:
        self.application_workflow = application_workflow
        self.test_runner = test_runner

    def run(
        self,
        repository_url: str,
        approved_fix: RepositoryApprovedFix,
    ) -> RepositoryFixVerificationRun:
        """Run existing and exposing tests while the patched copy exists."""
        self.test_runner.validate_generated_tests(approved_fix.generated_tests)
        with self.application_workflow.apply(
            repository_url,
            approved_fix,
        ) as applied_workspace:
            selected_runner = self.test_runner.select_repository_test_runner(
                applied_workspace.path
            )
            installation = self.test_runner.install_repository_dependencies(
                applied_workspace.path
            )
            if installation.return_code != 0 or installation.timed_out:
                existing_execution = TestExecutionResult(
                    return_code=None,
                    output=(
                        "Existing repository tests were not run because dependency "
                        "installation failed."
                    ),
                    skipped=True,
                )
                exposing_execution = TestExecutionResult(
                    return_code=None,
                    output=(
                        "The generated exposing test was not run because dependency "
                        "installation failed."
                    ),
                    skipped=True,
                )
            else:
                test_results = self.test_runner.run_repository_test_sets(
                    applied_workspace.path,
                    applied_workspace.target_path,
                    approved_fix.generated_tests,
                    selected_runner,
                )
                existing_execution = test_results.existing
                exposing_execution = test_results.generated

        return RepositoryFixVerificationRun(
            test_runner=selected_runner,
            installation=installation,
            existing_execution=existing_execution,
            exposing_execution=exposing_execution,
        )
