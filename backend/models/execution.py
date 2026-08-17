"""Result models shared by isolated execution workflows."""

from dataclasses import dataclass


@dataclass
class TestExecutionResult:
    """The captured result of an isolated container command."""

    return_code: int | None
    output: str
    timed_out: bool = False
    skipped: bool = False


@dataclass
class RepositoryTestResults:
    """Keep original repository results separate from generated results."""

    existing: TestExecutionResult
    generated: TestExecutionResult
