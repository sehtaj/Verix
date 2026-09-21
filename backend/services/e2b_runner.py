"""Run Python repositories in short-lived E2B cloud sandboxes."""

from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from io import BytesIO
import os
from pathlib import Path
import shlex
import tarfile
from typing import Any, Callable, Iterator

from e2b import Sandbox
from e2b.exceptions import SandboxException, TimeoutException
from e2b.sandbox.commands.command_handle import CommandExitException

from models.execution import TestExecutionResult
from services.docker_runner import (
    DEFAULT_TIMEOUT_SECONDS,
    DockerTestRunner,
)
from services.repository_dependencies import REPOSITORY_VENV_DIRECTORY


DEFAULT_E2B_TEMPLATE = "verix-python-runner"
DEFAULT_E2B_SANDBOX_TIMEOUT_SECONDS = 600
REMOTE_WORKSPACE = "/workspace"
REMOTE_ARCHIVE = "/tmp/verix-workspace.tar.gz"


@dataclass
class _E2BWorkspace:
    sandbox: Any
    network_enabled: bool = True
    installing_dependencies: bool = False
    has_virtual_environment: bool = False
    workspace_read_only: bool = False


class E2BTestRunner(DockerTestRunner):
    """Reuse Verix's trusted test planning while replacing Docker transport."""

    def __init__(
        self,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        *,
        template: str = DEFAULT_E2B_TEMPLATE,
        sandbox_timeout_seconds: int = DEFAULT_E2B_SANDBOX_TIMEOUT_SECONDS,
        sandbox_factory: Callable[..., Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(timeout_seconds=timeout_seconds, **kwargs)
        if not template.strip():
            raise ValueError("E2B sandbox template cannot be empty.")
        if sandbox_timeout_seconds <= 0 or sandbox_timeout_seconds > 3600:
            raise ValueError("E2B sandbox timeout must be between 1 and 3600 seconds.")
        self.template = template.strip()
        self.sandbox_timeout_seconds = sandbox_timeout_seconds
        self.sandbox_factory = sandbox_factory or Sandbox.create
        self._workspaces: dict[Path, _E2BWorkspace] = {}

    def run_tests(self, code: str, tests: str) -> TestExecutionResult:
        """Run pasted code in one disposable internet-disabled cloud sandbox."""
        with self.temporary_workspaces.create("pasted-code-") as workspace_path:
            self._write_file(workspace_path / "main.py", code)
            self._write_file(workspace_path / "test_generated.py", tests)
            with self.execution_workspace(workspace_path):
                return self.run_repository_command(
                    workspace_path,
                    ["python", "-m", "pytest", "-p", "no:cacheprovider"],
                    allow_network=False,
                    workspace_read_only=True,
                    timeout_seconds=self.timeout_seconds,
                )

    @contextmanager
    def repository_workspace(self, repository_path: Path) -> Iterator[Path]:
        """Copy a prepared repository and bind it to one E2B sandbox."""
        with self.workspace_manager.create(repository_path) as workspace_path:
            with self.execution_workspace(workspace_path):
                yield workspace_path

    @contextmanager
    def execution_workspace(self, workspace_path: Path) -> Iterator[Path]:
        """Upload a disposable local workspace and always terminate its sandbox."""
        key = self._workspace_key(workspace_path)
        if key in self._workspaces:
            raise RuntimeError("E2B workspace is already active.")

        try:
            sandbox = self.sandbox_factory(
                self.template,
                timeout=self.sandbox_timeout_seconds,
                allow_internet_access=True,
            )
            state = _E2BWorkspace(sandbox=sandbox)
            self._workspaces[key] = state
            self._upload_workspace(workspace_path, sandbox)
            yield workspace_path
        except (SandboxException, OSError, tarfile.TarError) as error:
            raise RuntimeError("E2B could not prepare the isolated workspace.") from error
        finally:
            state = self._workspaces.pop(key, None)
            if state is not None:
                try:
                    state.sandbox.kill()
                except Exception:
                    pass

    def install_repository_dependencies(
        self, workspace_path: Path
    ) -> TestExecutionResult:
        """Permit network only during the existing bounded installation phase."""
        state = self._state(workspace_path)
        if not state.network_enabled:
            raise RuntimeError("E2B workspace network cannot be re-enabled.")
        state.installing_dependencies = True
        try:
            result = super().install_repository_dependencies(workspace_path)
        finally:
            state.installing_dependencies = False
        state.has_virtual_environment = not result.skipped and result.return_code == 0
        return result

    def write_repository_generated_tests(
        self,
        workspace_path: Path,
        target_path: str,
        generated_tests: str,
    ) -> Path:
        """Validate locally, then copy the exact generated module into E2B."""
        generated_path = super().write_repository_generated_tests(
            workspace_path,
            target_path,
            generated_tests,
        )
        relative_path = generated_path.relative_to(workspace_path).as_posix()
        try:
            self._state(workspace_path).sandbox.files.write(
                f"{REMOTE_WORKSPACE}/{relative_path}",
                generated_tests,
                user="root",
            )
            self._state(workspace_path).sandbox.commands.run(
                "chmod -R a-w /workspace/.verix-generated-tests",
                user="root",
                timeout=10,
            )
        except SandboxException as error:
            raise RuntimeError("E2B could not upload generated tests.") from error
        return generated_path

    def run_repository_command(
        self,
        workspace_path: Path,
        command: list[str],
        *,
        allow_network: bool = False,
        environment: dict[str, str] | None = None,
        workspace_read_only: bool = False,
        timeout_seconds: int = 60,
    ) -> TestExecutionResult:
        """Execute one backend-selected argv list in the active E2B sandbox."""
        self._validate_command(command, environment, timeout_seconds)
        state = self._state(workspace_path)
        network_required = allow_network or state.installing_dependencies
        if network_required and not state.network_enabled:
            raise RuntimeError("E2B workspace network cannot be re-enabled.")
        if not network_required and state.network_enabled:
            try:
                state.sandbox.update_network(
                    {"deny_out": ["0.0.0.0/0", "::/0"]}
                )
            except SandboxException as error:
                raise RuntimeError("E2B could not disable sandbox network access.") from error
            state.network_enabled = False

        if workspace_read_only and not state.workspace_read_only:
            try:
                state.sandbox.commands.run(
                    "chmod -R a-w /workspace",
                    user="root",
                    timeout=30,
                )
            except (CommandExitException, SandboxException) as error:
                raise RuntimeError("E2B could not lock the repository workspace.") from error
            state.workspace_read_only = True

        try:
            result = state.sandbox.commands.run(
                shlex.join(command),
                envs=environment or {},
                user="runner",
                cwd=REMOTE_WORKSPACE,
                timeout=timeout_seconds,
            )
        except CommandExitException as result:
            pass
        except TimeoutException:
            return TestExecutionResult(
                return_code=None,
                output="Repository command timed out.",
                timed_out=True,
            )
        except SandboxException as error:
            raise RuntimeError("E2B could not execute the repository command.") from error

        output = self._limit_output(self._combined_output(result.stdout, result.stderr))
        return TestExecutionResult(return_code=result.exit_code, output=output)

    def _repository_python_environment(
        self, workspace_path: Path
    ) -> tuple[str, dict[str, str]]:
        state = self._state(workspace_path)
        if not state.has_virtual_environment:
            return "python", {}
        return (
            f"{REPOSITORY_VENV_DIRECTORY}/bin/python",
            {"VIRTUAL_ENV": f"{REMOTE_WORKSPACE}/{REPOSITORY_VENV_DIRECTORY}"},
        )

    @staticmethod
    def _validate_command(
        command: list[str],
        environment: dict[str, str] | None,
        timeout_seconds: int,
    ) -> None:
        if not command or any(not argument or "\x00" in argument for argument in command):
            raise ValueError("Repository command cannot be empty.")
        if any(
            not name.isidentifier()
            or name.upper() != name
            or "\x00" in value
            for name, value in (environment or {}).items()
        ):
            raise ValueError("Repository command environment is invalid.")
        if timeout_seconds <= 0:
            raise ValueError("Repository command timeout must be greater than zero.")

    def _state(self, workspace_path: Path) -> _E2BWorkspace:
        state = self._workspaces.get(self._workspace_key(workspace_path))
        if state is None:
            raise RuntimeError("E2B execution requires an active workspace.")
        return state

    @staticmethod
    def _workspace_key(workspace_path: Path) -> Path:
        if not workspace_path.is_dir():
            raise ValueError("Repository workspace directory does not exist.")
        return workspace_path.resolve()

    def _upload_workspace(self, workspace_path: Path, sandbox: Any) -> None:
        archive = BytesIO()
        with tarfile.open(fileobj=archive, mode="w:gz") as tar:
            tar.add(workspace_path, arcname=".", recursive=True)
        sandbox.files.write(REMOTE_ARCHIVE, archive.getvalue())
        try:
            sandbox.commands.run(
                "mkdir -p /workspace /tox-work && "
                "tar -xzf /tmp/verix-workspace.tar.gz -C /workspace && "
                "chown -R runner:runner /workspace /tox-work && "
                "rm /tmp/verix-workspace.tar.gz",
                user="root",
                timeout=60,
            )
        except CommandExitException as error:
            raise RuntimeError("E2B could not unpack the repository workspace.") from error

    @staticmethod
    def _combined_output(stdout: str, stderr: str) -> str:
        if not stderr:
            return stdout
        if stdout and not stdout.endswith("\n"):
            stdout += "\n"
        return f"{stdout}{stderr}"
