"""Regression tests for deterministic Docker command construction."""

from pathlib import Path
import sys
import unittest


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from services.docker_commands import DockerCommandBuilder


class DockerCommandBuilderTests(unittest.TestCase):
    """Protect pasted-code isolation flags after command extraction."""

    def test_pasted_code_command_preserves_security_limits(self) -> None:
        workspace_path = Path("/tmp/verix-pasted-code")

        command = DockerCommandBuilder.build_pasted_code_command(
            workspace_path,
            "verix-test-container",
            runner_image="verix-test-runner:dev",
        )

        self.assertEqual(command[command.index("--network") + 1], "none")
        self.assertIn("--read-only", command)
        self.assertEqual(command[command.index("--cap-drop") + 1], "ALL")
        self.assertEqual(
            command[command.index("--security-opt") + 1],
            "no-new-privileges:true",
        )
        self.assertEqual(command[command.index("--pids-limit") + 1], "64")
        self.assertEqual(command[command.index("--memory") + 1], "256m")
        self.assertIn(
            "type=bind,source=/tmp/verix-pasted-code,target=/workspace,readonly",
            command,
        )
        self.assertEqual(
            command[-3:],
            ["verix-test-runner:dev", "-p", "no:cacheprovider"],
        )
