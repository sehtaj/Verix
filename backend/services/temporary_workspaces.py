"""Create and sweep only Verix-owned temporary workspace directories."""

from contextlib import contextmanager
import os
from pathlib import Path
import shutil
import tempfile
import time
from typing import Callable, Iterator


DEFAULT_STALE_WORKSPACE_SECONDS = 60 * 60
WORKSPACE_PREFIXES = (
    "pasted-code-",
    "prepared-repository-",
    "repository-run-",
)


class TemporaryWorkspaceManager:
    """Own one narrow temporary root and remove abandoned child workspaces."""

    def __init__(
        self,
        *,
        stale_after_seconds: int = DEFAULT_STALE_WORKSPACE_SECONDS,
        root: Path | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if stale_after_seconds <= 0:
            raise ValueError("Workspace stale limit must be greater than zero.")
        self.stale_after_seconds = stale_after_seconds
        self.root = root or Path(tempfile.gettempdir()) / "verix-workspaces"
        self.clock = clock

    @contextmanager
    def create(self, prefix: str) -> Iterator[Path]:
        """Yield one auto-cleaned directory after sweeping stale owned siblings."""
        if prefix not in WORKSPACE_PREFIXES:
            raise ValueError("Temporary workspace prefix is not Verix-owned.")
        self._prepare_root()
        self.cleanup_stale()
        with tempfile.TemporaryDirectory(prefix=prefix, dir=self.root) as workspace:
            yield Path(workspace)

    def cleanup_stale(self) -> int:
        """Remove old regular directories with known prefixes, never arbitrary paths."""
        self._prepare_root()
        cutoff = self.clock() - self.stale_after_seconds
        removed = 0
        for candidate in self.root.iterdir():
            if (
                candidate.is_symlink()
                or not candidate.is_dir()
                or not candidate.name.startswith(WORKSPACE_PREFIXES)
            ):
                continue
            try:
                modified_at = candidate.stat(follow_symlinks=False).st_mtime
            except FileNotFoundError:
                continue
            if modified_at > cutoff:
                continue
            try:
                shutil.rmtree(candidate)
            except FileNotFoundError:
                continue
            removed += 1
        return removed

    def _prepare_root(self) -> None:
        if self.root.is_symlink():
            raise RuntimeError("Verix temporary workspace root cannot be a symlink.")
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not self.root.is_dir():
            raise RuntimeError("Verix temporary workspace root is not a directory.")
        os.chmod(self.root, 0o700)
