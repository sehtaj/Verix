"""Verix FastAPI application."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


app = FastAPI(title="Verix API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)


class GenerateTestsRequest(BaseModel):
    code: str = Field(min_length=1)


@app.get("/")
def health_check() -> dict[str, str]:
    """Confirm that the API is available."""
    return {"message": "Verix API is running"}


@app.post("/generate")
def generate_tests(request: GenerateTestsRequest) -> dict[str, str]:
    """Return the Version 0.1 placeholder test result."""
    return {"tests": "Coming soon"}
