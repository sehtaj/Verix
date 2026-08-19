"""Data structures used by public repository workflows."""

from dataclasses import dataclass


@dataclass
class RepositoryMetadata:
    """Public GitHub repository details."""

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
    revision: str
    url: str


@dataclass
class RepositoryTreeEntry:
    """A file or directory in a repository tree."""

    path: str
    type: str


@dataclass
class RepositoryTree:
    """A bounded repository tree."""

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
    """A bounded set of repository paths for one generation request."""

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
    revision: str | None = None
    test_plan: RepositoryTestPlan | None = None


@dataclass
class RepositoryContext:
    """Repository evidence and the test plan derived from it."""

    metadata: RepositoryMetadata
    tree: RepositoryTree
    configuration_files: list[RepositoryConfigurationFile]
    test_plan: RepositoryTestPlan
    generation_selection: RepositoryGenerationSelection
    revision: str | None = None
