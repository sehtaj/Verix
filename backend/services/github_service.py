"""Fetch metadata and selected configuration files for public GitHub repositories."""

from base64 import b64decode
from dataclasses import dataclass
import json
import ssl
from pathlib import PurePosixPath
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

import certifi

GITHUB_API_URL = "https://api.github.com/repos"
MAX_TREE_ENTRIES = 500
CONFIGURATION_FILENAMES = (
    "pyproject.toml",
    "requirements.txt",
    "setup.cfg",
    "setup.py",
    "Pipfile",
    "tox.ini",
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
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


@dataclass
class RepositoryMetadata:
    """The public repository details used by the V0.4 interface."""

    name: str
    owner: str
    description: str | None
    language: str | None
    stars: int
    url: str


@dataclass
class RepositoryTreeEntry:
    """A file or directory in a repository tree."""

    path: str
    type: str


@dataclass
class RepositoryTree:
    """The bounded repository tree returned to the V0.5 interface."""

    entries: list[RepositoryTreeEntry]
    is_truncated: bool


@dataclass
class RepositoryConfigurationFile:
    """A root-level Python configuration file from a repository."""

    path: str
    content: str


@dataclass
class RepositoryPaths:
    """Likely Python source and test files discovered from a repository tree."""

    source_paths: list[str]
    test_paths: list[str]
    is_truncated: bool


@dataclass
class PythonProjectSetup:
    """Recognized Python project configuration and test tooling."""

    is_python_project: bool
    project_tool: str | None
    test_runner: str | None
    configuration_files: list[str]


@dataclass
class RepositoryTestPlanStep:
    """One evidence-based action in a repository test plan."""

    action: str
    description: str
    command: str | None


@dataclass
class RepositoryTestPlan:
    """A structured plan for testing a public Python repository."""

    setup: PythonProjectSetup
    source_paths: list[str]
    test_paths: list[str]
    steps: list[RepositoryTestPlanStep]
    is_truncated: bool


class GitHubRepositoryService:
    """Retrieve selected public information for a GitHub repository."""

    def fetch_metadata(self, repository_url: str) -> RepositoryMetadata:
        """Validate a GitHub URL and return its public repository metadata."""
        owner, repository = self._parse_repository_url(repository_url)
        data = self._fetch_repository_data(owner, repository)

        return RepositoryMetadata(
            name=data["name"],
            owner=data["owner"]["login"],
            description=data["description"],
            language=data["language"],
            stars=data["stargazers_count"],
            url=data["html_url"],
        )

    def fetch_file_tree(self, repository_url: str) -> RepositoryTree:
        """Return a bounded recursive tree for a public GitHub repository."""
        owner, repository = self._parse_repository_url(repository_url)
        repository_data = self._fetch_repository_data(owner, repository)
        branch = quote(repository_data["default_branch"], safe="")
        tree_data = self._request_json(
            f"{GITHUB_API_URL}/{quote(owner, safe='')}/{quote(repository, safe='')}/git/trees/{branch}?recursive=1"
        )
        tree_entries = sorted(
            tree_data["tree"],
            key=lambda entry: (entry["path"].lower(), entry["type"] != "tree"),
        )

        return RepositoryTree(
            entries=[
                RepositoryTreeEntry(path=entry["path"], type=entry["type"])
                for entry in tree_entries[:MAX_TREE_ENTRIES]
            ],
            is_truncated=tree_data["truncated"] or len(tree_entries) > MAX_TREE_ENTRIES,
        )

    def fetch_configuration_files(
        self, repository_url: str
    ) -> list[RepositoryConfigurationFile]:
        """Return available root-level Python configuration files from a public repository."""
        owner, repository = self._parse_repository_url(repository_url)
        self._fetch_repository_data(owner, repository)
        configuration_files = []

        for path in CONFIGURATION_FILENAMES:
            file_data = self._fetch_file_data(owner, repository, path)
            if file_data is None:
                continue

            try:
                content = b64decode(file_data["content"]).decode("utf-8")
            except (KeyError, TypeError, UnicodeDecodeError, ValueError):
                raise RuntimeError(
                    "GitHub could not return repository configuration files."
                ) from None

            configuration_files.append(
                RepositoryConfigurationFile(path=path, content=content)
            )

        return configuration_files

    def fetch_likely_paths(self, repository_url: str) -> RepositoryPaths:
        """Identify likely Python source and test files from a public repository tree."""
        tree = self.fetch_file_tree(repository_url)
        python_file_paths = [
            entry.path
            for entry in tree.entries
            if entry.type == "blob" and entry.path.endswith(".py")
        ]
        test_paths = [path for path in python_file_paths if self._is_test_path(path)]
        source_paths = [
            path
            for path in python_file_paths
            if not self._is_test_path(path) and self._is_source_path(path)
        ]

        return RepositoryPaths(
            source_paths=source_paths,
            test_paths=test_paths,
            is_truncated=tree.is_truncated,
        )

    def detect_python_project_setup(self, repository_url: str) -> PythonProjectSetup:
        """Recognize Python tooling from the repository's available configuration files."""
        configuration_files = self.fetch_configuration_files(repository_url)
        contents_by_path = {
            file.path: file.content.lower() for file in configuration_files
        }

        return PythonProjectSetup(
            is_python_project=bool(configuration_files),
            project_tool=self._detect_project_tool(contents_by_path),
            test_runner=self._detect_test_runner(contents_by_path),
            configuration_files=[file.path for file in configuration_files],
        )

    def generate_test_plan(self, repository_url: str) -> RepositoryTestPlan:
        """Build a test plan from available configuration and repository-path evidence."""
        setup = self.detect_python_project_setup(repository_url)
        paths = self.fetch_likely_paths(repository_url)

        return RepositoryTestPlan(
            setup=setup,
            source_paths=paths.source_paths,
            test_paths=paths.test_paths,
            steps=self._build_test_plan_steps(setup, paths),
            is_truncated=paths.is_truncated,
        )

    def _fetch_repository_data(self, owner: str, repository: str) -> dict[str, object]:
        """Fetch repository data and reject private repositories."""
        data = self._request_json(
            f"{GITHUB_API_URL}/{quote(owner, safe='')}/{quote(repository, safe='')}"
        )

        if data["private"]:
            raise ValueError("Repository is not public.")

        return data

    def _fetch_file_data(
        self, owner: str, repository: str, path: str
    ) -> dict[str, object] | None:
        """Fetch one file, returning None when the allowed file does not exist."""
        try:
            data = self._request_json(
                f"{GITHUB_API_URL}/{quote(owner, safe='')}/{quote(repository, safe='')}/contents/{quote(path, safe='')}"
            )
        except ValueError:
            return None

        if data.get("type") != "file" or data.get("encoding") != "base64":
            raise RuntimeError("GitHub could not return repository configuration files.")

        return data

    @staticmethod
    def _is_test_path(path: str) -> bool:
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
    def _is_source_path(path: str) -> bool:
        """Exclude generated environments and Python configuration files from source paths."""
        path_parts = PurePosixPath(path).parts

        return (
            not EXCLUDED_SOURCE_DIRECTORY_NAMES.intersection(path_parts[:-1])
            and (len(path_parts) > 1 or path_parts[-1] not in CONFIGURATION_FILENAMES)
        )

    @staticmethod
    def _detect_project_tool(contents_by_path: dict[str, str]) -> str | None:
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
    def _detect_test_runner(contents_by_path: dict[str, str]) -> str | None:
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

    @staticmethod
    def _build_test_plan_steps(
        setup: PythonProjectSetup, paths: RepositoryPaths
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
                command=GitHubRepositoryService._installation_command(
                    setup.project_tool
                ),
            )
        ]

        if setup.test_runner:
            steps.append(
                RepositoryTestPlanStep(
                    action="run_existing_tests",
                    description=f"Run the existing {setup.test_runner} test suite.",
                    command=GitHubRepositoryService._test_command(
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
    def _installation_command(project_tool: str | None) -> str | None:
        """Return a conservative dependency-install command for a recognized tool."""
        return {
            "poetry": "poetry install",
            "pdm": "pdm install",
            "pipenv": "pipenv install --dev",
            "pip": "pip install -r requirements.txt",
            "setuptools": "pip install -e .",
        }.get(project_tool)

    @staticmethod
    def _test_command(project_tool: str | None, test_runner: str) -> str:
        """Return a test command that uses a managed environment when needed."""
        environment_commands = {
            "poetry": "poetry run",
            "pdm": "pdm run",
            "pipenv": "pipenv run",
        }
        prefix = environment_commands.get(project_tool)

        return f"{prefix} {test_runner}" if prefix else test_runner

    @staticmethod
    def _request_json(url: str) -> dict[str, object]:
        """Request JSON from GitHub's public API with safe error messages."""
        request = Request(url, headers={"Accept": "application/vnd.github+json"})
        try:
            with urlopen(request, context=SSL_CONTEXT, timeout=10) as response:
                return json.load(response)
        except HTTPError as error:
            if error.code == 404:
                raise ValueError("Repository was not found or is not public.") from None
            raise RuntimeError("GitHub could not return repository metadata.") from None
        except URLError:
            raise RuntimeError("GitHub could not return repository metadata.") from None

    @staticmethod
    def _parse_repository_url(repository_url: str) -> tuple[str, str]:
        parsed_url = urlparse(repository_url)
        path_segments = [segment for segment in parsed_url.path.split("/") if segment]

        if (
            parsed_url.scheme != "https"
            or parsed_url.netloc.lower() not in {"github.com", "github.com:443"}
            or len(path_segments) != 2
            or parsed_url.query
            or parsed_url.fragment
        ):
            raise ValueError(
                "Enter a public GitHub repository URL, such as https://github.com/owner/repository."
            )

        return path_segments[0], path_segments[1]
