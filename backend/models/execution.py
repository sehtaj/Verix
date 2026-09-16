"""Result models shared by isolated execution workflows."""

from dataclasses import dataclass

from models.coverage import BranchCoverageRun, BranchCoverageSummary


@dataclass
class TestExecutionResult:
    """The captured result of an isolated container command."""

    return_code: int | None
    output: str
    timed_out: bool = False
    skipped: bool = False
    branch_coverage: BranchCoverageRun | None = None


@dataclass
class RepositoryTestResults:
    """Keep original repository results separate from generated results."""

    existing: TestExecutionResult
    generated: TestExecutionResult
    branch_coverage: BranchCoverageSummary | None = None
