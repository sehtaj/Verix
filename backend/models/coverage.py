"""Branch-coverage evidence for one selected repository source file."""

from dataclasses import dataclass


Branch = tuple[int, int]


@dataclass(frozen=True)
class BranchCoverageRun:
    """Raw branches observed during one isolated test run."""

    target_path: str
    total_branches: int
    executed_branches: frozenset[Branch]


@dataclass(frozen=True)
class BranchCoverageMeasurement:
    """Display-safe aggregate for one set of covered branches."""

    covered_branches: int
    total_branches: int
    percent: float


@dataclass(frozen=True)
class BranchCoverageSummary:
    """Existing and combined branch coverage kept explicitly separate."""

    target_path: str
    available: bool
    existing: BranchCoverageMeasurement | None = None
    combined: BranchCoverageMeasurement | None = None
    incremental_covered_branches: int | None = None
    untested_branches: int | None = None
    unavailable_reason: str | None = None
