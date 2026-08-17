"""Pure analysis rules for Python repository structure and test planning."""

from pathlib import PurePosixPath

from models.repository import (
    PythonProjectSetup,
    RepositoryConfigurationFile,
    RepositoryGenerationSelection,
    RepositoryPaths,
    RepositoryTestPlanStep,
    RepositoryTree,
)


MAX_GENERATION_TEST_PATHS = 3
MAX_GENERATION_CONFIGURATION_PATHS = 3
CONFIGURATION_FILENAMES = (
    "pyproject.toml",
    "requirements.txt",
    "setup.cfg",
    "setup.py",
    "Pipfile",
    "tox.ini",
)
GENERATION_CONFIGURATION_PRIORITY = (
    "pyproject.toml",
    "setup.cfg",
    "tox.ini",
    "requirements.txt",
    "setup.py",
    "Pipfile",
)
TEST_DIRECTORY_NAMES = {"test", "tests"}
EXCLUDED_SOURCE_DIRECTORY_NAMES = {
    ".venv",
    "build",
    "dist",
    "docs",
    "env",
    "example",
    "examples",
    "samples",
    "site-packages",
    "venv",
}


class RepositoryAnalyzer:
    """Derive Python project evidence without performing external requests."""

    @classmethod
    def identify_likely_paths(cls, tree: RepositoryTree) -> RepositoryPaths:
        """Identify likely Python paths from an already fetched tree."""
        python_file_paths = [
            entry.path
            for entry in tree.entries
            if entry.type == "blob" and entry.path.endswith(".py")
        ]
        test_paths = [
            path
            for path in python_file_paths
            if cls.is_test_path(path)
            and PurePosixPath(path).name not in {"__init__.py", "__main__.py"}
        ]
        source_paths = [
            path
            for path in python_file_paths
            if not cls.is_test_path(path) and cls.is_source_path(path)
        ]

        return RepositoryPaths(
            source_paths=source_paths,
            test_paths=test_paths,
            is_truncated=tree.is_truncated,
        )

    @classmethod
    def detect_python_project_setup(
        cls, configuration_files: list[RepositoryConfigurationFile]
    ) -> PythonProjectSetup:
        """Recognize Python tooling from already fetched configuration files."""
        contents_by_path = {
            file.path: file.content.lower() for file in configuration_files
        }

        return PythonProjectSetup(
            is_python_project=bool(configuration_files),
            project_tool=cls.detect_project_tool(contents_by_path),
            test_runner=cls.detect_test_runner(contents_by_path),
            configuration_files=[file.path for file in configuration_files],
        )

    @classmethod
    def select_generation_context(
        cls,
        paths: RepositoryPaths,
        configuration_files: list[RepositoryConfigurationFile],
    ) -> RepositoryGenerationSelection:
        """Select one source target and a small, deterministic context set."""
        preferred_targets = [
            path
            for path in paths.source_paths
            if PurePosixPath(path).name not in {"__init__.py", "__main__.py"}
        ]
        target_candidates = preferred_targets or paths.source_paths
        target_path = (
            min(
                target_candidates,
                key=lambda path: (
                    not any(
                        cls.is_direct_test_for_source(test_path, path)
                        for test_path in paths.test_paths
                    ),
                    len(PurePosixPath(path).parts),
                    path.lower(),
                ),
            )
            if target_candidates
            else None
        )

        related_test_paths: list[str] = []
        if target_path is not None:
            related_test_paths = sorted(
                paths.test_paths,
                key=lambda path: (
                    not cls.is_direct_test_for_source(path, target_path),
                    len(PurePosixPath(path).parts),
                    path.lower(),
                ),
            )[:MAX_GENERATION_TEST_PATHS]

        available_configuration_paths = {
            file.path for file in configuration_files
        }
        ordered_configuration_paths = [
            path
            for path in GENERATION_CONFIGURATION_PRIORITY
            if path in available_configuration_paths
        ]
        configuration_paths = ordered_configuration_paths[
            :MAX_GENERATION_CONFIGURATION_PATHS
        ]

        return RepositoryGenerationSelection(
            target_path=target_path,
            related_test_paths=related_test_paths,
            configuration_paths=configuration_paths,
            is_truncated=paths.is_truncated,
        )

    @staticmethod
    def is_direct_test_for_source(test_path: str, source_path: str) -> bool:
        """Match standard test filenames to a Python source filename."""
        source_stem = PurePosixPath(source_path).stem.lower()
        test_filename = PurePosixPath(test_path).name.lower()
        return test_filename in {
            f"test_{source_stem}.py",
            f"{source_stem}_test.py",
        }

    @staticmethod
    def is_test_path(path: str) -> bool:
        """Recognize common Python test file and directory conventions."""
        path_parts = PurePosixPath(path).parts
        filename = path_parts[-1]

        return (
            bool(TEST_DIRECTORY_NAMES.intersection(path_parts[:-1]))
            or filename.startswith("test_")
            or filename.endswith("_test.py")
            or filename in {"test.py", "tests.py"}
        )

    @staticmethod
    def is_source_path(path: str) -> bool:
        """Exclude environments and Python configuration files from source paths."""
        path_parts = PurePosixPath(path).parts

        return (
            not EXCLUDED_SOURCE_DIRECTORY_NAMES.intersection(path_parts[:-1])
            and (len(path_parts) > 1 or path_parts[-1] not in CONFIGURATION_FILENAMES)
        )

    @staticmethod
    def detect_project_tool(contents_by_path: dict[str, str]) -> str | None:
        """Recognize common Python dependency and build tools from configuration."""
        pyproject_content = contents_by_path.get("pyproject.toml", "")

        if "[tool.poetry]" in pyproject_content or "poetry-core" in pyproject_content:
            return "poetry"
        if "[tool.pdm]" in pyproject_content:
            return "pdm"
        if "[tool.hatch" in pyproject_content:
            return "hatch"
        if "Pipfile" in contents_by_path:
            return "pipenv"
        if (
            "setup.cfg" in contents_by_path
            or "setup.py" in contents_by_path
            or "setuptools" in pyproject_content
        ):
            return "setuptools"
        if "requirements.txt" in contents_by_path:
            return "pip"

        return None

    @staticmethod
    def detect_test_runner(contents_by_path: dict[str, str]) -> str | None:
        """Recognize configured Python test runners."""
        configuration_contents = "\n".join(contents_by_path.values())

        if "tox.ini" in contents_by_path:
            return "tox"
        if (
            "[tool.pytest" in configuration_contents
            or "[pytest]" in configuration_contents
            or "pytest" in configuration_contents
        ):
            return "pytest"

        return None

    @classmethod
    def build_test_plan_steps(
        cls, setup: PythonProjectSetup, paths: RepositoryPaths
    ) -> list[RepositoryTestPlanStep]:
        """Create concise next steps without running repository code."""
        if not setup.is_python_project:
            return [
                RepositoryTestPlanStep(
                    action="confirm_project_type",
                    description="No supported Python configuration files were found.",
                    command=None,
                )
            ]

        steps = [
            RepositoryTestPlanStep(
                action="prepare_environment",
                description=(
                    f"Prepare dependencies with {setup.project_tool}."
                    if setup.project_tool
                    else "Review the configuration files before preparing dependencies."
                ),
                command=cls.installation_command(setup.project_tool),
            )
        ]

        if setup.test_runner:
            steps.append(
                RepositoryTestPlanStep(
                    action="run_existing_tests",
                    description=f"Run the existing {setup.test_runner} test suite.",
                    command=cls.test_command(
                        setup.project_tool, setup.test_runner
                    ),
                )
            )
        elif paths.test_paths:
            steps.append(
                RepositoryTestPlanStep(
                    action="confirm_test_runner",
                    description="Review the existing test files to determine their runner.",
                    command=None,
                )
            )

        if paths.source_paths:
            steps.append(
                RepositoryTestPlanStep(
                    action="review_source_coverage",
                    description=(
                        f"Review {len(paths.source_paths)} likely source files against "
                        f"{len(paths.test_paths)} existing test files."
                    ),
                    command=None,
                )
            )

        if paths.is_truncated:
            steps.append(
                RepositoryTestPlanStep(
                    action="expand_repository_context",
                    description="The repository tree is incomplete; inspect additional paths before testing.",
                    command=None,
                )
            )

        return steps

    @staticmethod
    def installation_command(project_tool: str | None) -> str | None:
        """Return a conservative dependency-install command for a recognized tool."""
        return {
            "poetry": "poetry install",
            "pdm": "pdm install",
            "pipenv": "pipenv install --dev",
            "pip": "pip install -r requirements.txt",
            "setuptools": "pip install -e .",
        }.get(project_tool)

    @staticmethod
    def test_command(project_tool: str | None, test_runner: str) -> str:
        """Return a test command that uses a managed environment when needed."""
        environment_commands = {
            "poetry": "poetry run",
            "pdm": "pdm run",
            "pipenv": "pipenv run",
        }
        prefix = environment_commands.get(project_tool)

        return f"{prefix} {test_runner}" if prefix else test_runner
