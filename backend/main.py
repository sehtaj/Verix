"""Verix FastAPI application."""

from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI(title="Verix API")


class GenerateTestsRequest(BaseModel):
    code: str


@app.get("/")
def health_check() -> dict[str, str]:
    """Confirm that the API is available."""
    return {"message": "Verix API is running"}


@app.post("/generate")
def generate_tests(request: GenerateTestsRequest) -> dict[str, str]:
    """Return the Version 0.1 placeholder test result."""
    return {"tests": "Coming soon"}
