"""Convert repository domain models into the existing JSON response shapes."""

from models.investigation import RepositoryInvestigationRun

from models.repository import (
    PythonProjectSetup,
    RepositoryConfigurationFile,
    RepositoryContext,
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


def present_repository_context(context: RepositoryContext) -> dict[str, object]:
    """Return consolidated repository evidence in the existing API shape."""
    return {
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
