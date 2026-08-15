"""Fetch metadata and selected configuration files for public GitHub repositories."""

from base64 import b64decode
from binascii import Error as Base64DecodeError
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
MAX_GENERATION_TEST_PATHS = 3
MAX_GENERATION_CONFIGURATION_PATHS = 3
MAX_GENERATION_FILE_BYTES = 64 * 1024
MAX_GENERATION_CONTEXT_BYTES = 128 * 1024
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


@dataclass(frozen=True)
class RepositoryArchiveReference:
    """A validated public repository archive that can be downloaded safely."""

    owner: str
    repository: str
    default_branch: str
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
    available_configuration_paths: tuple[str, ...] = ()


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


@dataclass
class RepositoryGenerationSelection:
    """A bounded set of repository paths for one future generation request."""

    target_path: str | None
    related_test_paths: list[str]
    configuration_paths: list[str]
    is_truncated: bool


@dataclass(frozen=True)
class RepositoryFileContent:
    """One bounded UTF-8 repository file selected for generation context."""

    path: str
    content: str
    byte_count: int


@dataclass
class RepositoryGenerationContext:
    """Bounded source, tests, and configuration ready for prompt construction."""

    selection: RepositoryGenerationSelection
    source_file: RepositoryFileContent | None
    test_files: list[RepositoryFileContent]
    configuration_files: list[RepositoryConfigurationFile]
    skipped_paths: list[str]
    total_bytes: int


@dataclass
class RepositoryContext:
    """Repository evidence and the test plan derived from it."""

    metadata: RepositoryMetadata
    tree: RepositoryTree
    configuration_files: list[RepositoryConfigurationFile]
    test_plan: RepositoryTestPlan
    generation_selection: RepositoryGenerationSelection


