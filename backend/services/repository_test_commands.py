"""Plan trusted pytest and tox commands for prepared repositories."""

from pathlib import Path
import re

from services.repository_dependencies import REPOSITORY_VENV_DIRECTORY
from services.repository_workspace import (
    GENERATED_TEST_DIRECTORY,
    GENERATED_TEST_FILENAME,
)


TOX_ENVIRONMENT_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
TOX_PYTHON_ENVIRONMENT_PATTERN = re.compile(r"^(?:py(?:\d|$)|pypy\d)")


class RepositoryTestCommandPlanner:
    """Build test commands without executing them or repository code."""

    @staticmethod
    def select_test_runner(workspace_path: Path) -> str:
        """Select tox when configured and otherwise use pytest discovery."""
        if not workspace_path.is_dir():
            raise ValueError("Repository workspace directory does not exist.")
        return "tox" if (workspace_path / "tox.ini").is_file() else "pytest"

    @staticmethod
    def python_environment(
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
    def build_existing_test_command(
        python_command: str, test_runner: str
    ) -> list[str]:
        """Build the complete existing-suite command."""
        command = [python_command, "-m", test_runner]
        if test_runner == "pytest":
            command.extend(["-p", "no:cacheprovider"])
        else:
            command.extend(
                ["run", "--workdir", "/tox-work", "--skip-env-install"]
            )
        return command

    @staticmethod
    def build_tox_environment_list_command(python_command: str) -> list[str]:
        """Build the command that reports tox's default environments."""
        return [
            python_command,
            "-m",
            "tox",
            "list",
            "--workdir",
            "/tox-work",
            "--no-desc",
            "-d",
        ]

    @staticmethod
    def select_tox_environment(output: str) -> str | None:
        """Prefer one safe Python-style tox environment from reported defaults."""
        tox_environments = [
            line.strip()
            for line in output.splitlines()
            if TOX_ENVIRONMENT_NAME_PATTERN.fullmatch(line.strip())
        ]
        if not tox_environments:
            return None
        return next(
            (
                name
                for name in tox_environments
                if TOX_PYTHON_ENVIRONMENT_PATTERN.match(name.lower())
            ),
            tox_environments[0],
        )

    @staticmethod
    def build_generated_test_command(
        python_command: str,
        test_runner: str,
        *,
        tox_environment: str | None = None,
    ) -> list[str]:
        """Build the focused command for Verix's generated pytest module."""
        generated_test_argument = (
            f"/workspace/{GENERATED_TEST_DIRECTORY}/{GENERATED_TEST_FILENAME}"
        )
        if test_runner == "tox":
            if tox_environment is None:
                raise ValueError("Tox environment is required for generated tests.")
            return [
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
        return [
            python_command,
            "-m",
            "pytest",
            "-p",
            "no:cacheprovider",
            generated_test_argument,
        ]
