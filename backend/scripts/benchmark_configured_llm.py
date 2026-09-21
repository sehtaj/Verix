"""Benchmark the configured LLM against Verix's pinned Python examples."""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
REPOSITORY_DIRECTORY = BACKEND_DIRECTORY.parent
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from models.fix_proposal import RepositoryFixProposal
from models.generated_test_report import GeneratedTestReport
from models.investigation import RepositoryInvestigationRun, RepositoryOutcomeKind
from models.repository import (
    RepositoryConfigurationFile,
    RepositoryFileContent,
    RepositoryGenerationContext,
    RepositoryGenerationSelection,
    RepositoryPaths,
    RepositoryTestPlan,
)
from scripts.validate_recruiter_journey import (
    LocalCatalogPreparer,
    SCENARIOS,
    load_catalog,
)
from services.docker_runner import DockerTestRunner
from services.llm_service import GeminiLLMService, MODEL_NAME
from services.repository_analyzer import CONFIGURATION_FILENAMES, RepositoryAnalyzer
from services.repository_fix_context import (
    FIXABLE_OUTCOMES,
    select_repository_fix_context,
)
from services.repository_fix_validation import (
    apply_repository_fix_patch,
    validate_repository_fix_proposal,
)
from services.repository_investigation import (
    build_repository_investigation_evidence,
    classify_repository_outcome,
)
from workflows.repository_execution import RepositoryExecutionWorkflow


def build_generation_context(
    catalog: dict[str, object],
    example: dict[str, object],
) -> RepositoryGenerationContext:
    """Build the exact bounded context shape used by production prompting."""
    fixture_path = REPOSITORY_DIRECTORY / example["subdirectory"]
    source_path = REPOSITORY_DIRECTORY / example["target_path"]
    source_file = _file_content(example["target_path"], source_path)

    test_files = [
        _file_content(
            f"{example['subdirectory']}/{relative_path}",
            fixture_path / relative_path,
        )
        for relative_path in example["files"]
        if relative_path.startswith("tests/") and relative_path.endswith(".py")
    ]
    configuration_files = [
        RepositoryConfigurationFile(
            path=f"{example['subdirectory']}/{relative_path}",
            content=(fixture_path / relative_path).read_text(encoding="utf-8"),
        )
        for relative_path in example["files"]
        if PurePosixPath(relative_path).name in CONFIGURATION_FILENAMES
    ]
    documentation_path = example["behavior_source"]["path"]
    documentation_files = [
        _file_content(
            documentation_path,
            REPOSITORY_DIRECTORY / documentation_path,
        )
    ]
    paths = RepositoryPaths(
        source_paths=[example["target_path"]],
        test_paths=[file.path for file in test_files],
        is_truncated=False,
    )
    setup = RepositoryAnalyzer.detect_python_project_setup(configuration_files)
    test_plan = RepositoryTestPlan(
        setup=setup,
        source_paths=paths.source_paths,
        test_paths=paths.test_paths,
        steps=RepositoryAnalyzer.build_test_plan_steps(setup, paths),
        is_truncated=False,
    )
    selected_files = [source_file, *test_files, *documentation_files]
    total_bytes = sum(file.byte_count for file in selected_files) + sum(
        len(file.content.encode("utf-8")) for file in configuration_files
    )
    return RepositoryGenerationContext(
        selection=RepositoryGenerationSelection(
            target_path=example["target_path"],
            related_test_paths=[file.path for file in test_files],
            configuration_paths=[file.path for file in configuration_files],
            documentation_paths=[documentation_path],
            is_truncated=False,
        ),
        source_file=source_file,
        test_files=test_files,
        configuration_files=configuration_files,
        documentation_files=documentation_files,
        skipped_paths=[],
        total_bytes=total_bytes,
        revision=catalog["revision"],
        test_plan=test_plan,
        subdirectory=example["subdirectory"],
    )


