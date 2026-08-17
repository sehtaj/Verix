"""Launch Docker commands and capture their bounded process results."""

import subprocess
from typing import Callable

from models.execution import TestExecutionResult


ProcessRunner = Callable[..., subprocess.CompletedProcess[str]]


class DockerProcessExecutor:
    """Manage one Docker process lifecycle without building its command."""

    @classmethod
    def execute(
        cls,
        command: list[str],
        container_name: str,
        timeout_seconds: int,
        timeout_message: str,
        *,
        process_runner: ProcessRunner,
        maximum_output_characters: int,
    ) -> TestExecutionResult:
        """Run a Docker command and consistently capture output and timeouts."""
        try:
            result = process_runner(
                command,
                capture_output=True,
                check=False,
                text=True,
                timeout=timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            cls.remove_container(container_name, process_runner=process_runner)
            output = f"{error.stdout or ''}{error.stderr or ''}{timeout_message}"
            return TestExecutionResult(
                return_code=None,
                output=cls.limit_output(output, maximum_output_characters),
                timed_out=True,
            )
        except OSError:
            raise RuntimeError("Docker could not start the test container.") from None

        if result.returncode == 125:
            raise RuntimeError("Docker could not start the test container.")

        return TestExecutionResult(
            return_code=result.returncode,
            output=cls.limit_output(
                f"{result.stdout}{result.stderr}", maximum_output_characters
            ),
        )

    @staticmethod
    def limit_output(output: str, maximum_characters: int) -> str:
        """Bound container output while retaining its beginning and summary."""
        if len(output) <= maximum_characters:
            return output

        marker = "\n... container output truncated by Verix ...\n"
        retained_characters = maximum_characters - len(marker)
        beginning_characters = retained_characters // 2
        ending_characters = retained_characters - beginning_characters
        return (
            output[:beginning_characters]
            + marker
            + output[-ending_characters:]
        )

    @staticmethod
    def remove_container(
        container_name: str, *, process_runner: ProcessRunner
    ) -> None:
        """Force-remove a named container after its client-side timeout."""
        process_runner(
            ["docker", "rm", "--force", container_name],
            capture_output=True,
            check=False,
            text=True,
        )
