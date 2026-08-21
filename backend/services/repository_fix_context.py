"""Select bounded, failure-focused evidence for one proposed source fix."""

from models.fix_proposal import (
    COMMIT_SHA_PATTERN,
    MAX_FIX_CONFIGURATION_FILES,
    MAX_FIX_CONTEXT_BYTES,
    MAX_FIX_RELATED_TEST_FILES,
    RepositoryFixContext,
    validate_fix_target_path,
)
from models.investigation import (
    RepositoryCommandEvidence,
    RepositoryInvestigationRun,
    RepositoryOutcomeKind,
)
from models.repository import (
    RepositoryConfigurationFile,
    RepositoryFileContent,
    RepositoryGenerationContext,
)
from services.repository_investigation import classify_repository_outcome


GENERATED_TEST_PATH = ".verix-generated-tests/test_verix_generated.py"
FIXABLE_OUTCOMES = frozenset(
    {
        RepositoryOutcomeKind.EXISTING_TESTS_TIMED_OUT,
        RepositoryOutcomeKind.EXISTING_TESTS_FAILED,
        RepositoryOutcomeKind.GENERATED_TESTS_TIMED_OUT,
        RepositoryOutcomeKind.GENERATED_TESTS_FAILED,
    }
)


def select_repository_fix_context(
    generation_context: RepositoryGenerationContext,
    investigation: RepositoryInvestigationRun,
) -> RepositoryFixContext:
    """Keep only the selected source and evidence for the observed test failure."""
    revision = generation_context.revision
    source_file = generation_context.source_file
    target_path = generation_context.selection.target_path

    if revision is None or COMMIT_SHA_PATTERN.fullmatch(revision) is None:
        raise ValueError("Repository fix context requires a pinned commit SHA.")
    if source_file is None or target_path is None:
        raise ValueError("Repository fix context requires a selected source file.")
    if source_file.path != target_path or investigation.target_path != target_path:
        raise ValueError("Repository fix context does not match the investigated target.")

    validate_fix_target_path(target_path, generation_context.subdirectory)

    if investigation.outcome not in FIXABLE_OUTCOMES:
        raise ValueError("Repository outcome does not justify a source fix proposal.")

    failure_evidence = _select_failure_evidence(investigation)
    if classify_repository_outcome(investigation.evidence) != investigation.outcome:
        raise ValueError("Repository fix context has inconsistent failure evidence.")
    explanation = investigation.explanation
    source_bytes = _file_content_bytes(source_file)
    total_bytes = (
        source_bytes
        + len(failure_evidence.output_excerpt.encode("utf-8"))
        + len(explanation.encode("utf-8"))
    )
    if total_bytes > MAX_FIX_CONTEXT_BYTES:
        raise ValueError("Required repository fix context is too large.")

    skipped_paths = list(generation_context.skipped_paths)
    selected_tests: list[RepositoryFileContent] = []

    if investigation.outcome in {
        RepositoryOutcomeKind.GENERATED_TESTS_TIMED_OUT,
        RepositoryOutcomeKind.GENERATED_TESTS_FAILED,
    }:
        generated_test = RepositoryFileContent(
            path=GENERATED_TEST_PATH,
            content=investigation.generated_tests,
            byte_count=len(investigation.generated_tests.encode("utf-8")),
        )
        total_bytes = _append_required_file(
            selected_tests,
            generated_test,
            total_bytes,
        )
    else:
        test_candidates = generation_context.test_files
        for test_file in test_candidates[:MAX_FIX_RELATED_TEST_FILES]:
            total_bytes = _append_optional_file(
                selected_tests,
                skipped_paths,
                test_file,
                total_bytes,
            )
        skipped_paths.extend(
            test.path for test in test_candidates[MAX_FIX_RELATED_TEST_FILES:]
        )

    selected_configuration_files: list[RepositoryConfigurationFile] = []
    configuration_candidates = generation_context.configuration_files
    for configuration_file in configuration_candidates[:MAX_FIX_CONFIGURATION_FILES]:
        byte_count = len(configuration_file.content.encode("utf-8"))
        if total_bytes + byte_count > MAX_FIX_CONTEXT_BYTES:
            skipped_paths.append(configuration_file.path)
            continue
        selected_configuration_files.append(configuration_file)
        total_bytes += byte_count
    skipped_paths.extend(
        file.path
        for file in configuration_candidates[MAX_FIX_CONFIGURATION_FILES:]
    )

    return RepositoryFixContext(
        revision=revision,
        subdirectory=generation_context.subdirectory,
        target_path=target_path,
        outcome=investigation.outcome,
        source_file=source_file,
        test_files=tuple(selected_tests),
        configuration_files=tuple(selected_configuration_files),
        failure_evidence=failure_evidence,
        investigation_explanation=explanation,
        skipped_paths=tuple(dict.fromkeys(skipped_paths)),
        total_bytes=total_bytes,
    )


def _select_failure_evidence(
    investigation: RepositoryInvestigationRun,
) -> RepositoryCommandEvidence:
    """Use only the command result responsible for the fixed outcome."""
    if investigation.outcome in {
        RepositoryOutcomeKind.EXISTING_TESTS_TIMED_OUT,
        RepositoryOutcomeKind.EXISTING_TESTS_FAILED,
    }:
        return investigation.evidence.existing_execution

    generated_evidence = investigation.evidence.generated_execution
    if generated_evidence is None:
        raise ValueError("Generated-test failure evidence is missing.")
    return generated_evidence


def _file_content_bytes(file: RepositoryFileContent) -> int:
    """Verify a bounded file model before using its declared size."""
    byte_count = len(file.content.encode("utf-8"))
    if file.byte_count != byte_count:
        raise ValueError("Repository fix context contains invalid file size data.")
    return byte_count


def _append_required_file(
    selected_files: list[RepositoryFileContent],
    file: RepositoryFileContent,
    total_bytes: int,
) -> int:
    """Include required failing-test content or reject an incomplete context."""
    byte_count = _file_content_bytes(file)
    if total_bytes + byte_count > MAX_FIX_CONTEXT_BYTES:
        raise ValueError("Required repository fix context is too large.")
    selected_files.append(file)
    return total_bytes + byte_count


def _append_optional_file(
    selected_files: list[RepositoryFileContent],
    skipped_paths: list[str],
    file: RepositoryFileContent,
    total_bytes: int,
) -> int:
    """Include an optional related test only when it fits the remaining budget."""
    byte_count = _file_content_bytes(file)
    if total_bytes + byte_count > MAX_FIX_CONTEXT_BYTES:
        skipped_paths.append(file.path)
        return total_bytes
    selected_files.append(file)
    return total_bytes + byte_count
