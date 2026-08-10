"""Run generated Python tests in an isolated Docker container."""

from dataclasses import dataclass
from pathlib import Path
import os
import subprocess
import tempfile
from uuid import uuid4


RUNNER_IMAGE = "verix-test-runner:dev"
DEFAULT_TIMEOUT_SECONDS = 10


@dataclass
class TestExecutionResult:
    """The captured result of a pytest container run."""

    return_code: int | None
    output: str
    timed_out: bool = False


class DockerTestRunner:
    """Execute Python code and tests without running them on the host."""

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

            try:
                result = subprocess.run(
                    self._docker_command(workspace_path, container_name),
                    capture_output=True,
                    check=False,
                    text=True,
                    timeout=self.timeout_seconds,
                )
            except subprocess.TimeoutExpired as error:
                self._remove_container(container_name)
                output = f"{error.stdout or ''}{error.stderr or ''}Test execution timed out."
                return TestExecutionResult(
                    return_code=None,
                    output=output,
                    timed_out=True,
                )

        return TestExecutionResult(
            return_code=result.returncode,
            output=f"{result.stdout}{result.stderr}",
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
