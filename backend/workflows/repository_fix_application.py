"""Apply one approved repository fix only inside a disposable workspace."""

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterator

from models.fix_proposal import RepositoryApprovedFix
from services.repository_fix_validation import apply_repository_fix_patch
from services.repository_preparer import PublicRepositoryPreparer
from services.repository_workspace import RepositoryWorkspaceManager


@dataclass(frozen=True)
class AppliedRepositoryFixWorkspace:
    """One temporary workspace containing an approved, validated source change."""

    path: Path
    target_path: str


class RepositoryFixApplicationWorkflow:
    """Prepare one pinned repository and patch only its disposable copy."""

    def __init__(
        self,
        repository_preparer: PublicRepositoryPreparer,
        workspace_manager: RepositoryWorkspaceManager | None = None,
    ) -> None:
        self.repository_preparer = repository_preparer
        self.workspace_manager = workspace_manager or RepositoryWorkspaceManager()

    @contextmanager
    def apply(
        self,
        repository_url: str,
        approved_fix: RepositoryApprovedFix,
    ) -> Iterator[AppliedRepositoryFixWorkspace]:
        """Yield one patched temporary copy, then remove it without host writes."""
        with self.repository_preparer.prepare(
            repository_url,
            approved_fix.revision,
            approved_fix.subdirectory,
        ) as prepared_repository:
            with self.workspace_manager.create(prepared_repository.path) as workspace:
                project_target_path = self._project_target_path(
                    approved_fix.target_path,
                    approved_fix.subdirectory,
                )
                target_file = self._target_file(
                    workspace,
                    project_target_path,
                )
                try:
                    source_content = target_file.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    raise ValueError("Repository fix target must be UTF-8 source.") from None

                patched_content = apply_repository_fix_patch(
                    target_path=approved_fix.target_path,
                    patch=approved_fix.patch,
                    source_content=source_content,
                )
                target_file.write_text(patched_content, encoding="utf-8")
                yield AppliedRepositoryFixWorkspace(
                    path=workspace,
                    target_path=project_target_path,
                )

    @staticmethod
    def _project_target_path(
        target_path: str,
        subdirectory: str | None,
    ) -> str:
        """Translate a repository path into the selected project workspace."""
        relative_target = PurePosixPath(target_path)
        if subdirectory is not None:
            try:
                relative_target = relative_target.relative_to(
                    PurePosixPath(subdirectory)
                )
            except ValueError:
                raise ValueError(
                    "Repository fix target is outside the selected subdirectory."
                ) from None
        if not relative_target.parts:
            raise ValueError("Repository fix target is invalid.")
        return relative_target.as_posix()

    @staticmethod
    def _target_file(workspace: Path, target_path: str) -> Path:
        """Resolve the selected project target inside the temporary copy only."""
        relative_target = PurePosixPath(target_path)
        target_file = workspace.joinpath(*relative_target.parts)
        current_path = workspace
        for part in relative_target.parts:
            current_path /= part
            if current_path.is_symlink():
                raise ValueError("Repository fix target cannot use symbolic links.")
        if not target_file.is_file():
            raise ValueError("Repository fix target does not exist in the prepared copy.")
        return target_file