class GitHubRepositoryService:
    """Retrieve selected public information for a GitHub repository."""

    def fetch_metadata(self, repository_url: str) -> RepositoryMetadata:
        """Validate a GitHub URL and return its public repository metadata."""
        owner, repository = self._parse_repository_url(repository_url)
        data = self._fetch_repository_data(owner, repository)

        return self._build_metadata(data)

    def fetch_archive_reference(
        self, repository_url: str
    ) -> RepositoryArchiveReference:
        """Validate a public repository and return its default-branch archive URL."""
        owner, repository = self._parse_repository_url(repository_url)
        data = self._fetch_repository_data(owner, repository)
        default_branch = str(data["default_branch"])

        return RepositoryArchiveReference(
            owner=owner,
            repository=repository,
            default_branch=default_branch,
            url=(
                f"{GITHUB_API_URL}/{quote(owner, safe='')}/"
                f"{quote(repository, safe='')}/tarball/"
                f"{quote(default_branch, safe='')}"
            ),
        )

    @staticmethod
    def _build_metadata(data: dict[str, object]) -> RepositoryMetadata:
        """Build the public metadata model from GitHub repository data."""
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
        return self._fetch_file_tree(owner, repository, repository_data)

    def _fetch_file_tree(
        self, owner: str, repository: str, repository_data: dict[str, object]
    ) -> RepositoryTree:
        """Fetch a bounded recursive tree using previously fetched repository data."""
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
            available_configuration_paths=tuple(
                entry["path"]
                for entry in tree_entries
                if entry["type"] == "blob"
                and entry["path"] in CONFIGURATION_FILENAMES
            ),
        )

    def fetch_configuration_files(
        self, repository_url: str
    ) -> list[RepositoryConfigurationFile]:
        """Return available root-level Python configuration files from a public repository."""
        owner, repository = self._parse_repository_url(repository_url)
        repository_data = self._fetch_repository_data(owner, repository)
        tree = self._fetch_file_tree(owner, repository, repository_data)

        return self._fetch_configuration_files(owner, repository, tree)

    def _fetch_configuration_files(
        self, owner: str, repository: str, tree: RepositoryTree
    ) -> list[RepositoryConfigurationFile]:
        """Fetch only allowed configuration files known to exist in the tree."""
        configuration_files = []
        available_paths = set(tree.available_configuration_paths)

        for path in CONFIGURATION_FILENAMES:
            if path not in available_paths:
                continue

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

        return self._identify_likely_paths(tree)

    def _identify_likely_paths(self, tree: RepositoryTree) -> RepositoryPaths:
        """Identify likely Python paths from an already fetched tree."""
        python_file_paths = [
            entry.path
            for entry in tree.entries
            if entry.type == "blob" and entry.path.endswith(".py")
        ]
        test_paths = [
            path
            for path in python_file_paths
            if self._is_test_path(path)
            and PurePosixPath(path).name not in {"__init__.py", "__main__.py"}
        ]
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

        return self._detect_python_project_setup(configuration_files)

    def _detect_python_project_setup(
        self, configuration_files: list[RepositoryConfigurationFile]
    ) -> PythonProjectSetup:
        """Recognize Python tooling from already fetched configuration files."""
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
        return self.fetch_context(repository_url).test_plan

    def fetch_context(self, repository_url: str) -> RepositoryContext:
        """Fetch repository evidence once and derive its complete test-planning context."""
        owner, repository = self._parse_repository_url(repository_url)
        repository_data = self._fetch_repository_data(owner, repository)
        metadata = self._build_metadata(repository_data)
        tree = self._fetch_file_tree(owner, repository, repository_data)
        configuration_files = self._fetch_configuration_files(
            owner, repository, tree
        )
        paths = self._identify_likely_paths(tree)
        setup = self._detect_python_project_setup(configuration_files)
        test_plan = RepositoryTestPlan(
            setup=setup,
            source_paths=paths.source_paths,
            test_paths=paths.test_paths,
            steps=self._build_test_plan_steps(setup, paths),
            is_truncated=paths.is_truncated,
        )
        generation_selection = self._select_generation_context(
            paths, configuration_files
        )

        return RepositoryContext(
            metadata=metadata,
            tree=tree,
            configuration_files=configuration_files,
            test_plan=test_plan,
            generation_selection=generation_selection,
        )

    def fetch_generation_context(
        self, repository_url: str
    ) -> RepositoryGenerationContext:
        """Fetch only the bounded file contents selected for one generation request."""
        owner, repository = self._parse_repository_url(repository_url)
        repository_context = self.fetch_context(repository_url)
        selection = repository_context.generation_selection
        selected_configuration_files = {
            file.path: file for file in repository_context.configuration_files
        }
        source_file: RepositoryFileContent | None = None
        test_files: list[RepositoryFileContent] = []
        configuration_files: list[RepositoryConfigurationFile] = []
        skipped_paths: list[str] = []
        total_bytes = 0

        if selection.target_path is not None:
            try:
                source_file = self._fetch_bounded_repository_file(
                    owner, repository, selection.target_path
                )
            except ValueError:
                raise ValueError(
                    "The selected source file is too large for test generation."
                ) from None
            total_bytes = source_file.byte_count

            for path in selection.related_test_paths:
                try:
                    test_file = self._fetch_bounded_repository_file(
                        owner, repository, path
                    )
                except (RuntimeError, ValueError):
                    skipped_paths.append(path)
                    continue

                if total_bytes + test_file.byte_count > MAX_GENERATION_CONTEXT_BYTES:
                    skipped_paths.append(path)
                    continue

                test_files.append(test_file)
                total_bytes += test_file.byte_count

        for path in selection.configuration_paths:
            configuration_file = selected_configuration_files.get(path)
            if configuration_file is None:
                continue

            byte_count = len(configuration_file.content.encode("utf-8"))
            if (
                byte_count > MAX_GENERATION_FILE_BYTES
                or total_bytes + byte_count > MAX_GENERATION_CONTEXT_BYTES
            ):
                skipped_paths.append(path)
                continue

            configuration_files.append(configuration_file)
            total_bytes += byte_count

        return RepositoryGenerationContext(
            selection=selection,
            source_file=source_file,
            test_files=test_files,
            configuration_files=configuration_files,
            skipped_paths=skipped_paths,
            total_bytes=total_bytes,
        )

    @staticmethod
    def _select_generation_context(
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
                        GitHubRepositoryService._is_direct_test_for_source(
                            test_path, path
                        )
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
                    not GitHubRepositoryService._is_direct_test_for_source(
                        path, target_path
                    ),
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
    def _is_direct_test_for_source(test_path: str, source_path: str) -> bool:
        """Match standard test filenames to a Python source filename."""
        source_stem = PurePosixPath(source_path).stem.lower()
        test_filename = PurePosixPath(test_path).name.lower()
        return test_filename in {
            f"test_{source_stem}.py",
            f"{source_stem}_test.py",
        }

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
            raise RuntimeError("GitHub could not return repository file contents.")

        return data

    def _fetch_bounded_repository_file(
        self, owner: str, repository: str, path: str
    ) -> RepositoryFileContent:
        """Fetch one selected UTF-8 file without exceeding the per-file limit."""
        file_data = self._fetch_file_data(owner, repository, path)
        if file_data is None:
            raise RuntimeError("GitHub could not return selected repository files.")

        declared_size = file_data.get("size")
        if isinstance(declared_size, int) and declared_size > MAX_GENERATION_FILE_BYTES:
            raise ValueError("Selected repository file is too large.")

        encoded_content = file_data.get("content")
        if not isinstance(encoded_content, str):
            raise RuntimeError(
                "GitHub could not return selected repository files."
            )

        compact_content = "".join(encoded_content.split())
        maximum_encoded_characters = 4 * ((MAX_GENERATION_FILE_BYTES + 2) // 3)
        if len(compact_content) > maximum_encoded_characters:
            raise ValueError("Selected repository file is too large.")

        try:
            raw_content = b64decode(compact_content, validate=True)
            content = raw_content.decode("utf-8")
        except (Base64DecodeError, UnicodeDecodeError):
            raise RuntimeError(
                "GitHub could not return selected repository files."
            ) from None

        if len(raw_content) > MAX_GENERATION_FILE_BYTES:
            raise ValueError("Selected repository file is too large.")

        return RepositoryFileContent(
            path=path,
            content=content,
            byte_count=len(raw_content),
        )

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
