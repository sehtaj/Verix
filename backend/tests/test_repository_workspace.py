"""Regression tests for the repository workspace boundary."""

from pathlib import Path
import sys
import unittest
from unittest.mock import Mock


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from services.docker_runner import DockerTestRunner, MAX_GENERATED_TEST_BYTES


class DockerRunnerWorkspaceDelegationTests(unittest.TestCase):
    """Protect DockerTestRunner's existing workspace-facing methods."""

    def test_repository_workspace_delegates_to_workspace_manager(self) -> None:
        manager = Mock()
        context_manager = Mock()
        manager.create.return_value = context_manager
        runner = DockerTestRunner(workspace_manager=manager)
        repository_path = Path("prepared-repository")

        result = runner.repository_workspace(repository_path)

        manager.create.assert_called_once_with(repository_path)
        self.assertIs(result, context_manager)

    def test_generated_test_writing_preserves_configured_size_limit(self) -> None:
        manager = Mock()
        generated_path = Path("generated-test.py")
        manager.write_generated_tests.return_value = generated_path
        runner = DockerTestRunner(workspace_manager=manager)
        workspace_path = Path("repository-workspace")

        result = runner.write_repository_generated_tests(
            workspace_path,
            "src/sample.py",
            "def test_sample():\n    assert True\n",
        )

        manager.write_generated_tests.assert_called_once_with(
            workspace_path,
            "src/sample.py",
            "def test_sample():\n    assert True\n",
            maximum_bytes=MAX_GENERATED_TEST_BYTES,
        )
        self.assertIs(result, generated_path)
