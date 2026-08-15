"""Run generated and repository Python commands in isolated Docker containers."""

import ast
from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import tempfile
from typing import Iterator
from uuid import uuid4


RUNNER_IMAGE = "verix-test-runner:dev"
DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_REPOSITORY_TIMEOUT_SECONDS = 60
DEPENDENCY_INSTALL_TIMEOUT_SECONDS = 180
REPOSITORY_TEST_TIMEOUT_SECONDS = 60
MAX_CAPTURED_OUTPUT_CHARACTERS = 50_000
REPOSITORY_VENV_DIRECTORY = ".verix-venv"
REPOSITORY_TOX_DIRECTORY = ".verix-tox"
GENERATED_TEST_DIRECTORY = ".verix-generated-tests"
GENERATED_TEST_FILENAME = "test_verix_generated.py"
MAX_GENERATED_TEST_BYTES = 128 * 1024
REQUIREMENTS_FILENAMES = (
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-test.txt",
    "dev-requirements.txt",
    "test-requirements.txt",
)
PROJECT_CONFIGURATION_READ_LIMIT = 128 * 1024
TOX_ENVIRONMENT_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
TOX_PYTHON_ENVIRONMENT_PATTERN = re.compile(r"^(?:py(?:\d|$)|pypy\d)")


@dataclass
class TestExecutionResult:
    """The captured result of an isolated container command."""

    return_code: int | None
    output: str
    timed_out: bool = False
    skipped: bool = False


@dataclass
class RepositoryTestResults:
    """Keep original repository results separate from Verix-generated results."""

    existing: TestExecutionResult
    generated: TestExecutionResult


class GeneratedTestsValidationError(ValueError):
    """Raised when LLM output cannot safely become a Python test module."""


