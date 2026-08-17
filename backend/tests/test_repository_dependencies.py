"""Regression tests for the repository dependency-planning boundary."""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from services.docker_runner import DockerTestRunner
from services.repository_dependencies import RepositoryDependencyPlanner


class DockerRunnerDependencyDelegationTests(unittest.TestCase):
    """Protect DockerTestRunner's existing dependency-planning method."""

    def test_install_command_selection_delegates_to_dependency_planner(self) -> None:
        planner = Mock()
        commands = [("Install dependencies", ["python", "-m", "pip"])]
        planner.build_install_commands.return_value = commands
        runner = DockerTestRunner(dependency_planner=planner)
        workspace_path = Path("repository-workspace")

        result = runner._dependency_install_commands(workspace_path)

        planner.build_install_commands.assert_called_once_with(workspace_path)
        self.assertIs(result, commands)


class RepositoryDependencyPlannerTests(unittest.TestCase):
    """Protect existing manager detection and trusted command selection."""

    def test_lock_files_preserve_project_manager_priority(self) -> None:
        cases = (
            ("Pipfile", "pipenv"),
            ("poetry.lock", "poetry"),
            ("pdm.lock", "pdm"),
        )

        for filename, expected_tool in cases:
            with self.subTest(filename=filename):
                with tempfile.TemporaryDirectory() as workspace:
                    workspace_path = Path(workspace)
                    (workspace_path / filename).write_text("", encoding="utf-8")

                    detected_tool = RepositoryDependencyPlanner.detect_project_tool(
                        workspace_path
                    )

                self.assertEqual(detected_tool, expected_tool)

    def test_pipenv_lock_preserves_sync_command(self) -> None:
        planner = RepositoryDependencyPlanner()

        with tempfile.TemporaryDirectory() as workspace:
            workspace_path = Path(workspace)
            (workspace_path / "Pipfile").write_text("", encoding="utf-8")
            (workspace_path / "Pipfile.lock").write_text("{}", encoding="utf-8")

            commands = planner.build_install_commands(workspace_path)

        self.assertEqual(
            commands[1],
            (
                "Install dependencies with pipenv",
                [
                    ".verix-venv/bin/python",
                    "-m",
                    "pipenv",
                    "sync",
                    "--dev",
                ],
            ),
        )
