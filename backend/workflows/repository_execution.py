"""Coordinate preparation and isolated execution for public repositories."""

from pathlib import PurePosixPath

from services.docker_runner import DockerTestRunner
from services.repository_preparer import PublicRepositoryPreparer


class RepositoryExecutionWorkflow:
    """Prepare repositories, install dependencies, and run their test sets."""

    def __init__(
        self,
        repository_preparer: PublicRepositoryPreparer,
        test_runner: DockerTestRunner,
    ) -> None:
        self.repository_preparer = repository_preparer
        self.test_runner = test_runner

    def run_existing_tests(
        self,
        repository_url: str,
        revision: str | None = None,
        subdirectory: str | None = None,
    ) -> dict[str, object]:
        """Run a repository's existing tests in an isolated workspace."""
        preparation = (
            self.repository_preparer.prepare(
                repository_url, revision, subdirectory
            )
            if subdirectory is not None
            else (
                self.repository_preparer.prepare(repository_url, revision)
                if revision is not None
                else self.repository_preparer.prepare(repository_url)
            )
        )
        with preparation as prepared_repository:
            preparation = {
                "file_count": prepared_repository.file_count,
                "total_bytes": prepared_repository.total_bytes,
                "skipped_entries": prepared_repository.skipped_entries,
            }
            with self.test_runner.repository_workspace(
                prepared_repository.path
            ) as workspace_path:
                selected_runner = self.test_runner.select_repository_test_runner(
                    workspace_path
                )
                installation = self.test_runner.install_repository_dependencies(
                    workspace_path
                )

                if installation.return_code != 0 or installation.timed_out:
                    execution = {
                        "return_code": None,
                        "output": (
                            "Repository tests were not run because dependency "
                            "installation failed."
                        ),
                        "timed_out": False,
                        "skipped": True,
                    }
                else:
                    test_execution = self.test_runner.run_repository_tests(
                        workspace_path, selected_runner
                    )
                    execution = {
                        "return_code": test_execution.return_code,
                        "output": test_execution.output,
                        "timed_out": test_execution.timed_out,
                        "skipped": False,
                    }

        return {
            "preparation": preparation,
            "installation": {
                "return_code": installation.return_code,
                "output": installation.output,
                "timed_out": installation.timed_out,
                "skipped": installation.skipped,
            },
            "test_runner": selected_runner,
            "execution": execution,
        }

    def validate_generated_tests(self, generated_tests: str) -> None:
        """Reject invalid generated tests before repository preparation begins."""
        self.test_runner.validate_generated_tests(generated_tests)

    def run_existing_and_generated_tests(
        self,
        repository_url: str,
        target_path: str,
        generated_tests: str,
        revision: str | None = None,
        subdirectory: str | None = None,
    ) -> dict[str, object]:
        """Run existing and generated tests after one shared preparation step."""
        preparation = (
            self.repository_preparer.prepare(
                repository_url, revision, subdirectory
            )
            if subdirectory is not None
            else (
                self.repository_preparer.prepare(repository_url, revision)
                if revision is not None
                else self.repository_preparer.prepare(repository_url)
            )
        )
        project_target_path = self._project_target_path(
            target_path, subdirectory
        )
        with preparation as prepared_repository:
            preparation = {
                "file_count": prepared_repository.file_count,
                "total_bytes": prepared_repository.total_bytes,
                "skipped_entries": prepared_repository.skipped_entries,
            }
            with self.test_runner.repository_workspace(
                prepared_repository.path
            ) as workspace_path:
                selected_runner = self.test_runner.select_repository_test_runner(
                    workspace_path
                )
                installation = self.test_runner.install_repository_dependencies(
                    workspace_path
                )

                if installation.return_code != 0 or installation.timed_out:
                    existing_execution = {
                        "return_code": None,
                        "output": (
                            "Existing repository tests were not run because dependency "
                            "installation failed."
                        ),
                        "timed_out": False,
                        "skipped": True,
                    }
                    generated_execution = {
                        "return_code": None,
                        "output": (
                            "Generated repository tests were not run because dependency "
                            "installation failed."
                        ),
                        "timed_out": False,
                        "skipped": True,
                    }
                else:
                    test_results = self.test_runner.run_repository_test_sets(
                        workspace_path,
                        project_target_path,
                        generated_tests,
                        selected_runner,
                    )
                    existing_execution = {
                        "return_code": test_results.existing.return_code,
                        "output": test_results.existing.output,
                        "timed_out": test_results.existing.timed_out,
                        "skipped": test_results.existing.skipped,
                    }
                    generated_execution = {
                        "return_code": test_results.generated.return_code,
                        "output": test_results.generated.output,
                        "timed_out": test_results.generated.timed_out,
                        "skipped": test_results.generated.skipped,
                    }

        return {
            "preparation": preparation,
            "installation": {
                "return_code": installation.return_code,
                "output": installation.output,
                "timed_out": installation.timed_out,
                "skipped": installation.skipped,
            },
            "test_runner": selected_runner,
            "existing_execution": existing_execution,
            "generated_execution": generated_execution,
        }

    @staticmethod
    def _project_target_path(
        target_path: str, subdirectory: str | None
    ) -> str:
        """Translate a repository-relative source path into the project workspace."""
        if subdirectory is None:
            return target_path

        try:
            relative_target = PurePosixPath(target_path).relative_to(
                PurePosixPath(subdirectory)
            )
        except ValueError:
            raise ValueError(
                "Repository source target is outside the selected subdirectory."
            ) from None
        if not relative_target.parts:
            raise ValueError("Repository source target is invalid.")
        return relative_target.as_posix()