class DockerTestRunner:
    """Execute Python commands without running untrusted code on the host."""

    def __init__(self, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> None:
        self.timeout_seconds = timeout_seconds

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

    @contextmanager
    def repository_workspace(self, repository_path: Path) -> Iterator[Path]:
        """Yield an isolated writable copy of a prepared repository, then remove it."""
        if not repository_path.is_dir():
            raise ValueError("Prepared repository directory does not exist.")

        with tempfile.TemporaryDirectory(
            prefix="verix-repository-runner-"
        ) as workspace:
            workspace_path = Path(workspace) / "repository"
            shutil.copytree(repository_path, workspace_path, symlinks=True)
            self._make_workspace_writable(workspace_path)
            yield workspace_path

    def write_repository_generated_tests(
        self,
        workspace_path: Path,
        target_path: str,
        generated_tests: str,
    ) -> Path:
        """Safely add one generated pytest module to a disposable repository copy."""
        if not workspace_path.is_dir():
            raise ValueError("Repository workspace directory does not exist.")

        relative_target = PurePosixPath(target_path)
        if (
            not target_path
            or "\\" in target_path
            or relative_target.is_absolute()
            or ".." in relative_target.parts
            or relative_target.suffix != ".py"
        ):
            raise ValueError("Repository generation target path is invalid.")

        target_file = workspace_path.joinpath(*relative_target.parts)
        current_path = workspace_path
        for part in relative_target.parts:
            current_path /= part
            if current_path.is_symlink():
                raise ValueError("Repository generation target cannot use symlinks.")
        if not target_file.is_file():
            raise ValueError("Repository generation target does not exist.")

        self.validate_generated_tests(generated_tests)

        generated_directory = workspace_path / GENERATED_TEST_DIRECTORY
        if generated_directory.exists() or generated_directory.is_symlink():
            raise ValueError(
                f"Repository contains the reserved {GENERATED_TEST_DIRECTORY} path."
            )

        generated_directory.mkdir(mode=0o755)
        generated_test_path = generated_directory / GENERATED_TEST_FILENAME
        with generated_test_path.open("x", encoding="utf-8") as generated_file:
            generated_file.write(generated_tests)
        os.chmod(generated_test_path, 0o644)
        return generated_test_path

    @staticmethod
    def validate_generated_tests(generated_tests: str) -> None:
        """Reject unusable generated code before repository setup or execution."""
        if not isinstance(generated_tests, str) or not generated_tests.strip():
            raise GeneratedTestsValidationError("Generated tests cannot be empty.")
        if "\x00" in generated_tests:
            raise GeneratedTestsValidationError(
                "Generated tests contain invalid characters."
            )
        if len(generated_tests.encode("utf-8")) > MAX_GENERATED_TEST_BYTES:
            raise GeneratedTestsValidationError(
                "Generated tests exceed the allowed size."
            )
        try:
            ast.parse(generated_tests)
        except SyntaxError:
            raise GeneratedTestsValidationError(
                "Generated tests are not valid Python."
            ) from None

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
        generated_test_argument = (
            f"/workspace/{GENERATED_TEST_DIRECTORY}/{GENERATED_TEST_FILENAME}"
        )
        if selected_runner == "tox":
            list_result = self.run_repository_command(
                workspace_path,
                [
                    python_command,
                    "-m",
                    "tox",
                    "list",
                    "--workdir",
                    "/tox-work",
                    "--no-desc",
                    "-d",
                ],
                allow_network=False,
                environment=environment,
                workspace_read_only=True,
                timeout_seconds=REPOSITORY_TEST_TIMEOUT_SECONDS,
            )
            if list_result.return_code != 0 or list_result.timed_out:
                return list_result

            tox_environments = [
                line.strip()
                for line in list_result.output.splitlines()
                if TOX_ENVIRONMENT_NAME_PATTERN.fullmatch(line.strip())
            ]
            if not tox_environments:
                return TestExecutionResult(
                    return_code=2,
                    output="Tox did not report a default test environment.",
                )
            tox_environment = next(
                (
                    name
                    for name in tox_environments
                    if TOX_PYTHON_ENVIRONMENT_PATTERN.match(name.lower())
                ),
                tox_environments[0],
            )
            command = [
                python_command,
                "-m",
                "tox",
                "exec",
                "--workdir",
                "/tox-work",
                "--skip-env-install",
                "-e",
                tox_environment,
                "--",
                "python",
                "-m",
                "pytest",
                "-p",
                "no:cacheprovider",
                generated_test_argument,
            ]
        else:
            command = [
                python_command,
                "-m",
                "pytest",
                "-p",
                "no:cacheprovider",
                generated_test_argument,
            ]

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

        command = [python_command, "-m", selected_runner]
        if selected_runner == "pytest":
            command.extend(["-p", "no:cacheprovider"])
        else:
            command.extend(
                ["run", "--workdir", "/tox-work", "--skip-env-install"]
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
        if not workspace_path.is_dir():
            raise ValueError("Repository workspace directory does not exist.")
        return "tox" if (workspace_path / "tox.ini").is_file() else "pytest"

    @staticmethod
    def _repository_python_environment(
        workspace_path: Path,
    ) -> tuple[str, dict[str, str]]:
        """Use the prepared repository environment when one is available."""
        virtual_environment = workspace_path / REPOSITORY_VENV_DIRECTORY
        if not virtual_environment.is_dir():
            return "python", {}
        return (
            f"{REPOSITORY_VENV_DIRECTORY}/bin/python",
            {"VIRTUAL_ENV": f"/workspace/{REPOSITORY_VENV_DIRECTORY}"},
        )

    @staticmethod
    def _run_container(
        command: list[str],
        container_name: str,
        timeout_seconds: int,
        timeout_message: str,
    ) -> TestExecutionResult:
        """Run a Docker command and consistently capture output and timeouts."""
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                check=False,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            DockerTestRunner._remove_container(container_name)
            output = f"{error.stdout or ''}{error.stderr or ''}{timeout_message}"
            return TestExecutionResult(
                return_code=None,
                output=DockerTestRunner._limit_output(output),
                timed_out=True,
            )
        except OSError:
            raise RuntimeError("Docker could not start the test container.") from None

        if result.returncode == 125:
            raise RuntimeError("Docker could not start the test container.")

        return TestExecutionResult(
            return_code=result.returncode,
            output=DockerTestRunner._limit_output(
                f"{result.stdout}{result.stderr}"
            ),
        )

    @staticmethod
    def _docker_command(workspace_path: Path, container_name: str) -> list[str]:
        return [
            "docker",
            "run",
            "--rm",
            "--name",
            container_name,
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges:true",
            "--pids-limit",
            "64",
            "--memory",
            "256m",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=64m",
            "--mount",
            f"type=bind,source={workspace_path},target=/workspace,readonly",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            RUNNER_IMAGE,
            "-p",
            "no:cacheprovider",
        ]

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
        environment_options = [
            option
            for name, value in sorted((environment or {}).items())
            for option in ("--env", f"{name}={value}")
        ]
        workspace_mount = (
            f"type=bind,source={workspace_path.resolve()},target=/workspace"
            + (",readonly" if workspace_read_only else "")
        )
        tox_work_path = workspace_path / REPOSITORY_TOX_DIRECTORY
        if tox_work_path.is_symlink() or (
            tox_work_path.exists() and not tox_work_path.is_dir()
        ):
            raise ValueError(
                f"Repository contains an invalid {REPOSITORY_TOX_DIRECTORY} path."
            )
        tox_work_path.mkdir(exist_ok=True)
        os.chmod(tox_work_path, 0o777)

        return [
            "docker",
            "run",
            "--rm",
            "--name",
            container_name,
            "--network",
            "bridge" if allow_network else "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges:true",
            "--pids-limit",
            "128",
            "--memory",
            "512m",
            "--cpus",
            "1",
            "--tmpfs",
            "/tmp:rw,noexec,nosuid,size=128m",
            "--tmpfs",
            "/home/runner:rw,nosuid,size=64m,uid=1000,gid=1000,mode=700",
            "--mount",
            workspace_mount,
            "--mount",
            f"type=bind,source={tox_work_path.resolve()},target=/tox-work",
            "--env",
            "PYTHONDONTWRITEBYTECODE=1",
            *environment_options,
            "--entrypoint",
            command[0],
            RUNNER_IMAGE,
            *command[1:],
        ]

    @staticmethod
    def _dependency_install_commands(
        workspace_path: Path,
    ) -> list[tuple[str, list[str]]]:
        """Choose fixed install commands from supported root dependency declarations."""
        virtual_python = f"{REPOSITORY_VENV_DIRECTORY}/bin/python"
        pip_command = [
            virtual_python,
            "-m",
            "pip",
            "install",
            "--no-input",
            "--disable-pip-version-check",
            "--no-cache-dir",
        ]
        project_tool = DockerTestRunner._detect_project_tool(workspace_path)

        commands: list[tuple[str, list[str]]]
        if project_tool in {"poetry", "pdm", "pipenv"}:
            manager_command = {
                "poetry": [
                    f"{REPOSITORY_VENV_DIRECTORY}/bin/poetry",
                    "install",
                    "--no-interaction",
                ],
                "pdm": [
                    f"{REPOSITORY_VENV_DIRECTORY}/bin/pdm",
                    "install",
                ],
                "pipenv": [
                    virtual_python,
                    "-m",
                    "pipenv",
                    "sync" if (workspace_path / "Pipfile.lock").is_file() else "install",
                    "--dev",
                ],
            }[project_tool]
            commands = [
                (f"Install {project_tool} installer", [*pip_command, project_tool]),
                (f"Install dependencies with {project_tool}", manager_command),
            ]
        else:
            commands = [
                (
                    f"Install dependencies from {filename}",
                    [*pip_command, "-r", filename],
                )
                for filename in REQUIREMENTS_FILENAMES
                if (workspace_path / filename).is_file()
            ]

            if (workspace_path / "pyproject.toml").is_file() or (
                workspace_path / "setup.py"
            ).is_file():
                commands.append(("Install repository project", [*pip_command, "."]))

        if (workspace_path / "tox.ini").is_file():
            commands.append(
                (
                    "Prepare tox environments",
                    [
                        virtual_python,
                        "-m",
                        "tox",
                        "run",
                        "--workdir",
                        "/tox-work",
                        "--notest",
                    ],
                )
            )

        return commands

    @staticmethod
    def _detect_project_tool(workspace_path: Path) -> str | None:
        """Recognize managers that need their own dependency installation command."""
        if (workspace_path / "Pipfile").is_file():
            return "pipenv"
        if (workspace_path / "poetry.lock").is_file():
            return "poetry"
        if (workspace_path / "pdm.lock").is_file():
            return "pdm"

        pyproject_path = workspace_path / "pyproject.toml"
        if not pyproject_path.is_file():
            return None

        try:
            with pyproject_path.open(errors="ignore") as pyproject:
                content = pyproject.read(PROJECT_CONFIGURATION_READ_LIMIT).lower()
        except OSError:
            raise RuntimeError("Repository configuration could not be read.") from None

        if "[tool.poetry]" in content or "poetry-core" in content:
            return "poetry"
        if "[tool.pdm]" in content:
            return "pdm"

        return None

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
        if len(output) <= MAX_CAPTURED_OUTPUT_CHARACTERS:
            return output

        marker = "\n... container output truncated by Verix ...\n"
        retained_characters = MAX_CAPTURED_OUTPUT_CHARACTERS - len(marker)
        beginning_characters = retained_characters // 2
        ending_characters = retained_characters - beginning_characters
        return (
            output[:beginning_characters]
            + marker
            + output[-ending_characters:]
        )

    @staticmethod
    def _remove_container(container_name: str) -> None:
        subprocess.run(
            ["docker", "rm", "--force", container_name],
            capture_output=True,
            check=False,
            text=True,
        )

    @staticmethod
    def _write_file(path: Path, content: str) -> None:
        path.write_text(content)
        os.chmod(path, 0o644)

    @staticmethod
    def _make_workspace_writable(workspace_path: Path) -> None:
        """Allow the non-root container user to modify only the temporary copy."""
        os.chmod(workspace_path, 0o777)
        for path in workspace_path.rglob("*"):
            if path.is_symlink():
                continue
            if path.is_dir():
                os.chmod(path, 0o777)
                continue

            executable = bool(path.stat().st_mode & 0o111)
            os.chmod(path, 0o777 if executable else 0o666)
