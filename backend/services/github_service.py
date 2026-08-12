"""Fetch basic metadata for public GitHub repositories."""

from dataclasses import dataclass
import json
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

import certifi

GITHUB_API_URL = "https://api.github.com/repos"
MAX_TREE_ENTRIES = 500
SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


@dataclass
class RepositoryMetadata:
    """The public repository details used by the V0.4 interface."""

    name: str
    owner: str
    description: str | None
    language: str | None
    stars: int
    url: str


@dataclass
class RepositoryTreeEntry:
    """A file or directory in a repository tree."""

    path: str
    type: str


@dataclass
class RepositoryTree:
    """The bounded repository tree returned to the V0.5 interface."""

    entries: list[RepositoryTreeEntry]
    is_truncated: bool


class GitHubRepositoryService:
    """Retrieve metadata for a public GitHub repository."""

    def fetch_metadata(self, repository_url: str) -> RepositoryMetadata:
        """Validate a GitHub URL and return its public repository metadata."""
        owner, repository = self._parse_repository_url(repository_url)
        data = self._fetch_repository_data(owner, repository)

        return RepositoryMetadata(
            name=data["name"],
            owner=data["owner"]["login"],
            description=data["description"],
            language=data["language"],
            stars=data["stargazers_count"],
            url=data["html_url"],
        )

    def fetch_file_tree(self, repository_url: str) -> RepositoryTree:
        """Return a bounded recursive tree for a public GitHub repository."""
        owner, repository = self._parse_repository_url(repository_url)
        repository_data = self._fetch_repository_data(owner, repository)
        branch = quote(repository_data["default_branch"], safe="")
        tree_data = self._request_json(
            f"{GITHUB_API_URL}/{quote(owner, safe='')}/{quote(repository, safe='')}/git/trees/{branch}?recursive=1"
        )
        tree_entries = sorted(
            tree_data["tree"],
            key=lambda entry: (entry["path"].lower(), entry["type"] != "tree"),
        )

        return RepositoryTree(
            entries=[
                RepositoryTreeEntry(path=entry["path"], type=entry["type"])
                for entry in tree_entries[:MAX_TREE_ENTRIES]
            ],
            is_truncated=tree_data["truncated"] or len(tree_entries) > MAX_TREE_ENTRIES,
        )

    def _fetch_repository_data(self, owner: str, repository: str) -> dict[str, object]:
        """Fetch repository data and reject private repositories."""
        data = self._request_json(
            f"{GITHUB_API_URL}/{quote(owner, safe='')}/{quote(repository, safe='')}"
        )

        if data["private"]:
            raise ValueError("Repository is not public.")

        return data

    @staticmethod
    def _request_json(url: str) -> dict[str, object]:
        """Request JSON from GitHub's public API with safe error messages."""
        request = Request(url, headers={"Accept": "application/vnd.github+json"})
        try:
            with urlopen(request, context=SSL_CONTEXT, timeout=10) as response:
                return json.load(response)
        except HTTPError as error:
            if error.code == 404:
                raise ValueError("Repository was not found or is not public.") from None
            raise RuntimeError("GitHub could not return repository metadata.") from None
        except URLError:
            raise RuntimeError("GitHub could not return repository metadata.") from None

    @staticmethod
    def _parse_repository_url(repository_url: str) -> tuple[str, str]:
        parsed_url = urlparse(repository_url)
        path_segments = [segment for segment in parsed_url.path.split("/") if segment]

        if (
            parsed_url.scheme != "https"
            or parsed_url.netloc.lower() not in {"github.com", "github.com:443"}
            or len(path_segments) != 2
            or parsed_url.query
            or parsed_url.fragment
        ):
            raise ValueError(
                "Enter a public GitHub repository URL, such as https://github.com/owner/repository."
            )

        return path_segments[0], path_segments[1]
