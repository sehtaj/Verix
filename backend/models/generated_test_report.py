"""Validated expected-behavior provenance for generated repository tests."""

from dataclasses import dataclass
from enum import StrEnum


class BehaviorSourceKind(StrEnum):
    """The bounded repository evidence categories available to Gemini."""

    SOURCE_CODE = "source_code"
    DOCUMENTATION = "documentation"
    EXISTING_TEST = "existing_test"
    CONFIGURATION = "configuration"


@dataclass(frozen=True)
class BehaviorSource:
    """One exact excerpt from a bounded repository file."""

    kind: BehaviorSourceKind
    path: str
    excerpt: str


@dataclass(frozen=True)
class GeneratedTestReport:
    """Generated code plus bounded, non-authoritative provenance metadata."""

    tests: str
    sources: tuple[BehaviorSource, ...]
    assumptions: tuple[str, ...]
    model: str
