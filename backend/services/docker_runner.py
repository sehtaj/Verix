"""Run generated and repository Python commands in isolated Docker containers."""

from contextlib import AbstractContextManager
import os
from pathlib import Path
import subprocess
import tempfile
from uuid import uuid4

from models.execution import RepositoryTestResults, TestExecutionResult
from services.docker_commands import DockerCommandBuilder
from services.docker_executor import DockerProcessExecutor
from services.repository_dependencies import (
    PROJECT_CONFIGURATION_READ_LIMIT,
    REQUIREMENTS_FILENAMES,
    REPOSITORY_VENV_DIRECTORY,
    RepositoryDependencyPlanner,
)
from services.repository_test_commands import (
    TOX_ENVIRONMENT_NAME_PATTERN,
    TOX_PYTHON_ENVIRONMENT_PATTERN,
    RepositoryTestCommandPlanner,
)
from services.repository_workspace import (
    GENERATED_TEST_DIRECTORY,
    GENERATED_TEST_FILENAME,
    MAX_GENERATED_TEST_BYTES,
    GeneratedTestsValidationError,
    RepositoryWorkspaceManager,
)


RUNNER_IMAGE = "verix-test-runner:dev"
DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_REPOSITORY_TIMEOUT_SECONDS = 60
DEPENDENCY_INSTALL_TIMEOUT_SECONDS = 180
REPOSITORY_TEST_TIMEOUT_SECONDS = 60
MAX_CAPTURED_OUTPUT_CHARACTERS = 50_000
REPOSITORY_TOX_DIRECTORY = ".verix-tox"


