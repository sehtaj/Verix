"""Strict CORS origin configuration for local and hosted frontends."""

import os
from urllib.parse import urlsplit


LOCAL_FRONTEND_ORIGINS = (
    "http://localhost:3000",
    "http://127.0.0.1:3000",
)


def allowed_frontend_origins() -> list[str]:
    """Return exact trusted origins, rejecting wildcards and URL paths."""
    configured = os.getenv("VERIX_CORS_ORIGINS")
    if configured is None:
        return list(LOCAL_FRONTEND_ORIGINS)

    values = [value.strip() for value in configured.split(",")]
    if not values or any(not value for value in values):
        raise RuntimeError("VERIX_CORS_ORIGINS must contain exact HTTP origins.")

    origins: list[str] = []
    for value in values:
        try:
            parsed = urlsplit(value)
            port = parsed.port
        except ValueError:
            raise RuntimeError(
                "VERIX_CORS_ORIGINS must contain valid HTTP origins."
            ) from None
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or any(
                character.isspace() or ord(character) < 33
                for character in value
            )
            or "\\" in value
            or "%" in parsed.netloc
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
            or value == "*"
        ):
            raise RuntimeError(
                "VERIX_CORS_ORIGINS must contain exact HTTP origins without paths."
            )

        netloc = parsed.hostname
        if ":" in netloc and not netloc.startswith("["):
            netloc = f"[{netloc}]"
        if port is not None:
            netloc = f"{netloc}:{port}"
        origin = f"{parsed.scheme}://{netloc}"
        if origin not in origins:
            origins.append(origin)

    return origins
