"""Build a bounded, deterministic summary from generated and execution facts."""

from models.evidence_summary import EvidenceAssessment, EvidenceSummary
from models.generated_test_report import (
    GeneratedTestReport,
    TestCaseCategory,
    TestDesignStrategy,
)


DISCLAIMER = (
    "This summary describes observed evidence only. It does not prove that the "
    "selected code is error-free."
)


def build_evidence_summary(
    report: GeneratedTestReport,
    execution_results: dict[str, object],
) -> EvidenceSummary:
    """Separate passed, failed, assumed, and untested facts without an LLM."""
    passed: list[str] = []
    failed: list[str] = []
    untested: list[str] = []

    installation = _execution(execution_results, "installation")
    existing = _execution(execution_results, "existing_execution")
    generated = _execution(execution_results, "generated_execution")

    _summarize_installation(installation, passed, failed)
    _summarize_test_execution(
        "Existing repository suite",
        existing,
        passed,
        failed,
        untested,
        no_tests_is_untested=True,
    )
    _summarize_test_execution(
        "Generated focused suite",
        generated,
        passed,
        failed,
        untested,
        no_tests_is_untested=True,
    )
    _summarize_coverage(execution_results.get("branch_coverage"), passed, untested)
    _summarize_test_design(report, untested)

    assessment = (
        EvidenceAssessment.OBSERVED_FAILURES
        if failed
        else (
            EvidenceAssessment.INCOMPLETE
            if untested
            else EvidenceAssessment.NO_OBSERVED_FAILURES
        )
    )
    return EvidenceSummary(
        assessment=assessment,
        passed=tuple(passed),
        failed=tuple(failed),
        assumed=report.assumptions,
        untested=tuple(untested),
        behavior_sources=report.sources,
    )


def _execution(
    execution_results: dict[str, object],
    key: str,
) -> dict[str, object]:
    value = execution_results.get(key)
    if not isinstance(value, dict):
        raise RuntimeError("Repository execution returned invalid evidence data.")
    required = {"return_code", "timed_out", "skipped"}
    if not required.issubset(value):
        raise RuntimeError("Repository execution returned incomplete evidence data.")
    return value


def _summarize_installation(
    execution: dict[str, object],
    passed: list[str],
    failed: list[str],
) -> None:
    if execution["timed_out"]:
        failed.append("Dependency preparation timed out.")
    elif execution["return_code"] != 0:
        failed.append("Dependency preparation failed.")
    elif execution["skipped"]:
        passed.append("No dependency installation was required.")
    else:
        passed.append("Dependency preparation completed.")


def _summarize_test_execution(
    label: str,
    execution: dict[str, object],
    passed: list[str],
    failed: list[str],
    untested: list[str],
    *,
    no_tests_is_untested: bool,
) -> None:
    if execution["timed_out"]:
        failed.append(f"{label} timed out.")
    elif execution["skipped"] or execution["return_code"] is None:
        untested.append(f"{label} was not run.")
    elif execution["return_code"] == 0:
        passed.append(f"{label} passed.")
    elif execution["return_code"] == 5 and no_tests_is_untested:
        untested.append(f"{label} collected no tests.")
    else:
        failed.append(f"{label} failed with exit code {execution['return_code']}.")


def _summarize_coverage(
    value: object,
    passed: list[str],
    untested: list[str],
) -> None:
    if not isinstance(value, dict) or not isinstance(value.get("available"), bool):
        untested.append("Selected-source branch coverage was unavailable.")
        return
    if not value["available"]:
        reason = value.get("unavailable_reason")
        untested.append(
            str(reason)
            if isinstance(reason, str) and reason
            else "Selected-source branch coverage was unavailable."
        )
        return

    combined = value.get("combined")
    untested_branches = value.get("untested_branches")
    if not isinstance(combined, dict) or not isinstance(untested_branches, int):
        raise RuntimeError("Repository coverage returned invalid evidence data.")
    total = combined.get("total_branches")
    covered = combined.get("covered_branches")
    if not isinstance(total, int) or not isinstance(covered, int):
        raise RuntimeError("Repository coverage returned invalid evidence data.")
    if untested_branches:
        untested.append(
            f"{untested_branches} of {total} selected-source branches remain untested."
        )
    elif total == 0:
        passed.append("The selected source has no measurable branch destinations.")
    else:
        passed.append(f"All {covered} selected-source branches were executed.")


def _summarize_test_design(
    report: GeneratedTestReport,
    untested: list[str],
) -> None:
    categories = {case.category for case in report.cases}
    strategies = {case.strategy for case in report.cases}
    category_labels = {
        TestCaseCategory.NORMAL: "normal",
        TestCaseCategory.BOUNDARY: "boundary",
        TestCaseCategory.INVALID_INPUT: "invalid-input",
        TestCaseCategory.ERROR_HANDLING: "error-handling",
    }
    for category, label in category_labels.items():
        if category not in categories:
            untested.append(f"Generated suite contains no {label} case.")
    if TestDesignStrategy.BLACK_BOX not in strategies:
        untested.append("Generated suite contains no black-box case.")
    if TestDesignStrategy.GRAY_BOX not in strategies:
        untested.append("Generated suite contains no gray-box case.")