def evaluate_report(
    example: dict[str, object],
    report: GeneratedTestReport,
) -> dict[str, object]:
    """Compare structured generation metadata with the catalog requirements."""
    required_categories = {
        case["category"] for case in example["required_test_cases"]
    }
    required_strategies = {
        case["strategy"] for case in example["required_test_cases"]
    }
    observed_categories = {case.category.value for case in report.cases}
    observed_strategies = {case.strategy.value for case in report.cases}
    source_paths = {source.path for source in report.sources}
    expected_assumptions = tuple(example["assumptions"])
    return {
        "required_categories": sorted(required_categories),
        "observed_categories": sorted(observed_categories),
        "categories_met": required_categories.issubset(observed_categories),
        "required_strategies": sorted(required_strategies),
        "observed_strategies": sorted(observed_strategies),
        "strategies_met": required_strategies.issubset(observed_strategies),
        "documentation_source_cited": (
            example["behavior_source"]["path"] in source_paths
        ),
        "assumptions": list(report.assumptions),
        "assumptions_match_catalog": report.assumptions == expected_assumptions,
        "generated_test_sha256": hashlib.sha256(
            report.tests.encode("utf-8")
        ).hexdigest(),
    }


def run_benchmark(example_ids: set[str] | None = None) -> dict[str, object]:
    """Call Gemini a bounded number of times and collect reproducible evidence."""
    catalog = load_catalog()
    examples = {example["id"]: example for example in catalog["examples"]}
    scenarios = {scenario.example_id: scenario for scenario in SCENARIOS}
    preparer = LocalCatalogPreparer(catalog["repository_url"], catalog["revision"])
    runner = DockerTestRunner()
    execution_workflow = RepositoryExecutionWorkflow(preparer, runner)
    llm = GeminiLLMService()
    results = []
    llm_calls_attempted = 0

    for example_id, example in examples.items():
        if example_ids is not None and example_id not in example_ids:
            continue
        scenario = scenarios[example_id]
        context = build_generation_context(catalog, example)
        llm_calls_attempted += 1
        try:
            report = llm.generate_repository_test_report(context)
        except (RuntimeError, ValueError) as error:
            validation_reason = getattr(error, "reason", None)
            results.append(
                {
                    "id": example_id,
                    "model": MODEL_NAME,
                    "generation": {
                        "valid": False,
                        "error": str(error),
                        **(
                            {"validation_reason": validation_reason}
                            if validation_reason is not None
                            else {}
                        ),
                    },
                    "execution": {"attempted": False},
                    "investigation": {"attempted": False},
                    "proposal": {
                        "attempted": False,
                        "reason": "Generation did not produce a valid report.",
                        "applied": False,
                    },
                }
            )
            continue
        execution_results = execution_workflow.run_existing_and_generated_tests(
            catalog["repository_url"],
            example["target_path"],
            report.tests,
            catalog["revision"],
            example["subdirectory"],
        )
        evidence = build_repository_investigation_evidence(
            test_runner=execution_results["test_runner"],
            installation=_execution_result(execution_results["installation"]),
            existing_execution=_execution_result(
                execution_results["existing_execution"]
            ),
            generated_execution=_execution_result(
                execution_results["generated_execution"]
            ),
        )
        outcome = classify_repository_outcome(evidence)
        llm_calls_attempted += 1
        explanation = llm.generate_repository_investigation(
            outcome=outcome,
            evidence=evidence,
        )
        investigation = RepositoryInvestigationRun(
            test_plan=context.test_plan,
            target_path=example["target_path"],
            generated_tests=report.tests,
            generated_test_report=report,
            execution_results=execution_results,
            evidence=evidence,
            outcome=outcome,
            explanation=explanation,
            generation_context=context,
        )

        corrected_results = _run_against_known_correction(
            example,
            scenario.patch,
            report.tests,
            runner,
        )
        if outcome in FIXABLE_OUTCOMES:
            llm_calls_attempted += 1
        proposal_result = _evaluate_proposal(llm, context, investigation)
        expected_outcome = scenario.expected_outcome
        generated_execution = execution_results["generated_execution"]
        report_evaluation = evaluate_report(example, report)
        defect_exposed = (
            generated_execution["return_code"] not in {None, 0, 5}
            and not generated_execution["timed_out"]
            and corrected_results["generated_return_code"] == 0
        )
        results.append(
            {
                "id": example_id,
                "model": report.model,
                "generation": report_evaluation,
                "execution": {
                    "existing_return_code": execution_results[
                        "existing_execution"
                    ]["return_code"],
                    "generated_return_code": generated_execution["return_code"],
                    "outcome": outcome.value,
                    "expected_outcome": expected_outcome.value,
                    "outcome_matches_catalog": outcome == expected_outcome,
                    "generated_suite_passes_known_correction": corrected_results[
                        "generated_return_code"
                    ]
                    == 0,
                    "defect_exposed": defect_exposed,
                },
                "investigation": {
                    "explanation": explanation,
                    "bounded": 0 < len(explanation) <= 4_000,
                    "mentions_relevant_result": _mentions_relevant_result(
                        explanation,
                        outcome,
                    ),
                },
                "proposal": proposal_result,
            }
        )

    return {
        "model": MODEL_NAME,
        "catalog_revision": catalog["revision"],
        "llm_calls_attempted": llm_calls_attempted,
        "results": results,
        "summary": _summarize(results),
    }


