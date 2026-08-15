"""Verix FastAPI application."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from services.github_service import GitHubRepositoryService
from services.llm_service import GeminiLLMService
from services.repository_preparer import PublicRepositoryPreparer
from services.test_runner import DockerTestRunner


app = FastAPI(title="Verix API")

try:
    llm_service: GeminiLLMService | None = GeminiLLMService()
except RuntimeError:
    llm_service = None

test_runner = DockerTestRunner()
github_repository_service = GitHubRepositoryService()
repository_preparer = PublicRepositoryPreparer(github_repository_service)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)


class GenerateTestsRequest(BaseModel):
    code: str = Field(min_length=1)


class RepositoryRequest(BaseModel):
    url: str = Field(min_length=1)


@app.get("/")
def health_check() -> dict[str, str]:
    """Confirm that the API is available."""
    return {"message": "Verix API is running"}


@app.post("/generate")
def generate_tests(request: GenerateTestsRequest) -> dict[str, object]:
    """Generate and execute tests for the supplied Python code."""
    if llm_service is None:
        raise HTTPException(
            status_code=503,
            detail="LLM service is not configured.",
        )

    try:
        tests = llm_service.generate_tests(request.code)
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Unable to generate tests. Please try again.",
        ) from None

    execution = test_runner.run_tests(request.code, tests)

    return {
        "tests": tests,
        "execution": {
            "return_code": execution.return_code,
            "output": execution.output,
            "timed_out": execution.timed_out,
        },
    }


@app.post("/repository")
def get_repository_metadata(request: RepositoryRequest) -> dict[str, object]:
    """Return basic metadata for a public GitHub repository."""
    try:
        repository = github_repository_service.fetch_metadata(request.url)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except RuntimeError:
        raise HTTPException(
            status_code=502,
            detail="Unable to fetch repository metadata. Please try again.",
        ) from None

    return {
        "name": repository.name,
        "owner": repository.owner,
        "description": repository.description,
        "language": repository.language,
        "stars": repository.stars,
        "url": repository.url,
    }


@app.post("/repository/tree")
def get_repository_tree(request: RepositoryRequest) -> dict[str, object]:
    """Return a bounded file tree for a public GitHub repository."""
    try:
        tree = github_repository_service.fetch_file_tree(request.url)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except RuntimeError:
        raise HTTPException(
            status_code=502,
            detail="Unable to fetch repository file structure. Please try again.",
        ) from None

    return {
        "entries": [{"path": entry.path, "type": entry.type} for entry in tree.entries],
        "is_truncated": tree.is_truncated,
    }


@app.post("/repository/configuration")
def get_repository_configuration(request: RepositoryRequest) -> dict[str, object]:
    """Return selected root-level Python configuration files from a public repository."""
    try:
        files = github_repository_service.fetch_configuration_files(request.url)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except RuntimeError:
        raise HTTPException(
            status_code=502,
            detail="Unable to fetch repository configuration files. Please try again.",
        ) from None

    return {
        "files": [{"path": file.path, "content": file.content} for file in files]
    }


@app.post("/repository/paths")
def get_repository_paths(request: RepositoryRequest) -> dict[str, object]:
    """Identify likely Python source and test paths in a public repository."""
    try:
        paths = github_repository_service.fetch_likely_paths(request.url)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except RuntimeError:
        raise HTTPException(
            status_code=502,
            detail="Unable to identify repository paths. Please try again.",
        ) from None

    return {
        "source_paths": paths.source_paths,
        "test_paths": paths.test_paths,
        "is_truncated": paths.is_truncated,
    }


@app.post("/repository/setup")
def get_repository_setup(request: RepositoryRequest) -> dict[str, object]:
    """Detect Python project setup from a public repository's configuration files."""
    try:
        setup = github_repository_service.detect_python_project_setup(request.url)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except RuntimeError:
        raise HTTPException(
            status_code=502,
            detail="Unable to detect repository setup. Please try again.",
        ) from None

    return {
        "is_python_project": setup.is_python_project,
        "project_tool": setup.project_tool,
        "test_runner": setup.test_runner,
        "configuration_files": setup.configuration_files,
    }


