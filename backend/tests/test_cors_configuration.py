"""Tests for exact frontend-origin configuration."""

from pathlib import Path
import sys
import unittest
from unittest.mock import patch


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from services.cors_configuration import (
    LOCAL_FRONTEND_ORIGINS,
    allowed_frontend_origins,
)


class CorsConfigurationTests(unittest.TestCase):
    """Permit only explicit browser origins supplied by trusted operators."""

    def test_defaults_to_documented_local_frontends(self) -> None:
        with patch.dict("os.environ", {}, clear=True):
            self.assertEqual(
                allowed_frontend_origins(),
                list(LOCAL_FRONTEND_ORIGINS),
            )

    def test_accepts_normalizes_and_deduplicates_exact_origins(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "VERIX_CORS_ORIGINS": (
                    "https://verix.example, https://verix.example/, "
                    "http://127.0.0.1:3000"
                )
            },
            clear=True,
        ):
            self.assertEqual(
                allowed_frontend_origins(),
                ["https://verix.example", "http://127.0.0.1:3000"],
            )

    def test_rejects_wildcards_credentials_paths_and_empty_entries(self) -> None:
        invalid_values = (
            "*",
            "https://user@example.com",
            "https://verix.example/path",
            "https://verix.example?preview=true",
            "https://verix.example#fragment",
            "https://verix.example,",
            "ftp://verix.example",
            "not-an-origin",
            "http://localhost:invalid",
            "https://exa mple.com",
            "https://example.com\\evil",
            "https://%65xample.com",
        )

        for value in invalid_values:
            with self.subTest(value=value), patch.dict(
                "os.environ",
                {"VERIX_CORS_ORIGINS": value},
                clear=True,
            ):
                with self.assertRaises(RuntimeError):
                    allowed_frontend_origins()


if __name__ == "__main__":
    unittest.main()
