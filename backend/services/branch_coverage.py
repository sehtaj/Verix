"""Parse isolated branch evidence and build honest coverage summaries."""

import json

from models.coverage import (
    Branch,
    BranchCoverageMeasurement,
    BranchCoverageRun,
    BranchCoverageSummary,
)
from models.execution import TestExecutionResult


COVERAGE_SENTINEL = "VERIX_BRANCH_COVERAGE="
MAX_BRANCHES_PER_FILE = 20_000


def extract_branch_coverage(
    result: TestExecutionResult,
    target_path: str,
) -> TestExecutionResult:
    """Remove trusted runner metadata from output and attach validated evidence."""
    marker_index = result.output.rfind(COVERAGE_SENTINEL)
    if marker_index < 0:
        return result

    marker_end = result.output.find("\n", marker_index)
    if marker_end < 0:
        marker_end = len(result.output)
    payload_text = result.output[
        marker_index + len(COVERAGE_SENTINEL) : marker_end
    ]
    cleaned_output = result.output[:marker_index] + result.output[marker_end + 1 :]

    try:
        payload = json.loads(payload_text)
        if not isinstance(payload, dict) or set(payload) != {
            "target_path",
            "total_branches",
            "executed_branches",
        }:
            raise ValueError
        if payload["target_path"] != target_path:
            raise ValueError
        total_branches = payload["total_branches"]
        if not isinstance(total_branches, int) or total_branches < 0:
            raise ValueError
        executed = _parse_branches(payload["executed_branches"])
        if len(executed) > total_branches:
            raise ValueError
        coverage = BranchCoverageRun(
            target_path=target_path,
            total_branches=total_branches,
            executed_branches=executed,
        )
    except (TypeError, ValueError, json.JSONDecodeError):
        coverage = None

    return TestExecutionResult(
        return_code=result.return_code,
        output=cleaned_output,
        timed_out=result.timed_out,
        skipped=result.skipped,
        branch_coverage=coverage,
    )


def summarize_branch_coverage(
    target_path: str,
    existing: TestExecutionResult,
    generated: TestExecutionResult,
    *,
    test_runner: str,
) -> BranchCoverageSummary:
    """Report existing coverage and the generated suite's true branch delta."""
    if test_runner != "pytest":
        return unavailable_branch_coverage(
            target_path,
            "Branch coverage is not yet available for tox-based projects.",
        )

    existing_run = existing.branch_coverage
    generated_run = generated.branch_coverage
    if existing_run is None or generated_run is None:
        return unavailable_branch_coverage(
            target_path,
            "Branch coverage could not be collected from both isolated test runs.",
        )
    if (
        existing_run.target_path != target_path
        or generated_run.target_path != target_path
        or existing_run.total_branches != generated_run.total_branches
    ):
        return unavailable_branch_coverage(
            target_path,
            "Branch coverage evidence did not describe the same selected source.",
        )

    total = existing_run.total_branches
    existing_covered = existing_run.executed_branches
    combined_covered = existing_run.executed_branches | generated_run.executed_branches
    incremental = generated_run.executed_branches - existing_run.executed_branches
    if len(combined_covered) > total:
        return unavailable_branch_coverage(
            target_path,
            "Branch coverage evidence exceeded the selected source branch total.",
        )

    return BranchCoverageSummary(
        target_path=target_path,
        available=True,
        existing=_measurement(len(existing_covered), total),
        combined=_measurement(len(combined_covered), total),
        incremental_covered_branches=len(incremental),
        untested_branches=total - len(combined_covered),
    )


def unavailable_branch_coverage(
    target_path: str,
    reason: str,
) -> BranchCoverageSummary:
    """Return an explicit unavailable state instead of misleading zeroes."""
    return BranchCoverageSummary(
        target_path=target_path,
        available=False,
        unavailable_reason=reason,
    )


def present_branch_coverage(summary: BranchCoverageSummary) -> dict[str, object]:
    """Convert coverage evidence into a stable API payload."""
    return {
        "target_path": summary.target_path,
        "available": summary.available,
        "existing": _present_measurement(summary.existing),
        "combined": _present_measurement(summary.combined),
        "incremental_covered_branches": summary.incremental_covered_branches,
        "untested_branches": summary.untested_branches,
        "unavailable_reason": summary.unavailable_reason,
    }


def _parse_branches(value: object) -> frozenset[Branch]:
    if not isinstance(value, list) or len(value) > MAX_BRANCHES_PER_FILE:
        raise ValueError
    branches: set[Branch] = set()
    for branch in value:
        if (
            not isinstance(branch, list)
            or len(branch) != 2
            or any(not isinstance(line, int) for line in branch)
        ):
            raise ValueError
        branches.add((branch[0], branch[1]))
    if len(branches) != len(value):
        raise ValueError
    return frozenset(branches)


def _measurement(
    covered: int,
    total: int,
) -> BranchCoverageMeasurement:
    percent = 100.0 if total == 0 else round(covered / total * 100, 1)
    return BranchCoverageMeasurement(
        covered_branches=covered,
        total_branches=total,
        percent=percent,
    )


def _present_measurement(
    measurement: BranchCoverageMeasurement | None,
) -> dict[str, object] | None:
    if measurement is None:
        return None
    return {
        "covered_branches": measurement.covered_branches,
        "total_branches": measurement.total_branches,
        "percent": measurement.percent,
    }
