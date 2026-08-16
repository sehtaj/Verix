"""Regression tests for Docker process lifecycle handling."""

from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import Mock


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from services.docker_executor import DockerProcessExecutor


class DockerProcessExecutorTests(unittest.TestCase):
    """Protect output, timeout, and cleanup behavior after extraction."""

    def test_execute_combines_standard_output_and_error(self) -> None:
        process_runner = Mock(
            return_value=subprocess.CompletedProcess(
                args=["docker", "run"],
                returncode=1,
                stdout="test output\n",
                stderr="test error\n",
            )
        )

        result = DockerProcessExecutor.execute(
            ["docker", "run"],
            "verix-test-container",
            10,
            "timed out",
            process_runner=process_runner,
            maximum_output_characters=50_000,
        )

        self.assertEqual(result.return_code, 1)
        self.assertEqual(result.output, "test output\ntest error\n")
        self.assertFalse(result.timed_out)

    def test_timeout_removes_container_and_returns_partial_output(self) -> None:
        timeout = subprocess.TimeoutExpired(
            cmd=["docker", "run"],
            timeout=10,
            output="partial output\n",
            stderr="partial error\n",
        )
        process_runner = Mock(
            side_effect=[
                timeout,
                subprocess.CompletedProcess(
                    args=["docker", "rm"], returncode=0, stdout="", stderr=""
                ),
            ]
        )

        result = DockerProcessExecutor.execute(
            ["docker", "run"],
            "verix-test-container",
            10,
            "Test execution timed out.",
            process_runner=process_runner,
            maximum_output_characters=50_000,
        )

        self.assertIsNone(result.return_code)
        self.assertTrue(result.timed_out)
        self.assertEqual(
            result.output,
            "partial output\npartial error\nTest execution timed out.",
        )
        self.assertEqual(
            process_runner.call_args_list[1].args[0],
            ["docker", "rm", "--force", "verix-test-container"],
        )

    def test_limit_output_preserves_both_ends(self) -> None:
        output = "a" * 100 + "z" * 100

        limited = DockerProcessExecutor.limit_output(output, 100)

        self.assertEqual(len(limited), 100)
        self.assertTrue(limited.startswith("a"))
        self.assertTrue(limited.endswith("z"))
        self.assertIn("container output truncated by Verix", limited)