class DockerTestRunner:
    """Execute Python commands without running untrusted code on the host."""

    def __init__(
        self,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        workspace_manager: RepositoryWorkspaceManager | None = None,
        dependency_planner: RepositoryDependencyPlanner | None = None,
        test_command_planner: RepositoryTestCommandPlanner | None = None,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.workspace_manager = (
            workspace_manager
            if workspace_manager is not None
            else RepositoryWorkspaceManager()
        )
        self.dependency_planner = (
            dependency_planner
            if dependency_planner is not None
            else RepositoryDependencyPlanner()
        )
        self.test_command_planner = (
            test_command_planner
            if test_command_planner is not None
            else RepositoryTestCommandPlanner()
        )

    def run_tests(self, code: str, tests: str) -> TestExecutionResult:
        """Run pytest against code and tests written to a temporary workspace."""
        with tempfile.TemporaryDirectory() as workspace:
            workspace_path = Path(workspace)
            container_name = f"verix-test-runner-{uuid4().hex}"
            os.chmod(workspace_path, 0o755)
            self._write_file(workspace_path / "main.py", code)
            self._write_file(workspace_path / "test_generated.py", tests)

            return self._run_container(
                command=self._docker_command(workspace_path, container_name),
                container_name=container_name,
                timeout_seconds=self.timeout_seconds,
                timeout_message="Test execution timed out.",
            )

    def repository_workspace(
        self, repository_path: Path
    ) -> AbstractContextManager[Path]:
        """Yield an isolated writable copy of a prepared repository, then remove it."""
        return self.workspace_manager.create(repository_path)

    def write_repository_generated_tests(
        self,
        workspace_path: Path,
        target_path: str,
        generated_tests: str,
    ) -> Path:
        """Safely add one generated pytest module to a disposable repository copy."""
        return self.workspace_manager.write_generated_tests(
            workspace_path,
            target_path,
            generated_tests,
            maximum_bytes=MAX_GENERATED_TEST_BYTES,
        )

    @staticmethod
    def validate_generated_tests(generated_tests: str) -> None:
        """Reject unusable generated code before repository setup or execution."""
        RepositoryWorkspaceManager.validate_generated_tests(
            generated_tests,
            maximum_bytes=MAX_GENERATED_TEST_BYTES,
        )

    def run_repository_test_sets(
        self,
        workspace_path: Path,
        target_path: str,
        generated_tests: str,
        test_runner: str | None = None,
    ) -> RepositoryTestResults:
        """Run the original suite first, then run only the generated pytest file."""
        existing_result = self.run_repository_tests(workspace_path, test_runner)
        self.write_repository_generated_tests(
            workspace_path,
            target_path,
            generated_tests,
        )
        generated_result = self.run_repository_generated_tests(
            workspace_path, test_runner
        )
        return RepositoryTestResults(
            existing=existing_result,
            generated=generated_result,
        )

    def run_repository_generated_tests(
        self,
        workspace_path: Path,
        test_runner: str | None = None,
    ) -> TestExecutionResult:
        """Run only Verix's generated pytest module without network access."""
        if not workspace_path.is_dir():
            raise ValueError("Repository workspace directory does not exist.")

        generated_test_path = (
            workspace_path / GENERATED_TEST_DIRECTORY / GENERATED_TEST_FILENAME
        )
        if generated_test_path.is_symlink() or not generated_test_path.is_file():
            raise ValueError("Generated repository test file does not exist.")

        selected_runner = test_runner or self.select_repository_test_runner(
            workspace_path
        )
        if selected_runner not in {"pytest", "tox"}:
            raise ValueError("Repository test runner must be pytest or tox.")

        python_command, environment = self._repository_python_environment(
            workspace_path
        )
        tox_environment: str | None = None
        if selected_runner == "tox":
            list_result = self.run_repository_command(
                workspace_path,
                self.test_command_planner.build_tox_environment_list_command(
                    python_command
                ),
                allow_network=False,
                environment=environment,
                workspace_read_only=True,
                timeout_seconds=REPOSITORY_TEST_TIMEOUT_SECONDS,
            )
            if list_result.return_code != 0 or list_result.timed_out:
                return list_result

            tox_environment = self.test_command_planner.select_tox_environment(
                list_result.output
            )
            if tox_environment is None:
                return TestExecutionResult(
                    return_code=2,
                    output="Tox did not report a default test environment.",
                )

        command = self.test_command_planner.build_generated_test_command(
            python_command,
            selected_runner,
            tox_environment=tox_environment,
        )

        return self.run_repository_command(
            workspace_path,
            command,
            allow_network=False,
            environment=environment,
            workspace_read_only=True,
            timeout_seconds=REPOSITORY_TEST_TIMEOUT_SECONDS,
        )

    def run_repository_command(
        self,
        workspace_path: Path,
        command: list[str],
        *,
        allow_network: bool = False,
        environment: dict[str, str] | None = None,
        workspace_read_only: bool = False,
        timeout_seconds: int = DEFAULT_REPOSITORY_TIMEOUT_SECONDS,
    ) -> TestExecutionResult:
        """Run a backend-selected command inside a hardened repository container."""
        if not workspace_path.is_dir():
            raise ValueError("Repository workspace directory does not exist.")
        if not command or any(not argument for argument in command):
            raise ValueError("Repository command cannot be empty.")
        environment = environment or {}
        if any(
            not name.isidentifier()
            or name.upper() != name
            or "\x00" in value
            for name, value in environment.items()
        ):
            raise ValueError("Repository command environment is invalid.")
        if timeout_seconds <= 0:
            raise ValueError("Repository command timeout must be greater than zero.")

        container_name = f"verix-repository-runner-{uuid4().hex}"
        return self._run_container(
            command=self._repository_docker_command(
                workspace_path,
                container_name,
                command,
                allow_network=allow_network,
                environment=environment,
                workspace_read_only=workspace_read_only,
            ),
            container_name=container_name,
            timeout_seconds=timeout_seconds,
            timeout_message="Repository command timed out.",
        )

    def install_repository_dependencies(
        self, workspace_path: Path
    ) -> TestExecutionResult:
        """Install declared Python dependencies into the disposable workspace."""
        if not workspace_path.is_dir():
            raise ValueError("Repository workspace directory does not exist.")

        for reserved_directory in (
            REPOSITORY_VENV_DIRECTORY,
            REPOSITORY_TOX_DIRECTORY,
        ):
            reserved_path = workspace_path / reserved_directory
            if reserved_path.exists() or reserved_path.is_symlink():
                raise ValueError(
                    f"Repository contains the reserved {reserved_directory} path."
                )

        installation_commands = self._dependency_install_commands(workspace_path)
        if not installation_commands:
            return TestExecutionResult(
                return_code=0,
                output="No supported dependency declaration was found; installation was skipped.\n",
                skipped=True,
            )

        outputs = []
        create_environment = self.run_repository_command(
            workspace_path,
            [
                "python",
                "-m",
                "venv",
                "--system-site-packages",
                REPOSITORY_VENV_DIRECTORY,
            ],
        )
        outputs.append(
            self._format_dependency_step(
                "Create isolated virtual environment", create_environment
            )
        )
        if create_environment.return_code != 0 or create_environment.timed_out:
            return TestExecutionResult(
                return_code=create_environment.return_code,
                output=self._limit_output("".join(outputs)),
                timed_out=create_environment.timed_out,
            )

        dependency_environment = {
            "PDM_CHECK_UPDATE": "false",
            "PIPENV_IGNORE_VIRTUALENVS": "0",
            "PIPENV_NOSPIN": "1",
            "PIPENV_YES": "1",
            "POETRY_NO_INTERACTION": "1",
            "VIRTUAL_ENV": f"/workspace/{REPOSITORY_VENV_DIRECTORY}",
        }
        for label, command in installation_commands:
            result = self.run_repository_command(
                workspace_path,
                command,
                allow_network=True,
                environment=dependency_environment,
                timeout_seconds=DEPENDENCY_INSTALL_TIMEOUT_SECONDS,
            )
            outputs.append(self._format_dependency_step(label, result))
            if result.return_code != 0 or result.timed_out:
                return TestExecutionResult(
                    return_code=result.return_code,
                    output=self._limit_output("".join(outputs)),
                    timed_out=result.timed_out,
                )

        return TestExecutionResult(
            return_code=0,
            output=self._limit_output("".join(outputs)),
        )

    def run_repository_tests(
        self, workspace_path: Path, test_runner: str | None = None
    ) -> TestExecutionResult:
        """Run the complete existing repository test suite without network access."""
        if not workspace_path.is_dir():
            raise ValueError("Repository workspace directory does not exist.")

        selected_runner = test_runner or self.select_repository_test_runner(
            workspace_path
        )
        if selected_runner not in {"pytest", "tox"}:
            raise ValueError("Repository test runner must be pytest or tox.")

        python_command, environment = self._repository_python_environment(
            workspace_path
        )

        command = self.test_command_planner.build_existing_test_command(
            python_command, selected_runner
        )

        return self.run_repository_command(
            workspace_path,
            command,
            allow_network=False,
            environment=environment,
            workspace_read_only=True,
            timeout_seconds=REPOSITORY_TEST_TIMEOUT_SECONDS,
        )

    @staticmethod
    def select_repository_test_runner(workspace_path: Path) -> str:
        """Select tox when configured and otherwise use pytest discovery."""
        return RepositoryTestCommandPlanner.select_test_runner(workspace_path)

    @staticmethod
    def _repository_python_environment(
        workspace_path: Path,
    ) -> tuple[str, dict[str, str]]:
        """Use the prepared repository environment when one is available."""
        return RepositoryTestCommandPlanner.python_environment(workspace_path)

    @staticmethod
    def _run_container(
        command: list[str],
        container_name: str,
        timeout_seconds: int,
        timeout_message: str,
    ) -> TestExecutionResult:
        """Run a Docker command and consistently capture output and timeouts."""
        return DockerProcessExecutor.execute(
            command,
            container_name,
            timeout_seconds,
            timeout_message,
            process_runner=subprocess.run,
            maximum_output_characters=MAX_CAPTURED_OUTPUT_CHARACTERS,
        )

    @staticmethod
    def _docker_command(workspace_path: Path, container_name: str) -> list[str]:
        return DockerCommandBuilder.build_pasted_code_command(
            workspace_path,
            container_name,
            runner_image=RUNNER_IMAGE,
        )

    @staticmethod
    def _repository_docker_command(
        workspace_path: Path,
        container_name: str,
        command: list[str],
        *,
        allow_network: bool,
        environment: dict[str, str] | None = None,
        workspace_read_only: bool = False,
    ) -> list[str]:
        """Build a resource-bounded command for a repository workspace."""
        return DockerCommandBuilder.build_repository_command(
            workspace_path,
            container_name,
            command,
            allow_network=allow_network,
            environment=environment,
            workspace_read_only=workspace_read_only,
            runner_image=RUNNER_IMAGE,
            tox_directory=REPOSITORY_TOX_DIRECTORY,
        )

    def _dependency_install_commands(
        self, workspace_path: Path
    ) -> list[tuple[str, list[str]]]:
        """Choose fixed install commands from supported root dependency declarations."""
        return self.dependency_planner.build_install_commands(workspace_path)

    @staticmethod
    def _detect_project_tool(workspace_path: Path) -> str | None:
        """Recognize managers that need their own dependency installation command."""
        return RepositoryDependencyPlanner.detect_project_tool(workspace_path)

    @staticmethod
    def _format_dependency_step(label: str, result: TestExecutionResult) -> str:
        """Label dependency output without exposing shell-built commands."""
        output = result.output
        if output and not output.endswith("\n"):
            output += "\n"
        return f"[{label}]\n{output}"

    @staticmethod
    def _limit_output(output: str) -> str:
        """Bound returned container output while retaining its beginning and summary."""
        return DockerProcessExecutor.limit_output(
            output, MAX_CAPTURED_OUTPUT_CHARACTERS
        )

    @staticmethod
    def _remove_container(container_name: str) -> None:
        DockerProcessExecutor.remove_container(
            container_name,
            process_runner=subprocess.run,
        )

    @staticmethod
    def _write_file(path: Path, content: str) -> None:
        path.write_text(content)
        os.chmod(path, 0o644)
