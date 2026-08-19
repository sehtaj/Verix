"""Build bounded evidence for later repository-outcome investigation."""

from models.execution import TestExecutionResult
from models.investigation import (
    RepositoryCommandEvidence,
    RepositoryInvestigationEvidence,
    RepositoryOutcomeKind,
)


MAX_INVESTIGATION_OUTPUT_CHARACTERS = 2_000


def build_command_evidence(
    execution: TestExecutionResult,
) -> RepositoryCommandEvidence:
    """Keep command facts while limiting output included in investigation evidence."""
    output = execution.output
    output_truncated = len(output) > MAX_INVESTIGATION_OUTPUT_CHARACTERS

    return RepositoryCommandEvidence(
        return_code=execution.return_code,
        timed_out=execution.timed_out,
        skipped=execution.skipped,
        output_excerpt=output[:MAX_INVESTIGATION_OUTPUT_CHARACTERS],
        output_truncated=output_truncated,
    )


def build_repository_investigation_evidence(
    *,
    test_runner: str,
    installation: TestExecutionResult,
    existing_execution: TestExecutionResult,
    generated_execution: TestExecutionResult | None = None,
) -> RepositoryInvestigationEvidence:
    """Collect only bounded execution facts for one repository workflow run."""
    return RepositoryInvestigationEvidence(
        test_runner=test_runner,
        installation=build_command_evidence(installation),
        existing_execution=build_command_evidence(existing_execution),
        generated_execution=(
            build_command_evidence(generated_execution)
            if generated_execution is not None
            else None
        ),
    )


def classify_repository_outcome(
    evidence: RepositoryInvestigationEvidence,
) -> RepositoryOutcomeKind:
    """Classify one repository workflow run with fixed, explainable rules.

    A classification is deliberately derived from execution facts rather than
    inferred by the language model. This keeps the later explanation grounded
    in what the isolated runner actually observed.
    """
    installation = evidence.installation
    existing_execution = evidence.existing_execution
    generated_execution = evidence.generated_execution

    if (
        installation.timed_out
        or installation.return_code not in {0}
    ):
        return RepositoryOutcomeKind.SETUP_FAILED

    if existing_execution.timed_out:
        return RepositoryOutcomeKind.EXISTING_TESTS_TIMED_OUT

    if existing_execution.skipped or existing_execution.return_code is None:
        return RepositoryOutcomeKind.SETUP_FAILED

    # Pytest uses exit code 5 when it collects no tests. This is useful
    # information about a repository, not a failure in Verix itself.
    if existing_execution.return_code == 5:
        return RepositoryOutcomeKind.NO_EXISTING_TESTS

    if existing_execution.return_code != 0:
        return RepositoryOutcomeKind.EXISTING_TESTS_FAILED

    if generated_execution is None:
        return RepositoryOutcomeKind.TESTS_PASSED

    if generated_execution.timed_out:
        return RepositoryOutcomeKind.GENERATED_TESTS_TIMED_OUT

    if generated_execution.skipped or generated_execution.return_code is None:
        return RepositoryOutcomeKind.SETUP_FAILED

    if generated_execution.return_code != 0:
        return RepositoryOutcomeKind.GENERATED_TESTS_FAILED

    return RepositoryOutcomeKind.TESTS_PASSED
