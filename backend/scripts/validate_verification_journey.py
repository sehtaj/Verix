"""Validate Verix's deterministic investigation and approval journey with Docker."""

from contextlib import contextmanager
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import sys
from typing import Iterator


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
REPOSITORY_DIRECTORY = BACKEND_DIRECTORY.parent
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from models.evidence_summary import EvidenceAssessment
from models.fix_proposal import RepositoryApprovedFix, RepositoryFixProposal
from models.generated_test_report import (
    BehaviorSource,
    BehaviorSourceKind,
    GeneratedTestCase,
    GeneratedTestReport,
    TestCaseCategory,
    TestDesignStrategy,
)
from models.investigation import RepositoryOutcomeKind
from services.docker_runner import DockerTestRunner
from services.evidence_summary import build_evidence_summary
from services.repository_fix_validation import validate_repository_fix_proposal
from services.repository_investigation import (
    build_repository_investigation_evidence,
    classify_repository_outcome,
)
from services.repository_preparer import PreparedRepository
from workflows.repository_execution import RepositoryExecutionWorkflow
from workflows.repository_fix_application import RepositoryFixApplicationWorkflow
from workflows.repository_fix_verification import RepositoryFixVerificationWorkflow


CATALOG_PATH = REPOSITORY_DIRECTORY / "examples" / "python" / "catalog.json"


@dataclass(frozen=True)
class DeterministicScenario:
    """Pinned test and patch artifacts for one documented example."""

    example_id: str
    generated_tests: str
    test_names: tuple[str, str, str, str]
    patch: str
    expected_outcome: RepositoryOutcomeKind
    expected_post_existing_code: int


SCENARIOS = (
    DeterministicScenario(
        example_id="refund-boundary",
        generated_tests="""import pytest

from refunds import calculate_refund


def test_recent_purchase_receives_full_refund() -> None:
    assert calculate_refund(1_001, 10) == 1_001


def test_day_30_remains_in_full_refund_window() -> None:
    assert calculate_refund(1_001, 30) == 1_001


def test_invalid_refund_inputs_are_rejected() -> None:
    with pytest.raises(ValueError):
        calculate_refund(0, 10)
    with pytest.raises(ValueError):
        calculate_refund(1_001, -1)


def test_non_integer_refund_inputs_raise_type_error() -> None:
    with pytest.raises(TypeError):
        calculate_refund(True, 10)
    with pytest.raises(TypeError):
        calculate_refund(1_001, 10.5)
""",
        test_names=(
            "test_recent_purchase_receives_full_refund",
            "test_day_30_remains_in_full_refund_window",
            "test_invalid_refund_inputs_are_rejected",
            "test_non_integer_refund_inputs_raise_type_error",
        ),
        patch="""--- a/examples/python/refund_boundary/refunds.py
+++ b/examples/python/refund_boundary/refunds.py
@@ -17,3 +17,3 @@
     # Intentional defect: the documented full-refund window includes day 30.
-    if days_since_purchase < 30:
+    if days_since_purchase <= 30:
         return amount_cents
""",
        expected_outcome=RepositoryOutcomeKind.GENERATED_TESTS_FAILED,
        expected_post_existing_code=0,
    ),
    DeterministicScenario(
        example_id="shipping-threshold",
        generated_tests="""import pytest

from shipping import STANDARD_SHIPPING_CENTS, shipping_fee


def test_below_threshold_pays_standard_shipping() -> None:
    assert shipping_fee(4_999) == STANDARD_SHIPPING_CENTS


def test_threshold_itself_receives_free_shipping() -> None:
    assert shipping_fee(5_000) == 0


def test_negative_total_is_rejected() -> None:
    with pytest.raises(ValueError):
        shipping_fee(-1)


def test_boolean_total_raises_type_error() -> None:
    with pytest.raises(TypeError):
        shipping_fee(True)
""",
        test_names=(
            "test_below_threshold_pays_standard_shipping",
            "test_threshold_itself_receives_free_shipping",
            "test_negative_total_is_rejected",
            "test_boolean_total_raises_type_error",
        ),
        patch="""--- a/examples/python/shipping_threshold/shipping.py
+++ b/examples/python/shipping_threshold/shipping.py
@@ -15,4 +15,4 @@
     # Intentional defect: an order exactly at the threshold should be free.
-    if order_total_cents > FREE_SHIPPING_THRESHOLD_CENTS:
+    if order_total_cents >= FREE_SHIPPING_THRESHOLD_CENTS:
         return 0
     return STANDARD_SHIPPING_CENTS
""",
        expected_outcome=RepositoryOutcomeKind.EXISTING_TESTS_FAILED,
        expected_post_existing_code=0,
    ),
    DeterministicScenario(
        example_id="inventory-reservation",
        generated_tests="""import pytest

from inventory import can_reserve


def test_request_smaller_than_available_stock_succeeds() -> None:
    assert can_reserve(10, 2, 7) is True


def test_request_equal_to_available_stock_succeeds() -> None:
    assert can_reserve(10, 2, 8) is True


def test_invalid_reservation_values_are_rejected() -> None:
    with pytest.raises(ValueError):
        can_reserve(5, 6, 1)
    with pytest.raises(ValueError):
        can_reserve(5, 1, 0)


def test_boolean_reservation_value_raises_type_error() -> None:
    with pytest.raises(TypeError):
        can_reserve(True, 0, 1)
""",
        test_names=(
            "test_request_smaller_than_available_stock_succeeds",
            "test_request_equal_to_available_stock_succeeds",
            "test_invalid_reservation_values_are_rejected",
            "test_boolean_reservation_value_raises_type_error",
        ),
        patch="""--- a/examples/python/inventory_reservation/inventory.py
+++ b/examples/python/inventory_reservation/inventory.py
@@ -20,3 +20,3 @@
     available = stock - already_reserved
     # Intentional defect: requesting exactly the available stock should succeed.
-    return available > requested
+    return available >= requested
""",
        expected_outcome=RepositoryOutcomeKind.NO_EXISTING_TESTS,
        expected_post_existing_code=5,
    ),
)


