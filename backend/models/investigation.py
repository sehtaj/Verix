"""Structured, bounded facts used to investigate repository test outcomes."""

from dataclasses import dataclass
from enum import StrEnum

from models.repository import RepositoryTestPlan


class RepositoryOutcomeKind(StrEnum):
    """The mutually exclusive result categories planned for V0.9."""

    SETUP_FAILED = "setup_failed"
    NO_EXISTING_TESTS = "no_existing_tests"
    EXISTING_TESTS_TIMED_OUT = "existing_tests_timed_out"
    EXISTING_TESTS_FAILED = "existing_tests_failed"
    GENERATED_TESTS_TIMED_OUT = "generated_tests_timed_out"
    GENERATED_TESTS_FAILED = "generated_tests_failed"
    TESTS_PASSED = "tests_passed"


@dataclass(frozen=True)
class RepositoryCommandEvidence:
    """A bounded record of one installation or isolated test command."""

    return_code: int | None
    timed_out: bool
    skipped: bool
    output_excerpt: str
    output_truncated: bool


@dataclass(frozen=True)
class RepositoryInvestigationEvidence:
    """The small factual input that a later investigation step may use."""

    test_runner: str
    installation: RepositoryCommandEvidence
    existing_execution: RepositoryCommandEvidence
    generated_execution: RepositoryCommandEvidence | None


@dataclass(frozen=True)
class RepositoryInvestigationRun:
    """One completed plan-generate-execute-investigate workflow run."""

    test_plan: RepositoryTestPlan
    target_path: str
    generated_tests: str
    execution_results: dict[str, object]
    evidence: RepositoryInvestigationEvidence
    outcome: RepositoryOutcomeKind
    explanation: str