def run_generation_probe(example_id: str) -> dict[str, object]:
    """Make exactly one configured-model call for one disclosed example."""
    catalog = load_catalog()
    examples = {example["id"]: example for example in catalog["examples"]}
    example = examples[example_id]
    context = build_generation_context(catalog, example)
    llm = GeminiLLMService()

    try:
        report = llm.generate_repository_test_report(context)
    except (RuntimeError, ValueError) as error:
        validation_reason = getattr(error, "reason", None)
        generation = {
            "valid": False,
            "error": str(error),
            **(
                {"validation_reason": validation_reason}
                if validation_reason is not None
                else {}
            ),
        }
    else:
        generation = evaluate_report(example, report)

    return {
        "mode": "generation_probe",
        "model": MODEL_NAME,
        "catalog_revision": catalog["revision"],
        "llm_calls_attempted": 1,
        "result": {
            "id": example_id,
            "generation": generation,
            "execution": {"attempted": False},
            "investigation": {"attempted": False},
            "proposal": {"attempted": False, "applied": False},
        },
    }


def build_dry_run_manifest(
    example_ids: set[str] | None = None,
    *,
    generation_only: bool = False,
) -> dict[str, object]:
    """Describe the external payload and call ceiling without contacting Gemini."""
    catalog = load_catalog()
    scenarios = {scenario.example_id: scenario for scenario in SCENARIOS}
    examples = []
    total_calls = 0
    total_bytes = 0
    for example in catalog["examples"]:
        if example_ids is not None and example["id"] not in example_ids:
            continue
        context = build_generation_context(catalog, example)
        files = [
            context.source_file,
            *context.test_files,
            *context.documentation_files,
        ]
        file_manifest = [
            {"path": file.path, "bytes": file.byte_count}
            for file in files
            if file is not None
        ]
        file_manifest.extend(
            {
                "path": file.path,
                "bytes": len(file.content.encode("utf-8")),
            }
            for file in context.configuration_files
        )
        example_bytes = sum(file["bytes"] for file in file_manifest)
        expected_outcome = scenarios[example["id"]].expected_outcome
        planned_calls = (
            1
            if generation_only
            else 3 if expected_outcome in FIXABLE_OUTCOMES else 2
        )
        total_calls += planned_calls
        total_bytes += example_bytes
        examples.append(
            {
                "id": example["id"],
                "files": file_manifest,
                "context_bytes": example_bytes,
                "maximum_llm_calls": planned_calls,
            }
        )
    return {
        "dry_run": True,
        "destination": "Configured Google Gemini API",
        "model": MODEL_NAME,
        "catalog_revision": catalog["revision"],
        "examples": examples,
        "total_context_bytes": total_bytes,
        "maximum_llm_calls": total_calls,
        "generation_only": generation_only,
        "secrets_included": False,
        "patches_auto_approved_or_applied": False,
    }


def _run_against_known_correction(
    example: dict[str, object],
    patch: str,
    generated_tests: str,
    runner: DockerTestRunner,
) -> dict[str, int | None]:
    """Check generated tests against the catalog correction in a disposable copy."""
    fixture_path = REPOSITORY_DIRECTORY / example["subdirectory"]
    project_target = PurePosixPath(example["target_path"]).relative_to(
        example["subdirectory"]
    ).as_posix()
    with runner.repository_workspace(fixture_path) as workspace:
        target = workspace.joinpath(*PurePosixPath(project_target).parts)
        source = target.read_text(encoding="utf-8")
        target.write_text(
            apply_repository_fix_patch(
                target_path=example["target_path"],
                patch=patch,
                source_content=source,
            ),
            encoding="utf-8",
        )
        selected_runner = runner.select_repository_test_runner(workspace)
        installation = runner.install_repository_dependencies(workspace)
        if installation.return_code != 0 or installation.timed_out:
            return {"existing_return_code": None, "generated_return_code": None}
        results = runner.run_repository_test_sets(
            workspace,
            project_target,
            generated_tests,
            selected_runner,
        )
        return {
            "existing_return_code": results.existing.return_code,
            "generated_return_code": results.generated.return_code,
        }