class LocalCatalogPreparer:
    """Expose only a catalog fixture while production workflows make copies."""

    def __init__(self, repository_url: str, revision: str) -> None:
        self.repository_url = repository_url
        self.revision = revision

    @contextmanager
    def prepare(
        self,
        repository_url: str,
        revision: str | None = None,
        subdirectory: str | None = None,
    ) -> Iterator[PreparedRepository]:
        if repository_url != self.repository_url or revision != self.revision:
            raise ValueError("Validation must use the catalog's pinned repository.")
        if subdirectory is None:
            raise ValueError("Validation requires a catalog example subdirectory.")

        fixture_path = REPOSITORY_DIRECTORY / subdirectory
        if not fixture_path.is_dir():
            raise ValueError("Catalog example subdirectory was not found.")
        files = [path for path in fixture_path.rglob("*") if path.is_file()]
        yield PreparedRepository(
            path=fixture_path,
            file_count=len(files),
            total_bytes=sum(path.stat().st_size for path in files),
            skipped_entries=0,
        )


def load_catalog() -> dict[str, object]:
    """Load and integrity-check every pinned deterministic example."""
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    examples = catalog.get("examples")
    if not isinstance(examples, list) or not examples:
        raise RuntimeError("Deterministic example catalog is empty.")

    for example in examples:
        fixture_path = REPOSITORY_DIRECTORY / example["subdirectory"]
        for relative_path, expected_hash in example["files"].items():
            content = (fixture_path / relative_path).read_bytes()
            actual_hash = hashlib.sha256(content).hexdigest()
            if actual_hash != expected_hash:
                raise RuntimeError(
                    f"Catalog integrity failed for {example['id']}:{relative_path}."
                )
    return catalog


def build_report(
    example: dict[str, object],
    scenario: DeterministicScenario,
) -> GeneratedTestReport:
    """Create deterministic generation evidence matching the fixture contract."""
    categories = (
        TestCaseCategory.NORMAL,
        TestCaseCategory.BOUNDARY,
        TestCaseCategory.INVALID_INPUT,
        TestCaseCategory.ERROR_HANDLING,
    )
    required_cases = example["required_test_cases"]
    cases = tuple(
        GeneratedTestCase(
            test_name=test_name,
            category=category,
            strategy=TestDesignStrategy(required["strategy"]),
            expected_behavior=required["behavior"],
        )
        for test_name, category, required in zip(
            scenario.test_names,
            categories,
            required_cases,
            strict=True,
        )
    )
    behavior_source = example["behavior_source"]
    source_path = behavior_source["path"]
    source_text = (REPOSITORY_DIRECTORY / source_path).read_text(encoding="utf-8")
    return GeneratedTestReport(
        tests=scenario.generated_tests,
        sources=(
            BehaviorSource(
                kind=BehaviorSourceKind.DOCUMENTATION,
                path=source_path,
                excerpt=source_text[:1_000],
            ),
        ),
        assumptions=tuple(example["assumptions"]),
        cases=cases,
        model="deterministic-validation-artifact",
    )


