"""Load the backend's ignored local environment file consistently."""

from pathlib import Path

from dotenv import load_dotenv


BACKEND_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


def load_backend_environment() -> None:
    """Load local development values without overriding host configuration."""
    load_dotenv(BACKEND_ENV_FILE)
