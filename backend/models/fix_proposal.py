"""Data contract for one approval-gated repository fix proposal."""

from dataclasses import dataclass, field
from pathlib import PurePosixPath
import re

from models.investigation import (
    RepositoryCommandEvidence,
    RepositoryInvestigationRun,
    RepositoryOutcomeKind,
)
from models.repository import RepositoryConfigurationFile, RepositoryFileContent


MAX_FIX_SUMMARY_CHARACTERS = 1_000
MAX_FIX_PATCH_BYTES = 128 * 1024
MAX_FIX_TARGET_CHARACTERS = 1_024
MAX_FIX_CONTEXT_BYTES = 256 * 1024
MAX_FIX_RELATED_TEST_FILES = 1
MAX_FIX_CONFIGURATION_FILES = 2
RESERVED_FIX_PATH_COMPONENTS = frozenset(
    {
        ".verix-generated-tests",
        ".verix-tox",
        ".verix-venv",
    }
)
COMMIT_SHA_PATTERN = re.compile(r"[0-9a-fA-F]{40}")


def validate_fix_target_path(target_path: str, subdirectory: str | None) -> None:
    """Require one safe Python file inside the selected project."""
    if (
        not target_path
        or target_path != target_path.strip()
        or len(target_path) > MAX_FIX_TARGET_CHARACTERS
        or "\\" in target_path
        or any(
            ord(character) < 32 or ord(character) == 127
            for character in target_path
        )
    ):
        raise ValueError("Repository fix target must use a safe repository path.")

    path = PurePosixPath(target_path)
    if (
        path.is_absolute()
        or path.suffix != ".py"
        or any(component in {"", ".", ".."} for component in target_path.split("/"))
    ):
        raise ValueError("Repository fix target must be a relative Python file.")

    if subdirectory is not None:
        project_path = PurePosixPath(subdirectory)
        if path == project_path or not path.is_relative_to(project_path):
            raise ValueError(
                "Repository fix target must be inside the selected subdirectory."
            )

    if RESERVED_FIX_PATH_COMPONENTS.intersection(path.parts):
        raise ValueError("Repository fix target uses a reserved Verix path.")


@dataclass(frozen=True)
class RepositoryFixProposal:
    """One immutable patch proposal that Verix has not applied."""

    revision: str
    subdirectory: str | None
    target_path: str
    summary: str
    patch: str
    approval_required: bool = field(default=True, init=False)
    applied: bool = field(default=False, init=False)

    def __post_init__(self) -> None:
        """Reject an unsafe or unbounded proposal at the model boundary."""
        if COMMIT_SHA_PATTERN.fullmatch(self.revision) is None:
            raise ValueError("Repository fix proposal requires a full commit SHA.")

        validate_fix_target_path(self.target_path, self.subdirectory)

        if not self.summary.strip():
            raise ValueError("Repository fix proposal summary cannot be empty.")
        if len(self.summary) > MAX_FIX_SUMMARY_CHARACTERS:
            raise ValueError("Repository fix proposal summary is too long.")

        if not self.patch.strip():
            raise ValueError("Repository fix proposal patch cannot be empty.")
        if "\x00" in self.patch:
            raise ValueError("Repository fix proposal patch contains invalid data.")
        if len(self.patch.encode("utf-8")) > MAX_FIX_PATCH_BYTES:
            raise ValueError("Repository fix proposal patch is too large.")


@dataclass(frozen=True)
class RepositoryFixContext:
    """The bounded source and failure evidence allowed into one fix prompt."""

    revision: str
    subdirectory: str | None
    target_path: str
    outcome: RepositoryOutcomeKind
    source_file: RepositoryFileContent
    test_files: tuple[RepositoryFileContent, ...]
    configuration_files: tuple[RepositoryConfigurationFile, ...]
    failure_evidence: RepositoryCommandEvidence
    investigation_explanation: str
    skipped_paths: tuple[str, ...]
    total_bytes: int


@dataclass(frozen=True)
class RepositoryFixProposalRun:
    """One investigation and its single unapplied fix proposal."""

    investigation: RepositoryInvestigationRun
    proposal: RepositoryFixProposal
    validated: bool = field(default=True, init=False)
