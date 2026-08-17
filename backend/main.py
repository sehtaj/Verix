"""Verix FastAPI application."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from api.presenters import (
    present_configuration_files,
    present_python_project_setup,
    present_repository_context,
    present_repository_metadata,
    present_repository_paths,
    present_repository_test_plan,
    present_repository_tree,
)
from api.schemas import GenerateTestsRequest, RepositoryRequest
from services.github_service import GitHubRepositoryService
from services.llm_service import GeminiLLMService
from services.repository_preparer import PublicRepositoryPreparer
from services.docker_runner import DockerTestRunner, GeneratedTestsValidationError
from workflows.repository_execution import RepositoryExecutionWorkflow


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

    try:
        execution = test_runner.run_tests(request.code, tests)
    except RuntimeError:
        raise HTTPException(
            status_code=502,
            detail="Unable to execute generated tests. Please try again.",
        ) from None

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

    return present_repository_metadata(repository)


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

    return present_repository_tree(tree)


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

    return {"files": present_configuration_files(files)}


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

    return present_repository_paths(paths)


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

    return present_python_project_setup(setup)


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

    return present_repository_test_plan(plan)


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

    return present_repository_context(context)


@app.post("/repository/test-run")
def run_repository_test_suite(request: RepositoryRequest) -> dict[str, object]:
    """Prepare a public Python repository and return its isolated test results."""
    try:
        workflow = RepositoryExecutionWorkflow(repository_preparer, test_runner)
        return workflow.run_existing_tests(request.url)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except RuntimeError:
        raise HTTPException(
            status_code=502,
            detail="Unable to prepare or test the repository. Please try again.",
        ) from None


@app.post("/repository/generate")
def generate_repository_test_suite(
    request: RepositoryRequest,
) -> dict[str, object]:
    """Generate repository-aware tests and return both isolated test results."""
    if llm_service is None:
        raise HTTPException(
            status_code=503,
            detail="LLM service is not configured.",
        )

    try:
        generation_context = github_repository_service.fetch_generation_context(
            request.url
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except RuntimeError:
        raise HTTPException(
            status_code=502,
            detail="Unable to fetch repository generation context. Please try again.",
        ) from None

    target_path = generation_context.selection.target_path
    if target_path is None or generation_context.source_file is None:
        raise HTTPException(
            status_code=422,
            detail="Repository has no Python source file available for test generation.",
        )

    try:
        generated_tests = llm_service.generate_repository_tests(generation_context)
        test_runner.validate_generated_tests(generated_tests)
    except GeneratedTestsValidationError:
        raise HTTPException(
            status_code=502,
            detail="Gemini returned unusable generated tests. Please try again.",
        ) from None
    except Exception:
        raise HTTPException(
            status_code=502,
            detail="Unable to generate repository tests. Please try again.",
        ) from None

    try:
        workflow = RepositoryExecutionWorkflow(repository_preparer, test_runner)
        execution_results = workflow.run_existing_and_generated_tests(
            request.url,
            target_path,
            generated_tests,
        )
    except GeneratedTestsValidationError:
        raise HTTPException(
            status_code=502,
            detail="Gemini returned unusable generated tests. Please try again.",
        ) from None
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None
    except RuntimeError:
        raise HTTPException(
            status_code=502,
            detail="Unable to prepare or test the repository. Please try again.",
        ) from None

    return {
        "target_path": target_path,
        "generated_tests": generated_tests,
        **execution_results,
    }
