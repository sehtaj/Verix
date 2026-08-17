"""Select trusted dependency-installation commands from repository evidence."""

from pathlib import Path


REPOSITORY_VENV_DIRECTORY = ".verix-venv"
REQUIREMENTS_FILENAMES = (
    "requirements.txt",
    "requirements-dev.txt",
    "requirements-test.txt",
    "dev-requirements.txt",
    "test-requirements.txt",
)
PROJECT_CONFIGURATION_READ_LIMIT = 128 * 1024


class RepositoryDependencyPlanner:
    """Build fixed installation commands without executing repository code."""

    def build_install_commands(
        self, workspace_path: Path
    ) -> list[tuple[str, list[str]]]:
        """Choose commands from supported root dependency declarations."""
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
        project_tool = self.detect_project_tool(workspace_path)

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
    def detect_project_tool(workspace_path: Path) -> str | None:
        """Recognize managers that need their own installation command."""
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
