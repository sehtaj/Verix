"""Select one isolated execution provider from explicit environment config."""

import os
from typing import Callable

from services.docker_runner import DockerTestRunner
from services.e2b_runner import DEFAULT_E2B_TEMPLATE, E2BTestRunner
from services.temporary_workspaces import TemporaryWorkspaceManager
from services.test_runner import IsolatedTestRunner


def configured_test_runner(
    temporary_workspaces: TemporaryWorkspaceManager,
    *,
    docker_factory: Callable[..., IsolatedTestRunner] = DockerTestRunner,
    e2b_factory: Callable[..., IsolatedTestRunner] = E2BTestRunner,
) -> IsolatedTestRunner:
    """Default to local Docker and fail closed on invalid hosted settings."""
    backend = os.getenv("VERIX_EXECUTION_BACKEND", "docker").strip().lower()
    if backend == "docker":
        return docker_factory(temporary_workspaces=temporary_workspaces)
    if backend != "e2b":
        raise RuntimeError("VERIX_EXECUTION_BACKEND must be docker or e2b.")
    if not os.getenv("E2B_API_KEY", "").strip():
        raise RuntimeError("E2B_API_KEY is required for hosted execution.")
    template = os.getenv("E2B_TEMPLATE", DEFAULT_E2B_TEMPLATE).strip()
    if not template:
        raise RuntimeError("E2B_TEMPLATE cannot be empty.")
    return e2b_factory(
        temporary_workspaces=temporary_workspaces,
        template=template,
    )
