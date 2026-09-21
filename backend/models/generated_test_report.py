"""Validated expected-behavior provenance for generated repository tests."""

from dataclasses import dataclass
from enum import StrEnum


class BehaviorSourceKind(StrEnum):
    """The bounded repository evidence categories available to Gemini."""

    SOURCE_CODE = "source_code"
    DOCUMENTATION = "documentation"
    EXISTING_TEST = "existing_test"
    CONFIGURATION = "configuration"


class TestCaseCategory(StrEnum):
    """The observable behavior category covered by one generated test."""

    NORMAL = "normal"
    BOUNDARY = "boundary"
    INVALID_INPUT = "invalid_input"
    ERROR_HANDLING = "error_handling"


class TestDesignStrategy(StrEnum):
    """How repository evidence informed one generated test."""

    BLACK_BOX = "black_box"
    GRAY_BOX = "gray_box"


@dataclass(frozen=True)
class BehaviorSource:
    """One exact excerpt from a bounded repository file."""

    kind: BehaviorSourceKind
    path: str
    excerpt: str


@dataclass(frozen=True)
class GeneratedTestCase:
    """A classification for one concrete generated pytest function."""

    test_name: str
    category: TestCaseCategory
    strategy: TestDesignStrategy
    expected_behavior: str


@dataclass(frozen=True)
class GeneratedTestReport:
    """Generated code plus bounded, non-authoritative provenance metadata."""

    tests: str
    sources: tuple[BehaviorSource, ...]
    assumptions: tuple[str, ...]
    cases: tuple[GeneratedTestCase, ...]
    model: str
