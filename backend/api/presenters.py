"""Convert repository domain models into the existing JSON response shapes."""

from models.fix_proposal import RepositoryFixProposalRun
from models.investigation import RepositoryInvestigationRun

from models.repository import (
    PythonProjectSetup,
    RepositoryConfigurationFile,
    RepositoryContext,
    RepositoryFileContent,
    RepositoryGenerationContext,
    RepositoryGenerationSelection,
    RepositoryMetadata,
    RepositoryPaths,
    RepositoryTestPlan,
    RepositoryTree,
)


def present_repository_metadata(repository: RepositoryMetadata) -> dict[str, object]:
    """Return the public repository metadata response."""
    return {
        "name": repository.name,
        "owner": repository.owner,
        "description": repository.description,
        "language": repository.language,
        "stars": repository.stars,
        "url": repository.url,
    }


def present_repository_tree(tree: RepositoryTree) -> dict[str, object]:
    """Return the bounded repository tree response."""
    return {
        "entries": [{"path": entry.path, "type": entry.type} for entry in tree.entries],
        "is_truncated": tree.is_truncated,
    }


def present_configuration_files(
    files: list[RepositoryConfigurationFile],
) -> list[dict[str, str]]:
    """Return configuration files without changing their order or content."""
    return [{"path": file.path, "content": file.content} for file in files]


def present_repository_paths(paths: RepositoryPaths) -> dict[str, object]:
    """Return likely Python source and test paths."""
    return {
        "source_paths": paths.source_paths,
        "test_paths": paths.test_paths,
        "is_truncated": paths.is_truncated,
    }


def present_python_project_setup(setup: PythonProjectSetup) -> dict[str, object]:
    """Return detected Python project tooling."""
    return {
        "is_python_project": setup.is_python_project,
        "project_tool": setup.project_tool,
        "test_runner": setup.test_runner,
        "configuration_files": setup.configuration_files,
    }


def present_repository_test_plan(plan: RepositoryTestPlan) -> dict[str, object]:
    """Return the structured repository test plan."""
    return {
        "setup": present_python_project_setup(plan.setup),
        "source_paths": plan.source_paths,
        "test_paths": plan.test_paths,
        "steps": [
            {
                "action": step.action,
                "description": step.description,
                "command": step.command,
            }
            for step in plan.steps
        ],
        "is_truncated": plan.is_truncated,
    }


def present_generation_selection(
    selection: RepositoryGenerationSelection,
) -> dict[str, object]:
    """Return the bounded path selection used for generation."""
    return {
        "target_path": selection.target_path,
        "related_test_paths": selection.related_test_paths,
        "configuration_paths": selection.configuration_paths,
        "is_truncated": selection.is_truncated,
    }


def present_repository_file_content(
    file: RepositoryFileContent,
) -> dict[str, object]:
    """Return one bounded repository file exactly as previewed for Gemini."""
    return {
        "path": file.path,
        "content": file.content,
        "byte_count": file.byte_count,
    }


def present_repository_generation_context(
    context: RepositoryGenerationContext,
) -> dict[str, object]:
    """Return the exact bounded repository evidence available to Gemini."""
    return {
        "revision": context.revision,
        "subdirectory": context.subdirectory,
        "selection": present_generation_selection(context.selection),
        "source_file": (
            present_repository_file_content(context.source_file)
            if context.source_file is not None
            else None
        ),
        "test_files": [
            present_repository_file_content(file) for file in context.test_files
        ],
        "configuration_files": present_configuration_files(
            context.configuration_files
        ),
        "skipped_paths": context.skipped_paths,
        "total_bytes": context.total_bytes,
    }


def present_repository_context(context: RepositoryContext) -> dict[str, object]:
    """Return consolidated repository evidence and its resolved revision."""
    return {
        "revision": context.revision,
        "subdirectory": context.subdirectory,
        "metadata": present_repository_metadata(context.metadata),
        "tree": present_repository_tree(context.tree),
        "configuration_files": present_configuration_files(
            context.configuration_files
        ),
        "test_plan": present_repository_test_plan(context.test_plan),
        "generation_selection": present_generation_selection(
            context.generation_selection
        ),
    }


def present_repository_investigation(
    investigation: RepositoryInvestigationRun,
) -> dict[str, object]:
    """Return one completed repository investigation without its raw evidence."""
    return {
        "test_plan": present_repository_test_plan(investigation.test_plan),
        "target_path": investigation.target_path,
        "generated_tests": investigation.generated_tests,
        **investigation.execution_results,
        "investigation": {
            "outcome": investigation.outcome.value,
            "explanation": investigation.explanation,
        },
    }


def present_repository_fix_proposal_run(
    run: RepositoryFixProposalRun,
) -> dict[str, object]:
    """Return one validated proposal with its completed investigation."""
    proposal = run.proposal
    return {
        **present_repository_investigation(run.investigation),
        "proposal": {
            "revision": proposal.revision,
            "subdirectory": proposal.subdirectory,
            "target_path": proposal.target_path,
            "summary": proposal.summary,
            "patch": proposal.patch,
            "validated": run.validated,
            "approval_required": proposal.approval_required,
            "applied": proposal.applied,
        },
    }
