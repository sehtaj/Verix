"""Fetch basic metadata for public GitHub repositories."""

from dataclasses import dataclass
import json
import ssl
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen

import certifi

GITHUB_API_URL = "https://api.github.com/repos"
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


class GitHubRepositoryService:
    """Retrieve metadata for a public GitHub repository."""

    def fetch_metadata(self, repository_url: str) -> RepositoryMetadata:
        """Validate a GitHub URL and return its public repository metadata."""
        owner, repository = self._parse_repository_url(repository_url)
        request = Request(
            f"{GITHUB_API_URL}/{quote(owner)}/{quote(repository)}",
            headers={"Accept": "application/vnd.github+json"},
        )

        try:
            with urlopen(request, context=SSL_CONTEXT, timeout=10) as response:
                data = json.load(response)
        except HTTPError as error:
            if error.code == 404:
                raise ValueError("Repository was not found or is not public.") from None
            raise RuntimeError("GitHub could not return repository metadata.") from None
        except URLError:
            raise RuntimeError("GitHub could not return repository metadata.") from None

        if data["private"]:
            raise ValueError("Repository is not public.")

        return RepositoryMetadata(
            name=data["name"],
            owner=data["owner"]["login"],
            description=data["description"],
            language=data["language"],
            stars=data["stargazers_count"],
            url=data["html_url"],
        )

    @staticmethod
    def _parse_repository_url(repository_url: str) -> tuple[str, str]:
        parsed_url = urlparse(repository_url)
        path_segments = [segment for segment in parsed_url.path.split("/") if segment]

        if (
            parsed_url.scheme != "https"
            or parsed_url.netloc != "github.com"
            or len(path_segments) != 2
            or parsed_url.query
            or parsed_url.fragment
        ):
            raise ValueError(
                "Enter a public GitHub repository URL, such as https://github.com/owner/repository."
            )

        return path_segments[0], path_segments[1]
