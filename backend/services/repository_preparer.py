"""Safely prepare public Python repository files in a temporary workspace."""

from contextlib import contextmanager
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path, PurePosixPath
import shutil
import tarfile
import tempfile
from typing import Iterator
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from services.github_service import (
    CONFIGURATION_FILENAMES,
    SSL_CONTEXT,
    GitHubRepositoryService,
)


MAX_ARCHIVE_BYTES = 25 * 1024 * 1024
MAX_EXTRACTED_BYTES = 100 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 10_000
DOWNLOAD_TIMEOUT_SECONDS = 30
DOWNLOAD_CHUNK_BYTES = 64 * 1024


@dataclass(frozen=True)
class PreparedRepository:
    """A temporary, validated Python repository ready for isolated use."""

    path: Path
    file_count: int
    total_bytes: int
    skipped_entries: int


class PublicRepositoryPreparer:
    """Download and safely unpack a public Python repository archive."""

    def __init__(
        self, github_service: GitHubRepositoryService | None = None
    ) -> None:
        self.github_service = github_service or GitHubRepositoryService()

    @contextmanager
    def prepare(
        self, repository_url: str, revision: str | None = None
    ) -> Iterator[PreparedRepository]:
        """Yield a temporary repository directory and remove it after use."""
        archive_reference = self.github_service.fetch_archive_reference(
            repository_url, revision
        )
        archive_data = self._download_archive(archive_reference.url)

        with tempfile.TemporaryDirectory(prefix="verix-repository-") as workspace:
            repository_path = Path(workspace) / "repository"
            repository_path.mkdir()
            file_count, total_bytes, skipped_entries = self._extract_archive(
                archive_data, repository_path
            )
            self._validate_python_project(repository_path)

            yield PreparedRepository(
                path=repository_path,
                file_count=file_count,
                total_bytes=total_bytes,
                skipped_entries=skipped_entries,
            )

    @staticmethod
    def _download_archive(url: str) -> bytes:
        """Download a repository archive without exceeding the compressed-size limit."""
        request = Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "Verix",
            },
        )

        try:
            with urlopen(
                request,
                context=SSL_CONTEXT,
                timeout=DOWNLOAD_TIMEOUT_SECONDS,
            ) as response:
                content_length = response.headers.get("Content-Length")
                if (
                    content_length
                    and content_length.isdigit()
                    and int(content_length) > MAX_ARCHIVE_BYTES
                ):
                    raise ValueError("Repository archive is too large to prepare.")

                chunks = []
                downloaded_bytes = 0
                while chunk := response.read(DOWNLOAD_CHUNK_BYTES):
                    downloaded_bytes += len(chunk)
                    if downloaded_bytes > MAX_ARCHIVE_BYTES:
                        raise ValueError("Repository archive is too large to prepare.")
                    chunks.append(chunk)

                return b"".join(chunks)
        except ValueError:
            raise
        except HTTPError as error:
            if error.code == 404:
                raise ValueError(
                    "Repository archive was not found or is not public."
                ) from None
            raise RuntimeError("GitHub could not return the repository archive.") from None
        except (URLError, TimeoutError):
            raise RuntimeError("GitHub could not return the repository archive.") from None

    @staticmethod
    def _extract_archive(
        archive_data: bytes, repository_path: Path
    ) -> tuple[int, int, int]:
        """Extract regular files while enforcing path, type, count, and size limits."""
        archive_root: str | None = None
        seen_paths: set[Path] = set()
        entry_count = 0
        file_count = 0
        total_bytes = 0
        skipped_entries = 0

        try:
            with tarfile.open(fileobj=BytesIO(archive_data), mode="r:gz") as archive:
                for member in archive:
                    entry_count += 1
                    if entry_count > MAX_ARCHIVE_ENTRIES:
                        raise ValueError(
                            "Repository archive contains too many entries to prepare."
                        )

                    member_path = PurePosixPath(member.name)
                    if member_path.is_absolute() or ".." in member_path.parts:
                        raise ValueError("Repository archive contains an unsafe path.")

                    path_parts = member_path.parts
                    if not path_parts:
                        continue

                    if archive_root is None:
                        archive_root = path_parts[0]
                    elif path_parts[0] != archive_root:
                        raise ValueError(
                            "Repository archive has an unexpected directory layout."
                        )

                    relative_parts = path_parts[1:]
                    if not relative_parts:
                        if not member.isdir():
                            raise ValueError(
                                "Repository archive has an unexpected directory layout."
                            )
                        continue

                    target_path = repository_path.joinpath(*relative_parts)
                    if target_path in seen_paths:
                        raise ValueError(
                            "Repository archive contains duplicate file paths."
                        )
                    seen_paths.add(target_path)

                    if member.isdir():
                        target_path.mkdir(parents=True, exist_ok=True)
                        continue

                    if not member.isreg():
                        skipped_entries += 1
                        continue

                    file_count += 1
                    total_bytes += member.size
                    if total_bytes > MAX_EXTRACTED_BYTES:
                        raise ValueError(
                            "Repository archive is too large after extraction."
                        )

                    source = archive.extractfile(member)
                    if source is None:
                        raise RuntimeError("Repository archive could not be extracted.")

                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    with source, target_path.open("wb") as destination:
                        shutil.copyfileobj(source, destination)
        except ValueError:
            raise
        except (OSError, tarfile.TarError):
            raise RuntimeError("Repository archive could not be extracted.") from None

        if archive_root is None or file_count == 0:
            raise ValueError("Repository archive does not contain any files.")

        return file_count, total_bytes, skipped_entries

    @staticmethod
    def _validate_python_project(repository_path: Path) -> None:
        """Require Python source or recognized root-level Python configuration."""
        has_python_source = any(
            path.is_file() for path in repository_path.rglob("*.py")
        )
        has_python_configuration = any(
            (repository_path / filename).is_file()
            for filename in CONFIGURATION_FILENAMES
        )

        if not has_python_source and not has_python_configuration:
            raise ValueError("Repository does not appear to be a Python project.")