@app.post("/repository/test-plan")
def get_repository_test_plan(request: RepositoryRequest) -> dict[str, object]:
    """Generate an evidence-based test plan for a public repository."""
    try:
        plan = github_repository_service.generate_test_plan(request.url)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except RuntimeError:
        raise HTTPException(
            status_code=502,
            detail="Unable to generate a repository test plan. Please try again.",
        ) from None

    return {
        "setup": {
            "is_python_project": plan.setup.is_python_project,
            "project_tool": plan.setup.project_tool,
            "test_runner": plan.setup.test_runner,
            "configuration_files": plan.setup.configuration_files,
        },
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


@app.post("/repository/context")
def get_repository_context(request: RepositoryRequest) -> dict[str, object]:
    """Return shared repository evidence and its derived test plan."""
    try:
        context = github_repository_service.fetch_context(request.url)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except RuntimeError:
        raise HTTPException(
            status_code=502,
            detail="Unable to fetch repository context. Please try again.",
        ) from None

    return {
        "metadata": {
            "name": context.metadata.name,
            "owner": context.metadata.owner,
            "description": context.metadata.description,
            "language": context.metadata.language,
            "stars": context.metadata.stars,
            "url": context.metadata.url,
        },
        "tree": {
            "entries": [
                {"path": entry.path, "type": entry.type}
                for entry in context.tree.entries
            ],
            "is_truncated": context.tree.is_truncated,
        },
        "configuration_files": [
            {"path": file.path, "content": file.content}
            for file in context.configuration_files
        ],
        "test_plan": {
            "setup": {
                "is_python_project": context.test_plan.setup.is_python_project,
                "project_tool": context.test_plan.setup.project_tool,
                "test_runner": context.test_plan.setup.test_runner,
                "configuration_files": context.test_plan.setup.configuration_files,
            },
            "source_paths": context.test_plan.source_paths,
            "test_paths": context.test_plan.test_paths,
            "steps": [
                {
                    "action": step.action,
                    "description": step.description,
                    "command": step.command,
                }
                for step in context.test_plan.steps
            ],
            "is_truncated": context.test_plan.is_truncated,
        },
    }


@app.post("/repository/test-run")
def run_repository_test_suite(request: RepositoryRequest) -> dict[str, object]:
    """Prepare a public Python repository and return its isolated test results."""
    try:
        with repository_preparer.prepare(request.url) as prepared_repository:
            preparation = {
                "file_count": prepared_repository.file_count,
                "total_bytes": prepared_repository.total_bytes,
                "skipped_entries": prepared_repository.skipped_entries,
            }
            with test_runner.repository_workspace(
                prepared_repository.path
            ) as workspace_path:
                selected_runner = test_runner.select_repository_test_runner(
                    workspace_path
                )
                installation = test_runner.install_repository_dependencies(
                    workspace_path
                )

                if installation.return_code != 0 or installation.timed_out:
                    execution = {
                        "return_code": None,
                        "output": (
                            "Repository tests were not run because dependency "
                            "installation failed."
                        ),
                        "timed_out": False,
                        "skipped": True,
                    }
                else:
                    test_execution = test_runner.run_repository_tests(
                        workspace_path, selected_runner
                    )
                    execution = {
                        "return_code": test_execution.return_code,
                        "output": test_execution.output,
                        "timed_out": test_execution.timed_out,
                        "skipped": False,
                    }
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except RuntimeError:
        raise HTTPException(
            status_code=502,
            detail="Unable to prepare or test the repository. Please try again.",
        ) from None

    return {
        "preparation": preparation,
        "installation": {
            "return_code": installation.return_code,
            "output": installation.output,
            "timed_out": installation.timed_out,
            "skipped": installation.skipped,
        },
        "test_runner": selected_runner,
        "execution": execution,
    }
