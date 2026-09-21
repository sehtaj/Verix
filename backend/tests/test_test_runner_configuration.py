"""Tests for explicit local versus hosted execution selection."""

from pathlib import Path
import os
import sys
import unittest
from unittest.mock import Mock, patch


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from services.test_runner_configuration import configured_test_runner


class TestRunnerConfigurationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.workspaces = Mock()

    def test_defaults_to_docker(self) -> None:
        docker = Mock()
        with patch.dict(os.environ, {}, clear=True):
            result = configured_test_runner(
                self.workspaces,
                docker_factory=docker,
            )

        self.assertIs(result, docker.return_value)
        docker.assert_called_once_with(temporary_workspaces=self.workspaces)

    def test_e2b_requires_an_api_key(self) -> None:
        with patch.dict(
            os.environ,
            {"VERIX_EXECUTION_BACKEND": "e2b"},
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "E2B_API_KEY"):
                configured_test_runner(self.workspaces)

    def test_e2b_uses_the_configured_template(self) -> None:
        e2b = Mock()
        with patch.dict(
            os.environ,
            {
                "VERIX_EXECUTION_BACKEND": "e2b",
                "E2B_API_KEY": "test-only-key",
                "E2B_TEMPLATE": "custom-verix-runner",
            },
            clear=True,
        ):
            result = configured_test_runner(
                self.workspaces,
                e2b_factory=e2b,
            )

        self.assertIs(result, e2b.return_value)
        e2b.assert_called_once_with(
            temporary_workspaces=self.workspaces,
            template="custom-verix-runner",
        )

    def test_rejects_unknown_execution_backend(self) -> None:
        with patch.dict(
            os.environ,
            {"VERIX_EXECUTION_BACKEND": "unsafe-subprocess"},
            clear=True,
        ):
            with self.assertRaisesRegex(RuntimeError, "docker or e2b"):
                configured_test_runner(self.workspaces)
