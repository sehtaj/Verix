"""Verix FastAPI application."""

from fastapi import FastAPI


app = FastAPI(title="Verix API")


@app.get("/")
def health_check() -> dict[str, str]:
    """Confirm that the API is available."""
    return {"message": "Verix API is running"}
