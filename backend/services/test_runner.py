"""Shared contract for local and hosted isolated Python execution."""

from contextlib import AbstractContextManager
from pathlib import Path
from typing import Protocol

from models.execution import RepositoryTestResults, TestExecutionResult


class IsolatedTestRunner(Protocol):
    """Behavior required by repository workflows, independent of provider."""

    def run_tests(self, code: str, tests: str) -> TestExecutionResult: ...

    def repository_workspace(
        self, repository_path: Path
    ) -> AbstractContextManager[Path]: ...

    def execution_workspace(
        self, workspace_path: Path
    ) -> AbstractContextManager[Path]: ...

    def validate_generated_tests(self, generated_tests: str) -> None: ...

    def select_repository_test_runner(self, workspace_path: Path) -> str: ...

    def install_repository_dependencies(
        self, workspace_path: Path
    ) -> TestExecutionResult: ...

    def run_repository_tests(
        self,
        workspace_path: Path,
        test_runner: str | None = None,
        *,
        target_path: str | None = None,
    ) -> TestExecutionResult: ...

    def run_repository_test_sets(
        self,
        workspace_path: Path,
        target_path: str,
        generated_tests: str,
        test_runner: str | None = None,
    ) -> RepositoryTestResults: ...
