"""Regression tests for GitHub transport behavior and service delegation."""

from io import BytesIO
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from services.github_client import GitHubApiClient
from services.github_service import GitHubRepositoryService


class GitHubApiClientTests(unittest.TestCase):
    """Protect the existing GitHub request and error contract."""

    def test_request_json_returns_decoded_response(self) -> None:
        response = BytesIO(b'{"name": "sample"}')

        with patch("services.github_client.urlopen", return_value=response) as open_url:
            result = GitHubApiClient().request_json(
                "https://api.github.com/repos/example/sample"
            )

        self.assertEqual(result, {"name": "sample"})
        request = open_url.call_args.args[0]
        self.assertEqual(request.get_header("Accept"), "application/vnd.github+json")
        self.assertEqual(open_url.call_args.kwargs["timeout"], 10)

    def test_request_json_maps_not_found_to_validation_error(self) -> None:
        error = HTTPError("https://api.github.com", 404, "Not Found", {}, None)

        with patch("services.github_client.urlopen", side_effect=error):
            with self.assertRaisesRegex(
                ValueError, "Repository was not found or is not public"
            ):
                GitHubApiClient().request_json("https://api.github.com")

    def test_request_json_hides_other_http_failures(self) -> None:
        error = HTTPError("https://api.github.com", 500, "Failure", {}, None)

        with patch("services.github_client.urlopen", side_effect=error):
            with self.assertRaisesRegex(
                RuntimeError, "GitHub could not return repository metadata"
            ):
                GitHubApiClient().request_json("https://api.github.com")

    def test_request_json_hides_network_failures(self) -> None:
        with patch(
            "services.github_client.urlopen", side_effect=URLError("offline")
        ):
            with self.assertRaisesRegex(
                RuntimeError, "GitHub could not return repository metadata"
            ):
                GitHubApiClient().request_json("https://api.github.com")

    def test_request_json_hides_socket_timeouts(self) -> None:
        with patch("services.github_client.urlopen", side_effect=TimeoutError):
            with self.assertRaisesRegex(
                RuntimeError, "GitHub could not return repository metadata"
            ):
                GitHubApiClient().request_json("https://api.github.com")


class GitHubRepositoryServiceClientTests(unittest.TestCase):
    """Protect the boundary between repository analysis and HTTP transport."""

    def test_metadata_uses_injected_client(self) -> None:
        client = Mock()
        client.request_json.return_value = {
            "name": "sample",
            "owner": {"login": "example"},
            "description": "Sample repository",
            "language": "Python",
            "stargazers_count": 7,
            "html_url": "https://github.com/example/sample",
            "private": False,
        }
        service = GitHubRepositoryService(client=client)

        metadata = service.fetch_metadata("https://github.com/example/sample")

        client.request_json.assert_called_once_with(
            "https://api.github.com/repos/example/sample"
        )
        self.assertEqual(metadata.name, "sample")
        self.assertEqual(metadata.owner, "example")
