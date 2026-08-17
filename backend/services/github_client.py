"""Low-level communication with GitHub's public JSON API."""

import json
import ssl
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import certifi


SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())


class GitHubApiClient:
    """Request JSON from GitHub and translate transport failures safely."""

    def request_json(self, url: str) -> dict[str, object]:
        """Return one GitHub JSON response using the existing timeout and errors."""
        request = Request(url, headers={"Accept": "application/vnd.github+json"})
        try:
            with urlopen(request, context=SSL_CONTEXT, timeout=10) as response:
                return json.load(response)
        except HTTPError as error:
            if error.code == 404:
                raise ValueError(
                    "Repository was not found or is not public."
                ) from None
            raise RuntimeError(
                "GitHub could not return repository metadata."
            ) from None
        except URLError:
            raise RuntimeError(
                "GitHub could not return repository metadata."
            ) from None
