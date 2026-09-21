"""Build the pinned E2B template used by hosted Verix execution."""

import os
from pathlib import Path

from e2b import Template, default_build_logger


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = REPOSITORY_ROOT / "backend" / "e2b.Dockerfile"
DEFAULT_ALIAS = "verix-python-runner"


def main() -> None:
    """Build one small Python runner image without embedding application secrets."""
    alias = os.getenv("E2B_TEMPLATE", DEFAULT_ALIAS).strip()
    if not alias:
        raise RuntimeError("E2B_TEMPLATE cannot be empty.")
    if not os.getenv("E2B_API_KEY", "").strip():
        raise RuntimeError("E2B_API_KEY is required to build the sandbox template.")

    os.chdir(REPOSITORY_ROOT)
    template = Template().from_dockerfile(str(DOCKERFILE))
    build = Template.build(
        template,
        alias=alias,
        cpu_count=1,
        memory_mb=512,
        on_build_logs=default_build_logger(),
    )
    print(f"Built E2B template {alias}: {build.template_id}")


if __name__ == "__main__":
    main()
