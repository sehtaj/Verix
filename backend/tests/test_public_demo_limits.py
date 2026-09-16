"""Tests for process-local public-demo admission controls."""

import asyncio
from pathlib import Path
import sys
import unittest
from unittest.mock import patch


BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
if str(BACKEND_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIRECTORY))

from api.public_demo_middleware import PublicDemoMiddleware
from services.public_demo_limits import (
    PublicDemoGuard,
    PublicDemoLimitError,
    PublicDemoLimits,
)


class PublicDemoGuardTests(unittest.TestCase):
    """Keep rate, concurrency, and cost ceilings deterministic."""

    def setUp(self) -> None:
        self.now = 1_000.0
        self.limits = PublicDemoLimits(
            max_request_bytes=8,
            max_concurrent_jobs=1,
            requests_per_minute=2,
            llm_calls_per_day=3,
            llm_max_output_tokens=128,
            stale_workspace_seconds=60,
        )
        self.guard = PublicDemoGuard(self.limits, clock=lambda: self.now)

    def test_rate_limit_recovers_after_the_rolling_window(self) -> None:
        self.guard.check_request_rate("client")
        self.guard.check_request_rate("client")

        with self.assertRaises(PublicDemoLimitError) as raised:
            self.guard.check_request_rate("client")
        self.assertEqual(raised.exception.status_code, 429)

        self.now += 61
        self.guard.check_request_rate("client")

    def test_concurrency_rejects_instead_of_queueing(self) -> None:
        self.guard.try_acquire_job()
        with self.assertRaises(PublicDemoLimitError) as raised:
            self.guard.try_acquire_job()
        self.assertEqual(raised.exception.status_code, 503)

        self.guard.release_job()
        self.guard.try_acquire_job()
        self.guard.release_job()

    def test_weighted_llm_budget_recovers_after_24_hours(self) -> None:
        self.guard.reserve_llm_calls(2)
        with self.assertRaises(PublicDemoLimitError) as raised:
            self.guard.reserve_llm_calls(2)
        self.assertIn("daily AI budget", raised.exception.detail)

        self.now += 86_401
        self.guard.reserve_llm_calls(3)

    def test_environment_requires_positive_integer_overrides(self) -> None:
        with patch.dict(
            "os.environ",
            {"VERIX_MAX_CONCURRENT_JOBS": "4"},
            clear=True,
        ):
            self.assertEqual(
                PublicDemoLimits.from_environment().max_concurrent_jobs,
                4,
            )

        for value in ("0", "-1", "many"):
            with self.subTest(value=value), patch.dict(
                "os.environ",
                {"VERIX_MAX_CONCURRENT_JOBS": value},
                clear=True,
            ):
                with self.assertRaises(RuntimeError):
                    PublicDemoLimits.from_environment()


class PublicDemoMiddlewareTests(unittest.TestCase):
    """Exercise body and weighted endpoint limits at the ASGI boundary."""

    def test_rejects_streamed_body_that_exceeds_limit(self) -> None:
        result = asyncio.run(self._request("/repository", (b"12345", b"6789")))

        self.assertEqual(result[0]["status"], 413)
        self.assertEqual(self.app_calls, 0)

    def test_reserves_weighted_llm_calls_and_releases_job_slot(self) -> None:
        first = asyncio.run(self._request("/repository/investigate", (b"{}",)))
        second = asyncio.run(self._request("/repository/investigate", (b"{}",)))

        self.assertEqual(first[0]["status"], 204)
        self.assertEqual(second[0]["status"], 429)
        self.assertEqual(self.app_calls, 1)
        self.guard.try_acquire_job()
        self.guard.release_job()

    async def _request(
        self,
        path: str,
        body_chunks: tuple[bytes, ...],
    ) -> list[dict]:
        self.app_calls = getattr(self, "app_calls", 0)
        self.guard = getattr(
            self,
            "guard",
            PublicDemoGuard(
                PublicDemoLimits(
                    max_request_bytes=8,
                    max_concurrent_jobs=1,
                    requests_per_minute=10,
                    llm_calls_per_day=3,
                    llm_max_output_tokens=128,
                    stale_workspace_seconds=60,
                )
            ),
        )

        async def app(scope, receive, send):
            self.app_calls += 1
            await receive()
            await send({"type": "http.response.start", "status": 204, "headers": []})
            await send({"type": "http.response.body", "body": b""})

        messages = [
            {
                "type": "http.request",
                "body": chunk,
                "more_body": index < len(body_chunks) - 1,
            }
            for index, chunk in enumerate(body_chunks)
        ]

        async def receive():
            return messages.pop(0)

        sent: list[dict] = []

        async def send(message):
            sent.append(message)

        scope = {
            "type": "http",
            "method": "POST",
            "path": path,
            "headers": (),
            "client": ("127.0.0.1", 1234),
        }
        middleware = PublicDemoMiddleware(app, guard=self.guard)
        await middleware(scope, receive, send)
        return sent


if __name__ == "__main__":
    unittest.main()
