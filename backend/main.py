"""Verix FastAPI application."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from services.github_service import GitHubRepositoryService
from services.llm_service import GeminiLLMService
from services.test_runner import DockerTestRunner


app = FastAPI(title="Verix API")

try:
    llm_service: GeminiLLMService | None = GeminiLLMService()
except RuntimeError:
    llm_service = None

test_runner = DockerTestRunner()
github_repository_service = GitHubRepositoryService()

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
