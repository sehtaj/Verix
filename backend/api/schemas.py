"""Pydantic request schemas for the Verix API."""

from pathlib import PurePosixPath
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from models.fix_proposal import (
    COMMIT_SHA_PATTERN,
    validate_fix_patch,
    validate_fix_target_path,
)


MAX_REPOSITORY_REFERENCE_CHARACTERS = 255
MAX_REPOSITORY_PATH_CHARACTERS = 1024
INVALID_GIT_REFERENCE_CHARACTERS = re.compile(r"[~^:?*\[\\]")


def _validate_repository_path(value: str, field_name: str) -> str:
    """Require one bounded repository-relative POSIX path."""
    if value != value.strip():
        raise ValueError(f"{field_name} cannot have surrounding whitespace.")
    if len(value) > MAX_REPOSITORY_PATH_CHARACTERS:
        raise ValueError(f"{field_name} is too long.")
    if "\\" in value or any(
        ord(character) < 32 or ord(character) == 127 for character in value
    ):
        raise ValueError(f"{field_name} must use a safe repository path.")

    path = PurePosixPath(value)
    components = value.split("/")
    if (
        not value
        or path.is_absolute()
        or any(component in {"", ".", ".."} for component in components)
    ):
        raise ValueError(f"{field_name} must be a repository-relative path.")

    return value


class GenerateTestsRequest(BaseModel):
    code: str = Field(min_length=1)


class RepositoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = Field(min_length=1)


class RepositoryReferenceRequest(RepositoryRequest):
    """A validated branch, tag, or commit choice for repository workflows."""

    reference: str | None = Field(
        default=None,
        min_length=1,
        max_length=MAX_REPOSITORY_REFERENCE_CHARACTERS,
        description="Branch, tag, or commit to resolve to one immutable commit SHA.",
    )

    @field_validator("reference")
    @classmethod
    def validate_reference(cls, value: str | None) -> str | None:
        """Accept a bounded Git branch, tag, or commit reference."""
        if value is None:
            return None
        if value != value.strip():
            raise ValueError("Repository reference cannot have surrounding whitespace.")
        if (
            value == "@"
            or value.startswith(("-", "/"))
            or value.endswith(("/", "."))
            or ".." in value
            or "@{" in value
            or INVALID_GIT_REFERENCE_CHARACTERS.search(value)
            or any(
                character.isspace()
                or ord(character) < 32
                or ord(character) == 127
                for character in value
            )
        ):
            raise ValueError("Repository reference is not a safe Git reference.")

        components = value.split("/")
        if any(
            not component
            or component.startswith(".")
            or component.endswith((".", ".lock"))
            for component in components
        ):
            raise ValueError("Repository reference is not a safe Git reference.")

        return value


class RepositorySubdirectoryRequest(RepositoryReferenceRequest):
    """A validated project subdirectory choice for repository workflows."""

    subdirectory: str | None = Field(
        default=None,
        min_length=1,
        max_length=MAX_REPOSITORY_PATH_CHARACTERS,
        description="Optional repository-relative project directory.",
    )

    @field_validator("subdirectory")
    @classmethod
    def validate_subdirectory(cls, value: str | None) -> str | None:
        """Accept only a repository-relative project directory path."""
        if value is None:
            return None
        return _validate_repository_path(value, "Repository subdirectory")


class RepositoryTargetRequest(RepositorySubdirectoryRequest):
    """Validated repository targeting choices for V0.10 workflows."""

    target_path: str | None = Field(
        default=None,
        min_length=1,
        max_length=MAX_REPOSITORY_PATH_CHARACTERS,
        description="Optional repository-relative Python source file.",
    )

    @field_validator("target_path")
    @classmethod
    def validate_target_path(cls, value: str | None) -> str | None:
        """Accept only a repository-relative Python source path."""
        if value is None:
            return None
        value = _validate_repository_path(value, "Repository source target")
        if not value.endswith(".py"):
            raise ValueError("Repository source target must be a Python file.")
        return value

    @model_validator(mode="after")
    def validate_target_scope(self) -> "RepositoryTargetRequest":
        """Keep a manual source target inside the selected project directory."""
        if self.subdirectory is None or self.target_path is None:
            return self

        subdirectory = PurePosixPath(self.subdirectory)
        target_path = PurePosixPath(self.target_path)
        if target_path == subdirectory or not target_path.is_relative_to(
            subdirectory
        ):
            raise ValueError(
                "Repository source target must be inside the selected subdirectory."
            )
        return self


class RepositoryFixProposalRequest(RepositoryTargetRequest):
    """A request to propose, but never automatically apply, one source fix."""

    target_path: str = Field(
        min_length=1,
        max_length=MAX_REPOSITORY_PATH_CHARACTERS,
        description="Repository-relative Python source file allowed to change.",
    )

    @model_validator(mode="after")
    def validate_fix_target(self) -> "RepositoryFixProposalRequest":
        """Keep fixes away from Verix-owned disposable workspace paths."""
        validate_fix_target_path(self.target_path, self.subdirectory)
        return self


class RepositoryFixApplyRequest(RepositoryRequest):
    """An explicit approval for a previously displayed, pinned source patch."""

    revision: str = Field(
        min_length=40,
        max_length=40,
        description="Exact commit SHA used when Verix created the proposal.",
    )
    subdirectory: str | None = Field(
        default=None,
        min_length=1,
        max_length=MAX_REPOSITORY_PATH_CHARACTERS,
        description="Optional repository-relative project directory.",
    )
    target_path: str = Field(
        min_length=1,
        max_length=MAX_REPOSITORY_PATH_CHARACTERS,
        description="Repository-relative Python source file approved to change.",
    )
    patch: str = Field(
        min_length=1,
        max_length=128 * 1024,
        description="Exact unified diff previously shown to the developer.",
    )
    approved: Literal[True] = Field(
        description="Must be true to explicitly authorize later disposable application.",
    )

    @field_validator("revision")
    @classmethod
    def validate_revision(cls, value: str) -> str:
        """Require the immutable revision displayed with the proposal."""
        if COMMIT_SHA_PATTERN.fullmatch(value) is None:
            raise ValueError("Repository fix approval requires a full commit SHA.")
        return value

    @field_validator("subdirectory")
    @classmethod
    def validate_subdirectory(cls, value: str | None) -> str | None:
        """Accept only a safe optional project directory."""
        if value is None:
            return None
        return _validate_repository_path(value, "Repository subdirectory")

    @field_validator("target_path")
    @classmethod
    def validate_target_path(cls, value: str) -> str:
        """Accept only a safe repository-relative Python source path."""
        value = _validate_repository_path(value, "Repository source target")
        if not value.endswith(".py"):
            raise ValueError("Repository source target must be a Python file.")
        return value

    @model_validator(mode="after")
    def validate_approved_fix(self) -> "RepositoryFixApplyRequest":
        """Require one safe target and bounded patch before later execution exists."""
        validate_fix_target_path(self.target_path, self.subdirectory)
        validate_fix_patch(self.patch)
        return self