def execution_result(payload: dict[str, object], key: str):
    """Convert one workflow payload into its established execution model."""
    from models.execution import TestExecutionResult

    value = payload[key]
    return TestExecutionResult(
        return_code=value["return_code"],
        output=value["output"],
        timed_out=value["timed_out"],
        skipped=value["skipped"],
    )


def validate_scenario(
    catalog: dict[str, object],
    scenario: DeterministicScenario,
    runner: DockerTestRunner,
) -> dict[str, object]:
    """Validate one full pre-fix, approval, and post-fix journey."""
    example = next(
        item for item in catalog["examples"] if item["id"] == scenario.example_id
    )
    report = build_report(example, scenario)
    preparer = LocalCatalogPreparer(catalog["repository_url"], catalog["revision"])
    execution_workflow = RepositoryExecutionWorkflow(preparer, runner)
    source_path = REPOSITORY_DIRECTORY / example["target_path"]
    original_source = source_path.read_text(encoding="utf-8")

    pre_fix = execution_workflow.run_existing_and_generated_tests(
        catalog["repository_url"],
        example["target_path"],
        report.tests,
        catalog["revision"],
        example["subdirectory"],
    )
    evidence = build_repository_investigation_evidence(
        test_runner=pre_fix["test_runner"],
        installation=execution_result(pre_fix, "installation"),
        existing_execution=execution_result(pre_fix, "existing_execution"),
        generated_execution=execution_result(pre_fix, "generated_execution"),
    )
    outcome = classify_repository_outcome(evidence)
    if outcome != scenario.expected_outcome:
        raise RuntimeError(
            f"{scenario.example_id} classified as {outcome}, expected "
            f"{scenario.expected_outcome}."
        )
    summary = build_evidence_summary(report, pre_fix)
    if summary.assessment is not EvidenceAssessment.OBSERVED_FAILURES:
        raise RuntimeError(f"{scenario.example_id} did not preserve failure evidence.")

    proposal = RepositoryFixProposal(
        revision=catalog["revision"],
        subdirectory=example["subdirectory"],
        target_path=example["target_path"],
        summary=f"Correct the documented boundary defect in {scenario.example_id}.",
        patch=scenario.patch,
    )
    validate_repository_fix_proposal(proposal, original_source)
    if not proposal.approval_required or proposal.applied:
        raise RuntimeError("Fix proposal bypassed the review-only state.")

    approved_fix = RepositoryApprovedFix(
        revision=proposal.revision,
        subdirectory=proposal.subdirectory,
        target_path=proposal.target_path,
        patch=proposal.patch,
        generated_tests=report.tests,
    )
    verification = RepositoryFixVerificationWorkflow(
        RepositoryFixApplicationWorkflow(preparer),
        runner,
    ).run(catalog["repository_url"], approved_fix)

    if verification.existing_execution.return_code != scenario.expected_post_existing_code:
        raise RuntimeError(f"{scenario.example_id} existing post-fix result was unexpected.")
    if verification.exposing_execution.return_code != 0:
        raise RuntimeError(f"{scenario.example_id} exposing test did not pass after patch.")
    if source_path.read_text(encoding="utf-8") != original_source:
        raise RuntimeError(f"{scenario.example_id} modified the source fixture.")

    coverage = pre_fix["branch_coverage"]
    return {
        "id": scenario.example_id,
        "behavior_source": report.sources[0].path,
        "generated_case_categories": [case.category.value for case in report.cases],
        "test_design_strategies": sorted({case.strategy.value for case in report.cases}),
        "pre_fix": {
            "outcome": outcome.value,
            "existing_return_code": pre_fix["existing_execution"]["return_code"],
            "generated_return_code": pre_fix["generated_execution"]["return_code"],
            "evidence_assessment": summary.assessment.value,
            "branch_coverage_available": coverage["available"],
            "incremental_covered_branches": coverage["incremental_covered_branches"],
            "untested_branches": coverage["untested_branches"],
        },
        "approval": {
            "required": proposal.approval_required,
            "explicit": approved_fix.approved,
            "github_changed": False,
        },
        "post_fix": {
            "existing_return_code": verification.existing_execution.return_code,
            "exposing_return_code": verification.exposing_execution.return_code,
            "fixture_unchanged": True,
        },
    }


def main() -> None:
    """Run every catalog scenario and print bounded machine-readable evidence."""
    catalog = load_catalog()
    runner = DockerTestRunner()
    results = [validate_scenario(catalog, scenario, runner) for scenario in SCENARIOS]
    print(
        json.dumps(
            {
                "catalog_revision": catalog["revision"],
                "validated_examples": results,
                "all_passed": True,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