def _evaluate_proposal(
    llm: GeminiLLMService,
    context: RepositoryGenerationContext,
    investigation: RepositoryInvestigationRun,
) -> dict[str, object]:
    """Validate a review-only proposal without approving or applying it."""
    if investigation.outcome not in FIXABLE_OUTCOMES:
        return {
            "attempted": False,
            "reason": "The current outcome policy does not permit a fix proposal.",
            "structurally_valid": False,
            "applied": False,
        }

    try:
        fix_context = select_repository_fix_context(context, investigation)
        proposal = llm.generate_repository_fix_proposal(fix_context)
        validate_repository_fix_proposal(
            proposal,
            fix_context.source_file.content,
        )
    except (RuntimeError, ValueError) as error:
        return {
            "attempted": True,
            "structurally_valid": False,
            "error": str(error),
            "applied": False,
        }

    return _present_proposal(proposal)


def _present_proposal(proposal: RepositoryFixProposal) -> dict[str, object]:
    return {
        "attempted": True,
        "structurally_valid": True,
        "summary": proposal.summary,
        "patch": proposal.patch,
        "approval_required": proposal.approval_required,
        "applied": proposal.applied,
    }


def _mentions_relevant_result(
    explanation: str,
    outcome: RepositoryOutcomeKind,
) -> bool:
    normalized = explanation.lower()
    if outcome == RepositoryOutcomeKind.GENERATED_TESTS_FAILED:
        return "generated" in normalized and "fail" in normalized
    if outcome == RepositoryOutcomeKind.EXISTING_TESTS_FAILED:
        return "existing" in normalized and "fail" in normalized
    if outcome == RepositoryOutcomeKind.NO_EXISTING_TESTS:
        return (
            "no existing" in normalized
            or "no tests" in normalized
            or "collected no" in normalized
        )
    return outcome.value.replace("_", " ") in normalized


def _summarize(results: list[dict[str, object]]) -> dict[str, object]:
    generation_passes = sum(
        result["generation"].get("valid", True)
        and all(
            (
                result["generation"]["categories_met"],
                result["generation"]["strategies_met"],
                result["generation"]["documentation_source_cited"],
                result["execution"]["defect_exposed"],
            )
        )
        for result in results
    )
    valid_proposals = sum(
        result["proposal"].get("structurally_valid", False) for result in results
    )
    return {
        "examples": len(results),
        "generation_and_exposure_passes": generation_passes,
        "investigation_checks_passed": sum(
            result["investigation"].get("bounded", False)
            and result["investigation"].get("mentions_relevant_result", False)
            for result in results
        ),
        "structurally_valid_review_only_proposals": valid_proposals,
        "proposal_attempts": sum(
            result["proposal"]["attempted"] for result in results
        ),
    }


def _file_content(path: str, filesystem_path: Path) -> RepositoryFileContent:
    content = filesystem_path.read_text(encoding="utf-8")
    return RepositoryFileContent(
        path=path,
        content=content,
        byte_count=len(content.encode("utf-8")),
    )


def _execution_result(payload: dict[str, object]):
    from models.execution import TestExecutionResult

    return TestExecutionResult(
        return_code=payload["return_code"],
        output=payload["output"],
        timed_out=payload["timed_out"],
        skipped=payload["skipped"],
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the external payload manifest without contacting Gemini.",
    )
    parser.add_argument(
        "--example",
        action="append",
        choices=[scenario.example_id for scenario in SCENARIOS],
        help="Benchmark only the selected example; repeat to select several.",
    )
    parser.add_argument(
        "--generation-only",
        action="store_true",
        help=(
            "Make exactly one generation call for one selected example; do not "
            "run Docker, investigation, or proposal evaluation."
        ),
    )
    arguments = parser.parse_args()
    example_ids = set(arguments.example) if arguments.example else None
    if arguments.generation_only and (
        arguments.example is None or len(arguments.example) != 1
    ):
        parser.error("--generation-only requires exactly one --example")
    if arguments.dry_run:
        result = build_dry_run_manifest(
            example_ids,
            generation_only=arguments.generation_only,
        )
    elif arguments.generation_only:
        result = run_generation_probe(arguments.example[0])
    else:
        result = run_benchmark(example_ids)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
