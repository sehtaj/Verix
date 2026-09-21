"""Process-local admission controls for a small public Verix demonstration."""

from collections import deque
from dataclasses import dataclass
import os
from threading import BoundedSemaphore, Lock
import time
from typing import Callable

from services.temporary_workspaces import DEFAULT_STALE_WORKSPACE_SECONDS


DEFAULT_MAX_REQUEST_BYTES = 256 * 1024
DEFAULT_MAX_CONCURRENT_JOBS = 2
DEFAULT_REQUESTS_PER_MINUTE = 30
DEFAULT_LLM_CALLS_PER_DAY = 100
DEFAULT_LLM_MAX_OUTPUT_TOKENS = 4_096
MAX_TRACKED_CLIENTS = 10_000


@dataclass(frozen=True)
class PublicDemoLimits:
    """Validated resource ceilings for one backend process."""

    max_request_bytes: int = DEFAULT_MAX_REQUEST_BYTES
    max_concurrent_jobs: int = DEFAULT_MAX_CONCURRENT_JOBS
    requests_per_minute: int = DEFAULT_REQUESTS_PER_MINUTE
    llm_calls_per_day: int = DEFAULT_LLM_CALLS_PER_DAY
    llm_max_output_tokens: int = DEFAULT_LLM_MAX_OUTPUT_TOKENS
    stale_workspace_seconds: int = DEFAULT_STALE_WORKSPACE_SECONDS

    @classmethod
    def from_environment(cls) -> "PublicDemoLimits":
        """Read optional integer overrides without accepting unsafe zeroes."""
        return cls(
            max_request_bytes=_positive_integer(
                "VERIX_MAX_REQUEST_BYTES", DEFAULT_MAX_REQUEST_BYTES
            ),
            max_concurrent_jobs=_positive_integer(
                "VERIX_MAX_CONCURRENT_JOBS", DEFAULT_MAX_CONCURRENT_JOBS
            ),
            requests_per_minute=_positive_integer(
                "VERIX_REQUESTS_PER_MINUTE", DEFAULT_REQUESTS_PER_MINUTE
            ),
            llm_calls_per_day=_positive_integer(
                "VERIX_LLM_CALLS_PER_DAY", DEFAULT_LLM_CALLS_PER_DAY
            ),
            llm_max_output_tokens=_positive_integer(
                "VERIX_LLM_MAX_OUTPUT_TOKENS", DEFAULT_LLM_MAX_OUTPUT_TOKENS
            ),
            stale_workspace_seconds=_positive_integer(
                "VERIX_STALE_WORKSPACE_SECONDS", DEFAULT_STALE_WORKSPACE_SECONDS
            ),
        )


class PublicDemoLimitError(RuntimeError):
    """A safe rejection produced before expensive public-demo work starts."""

    def __init__(self, status_code: int, detail: str, retry_after: int | None = None):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail
        self.retry_after = retry_after


class PublicDemoGuard:
    """Bound request rate, concurrent jobs, and LLM calls in one process."""

    def __init__(
        self,
        limits: PublicDemoLimits,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.limits = limits
        self.clock = clock
        self._jobs = BoundedSemaphore(limits.max_concurrent_jobs)
        self._state_lock = Lock()
        self._request_times: dict[str, deque[float]] = {}
        self._llm_calls: deque[tuple[float, int]] = deque()
        self._llm_call_total = 0

    def check_request_rate(self, client_key: str) -> None:
        """Reject clients exceeding the rolling one-minute request allowance."""
        now = self.clock()
        cutoff = now - 60
        with self._state_lock:
            if (
                client_key not in self._request_times
                and len(self._request_times) >= MAX_TRACKED_CLIENTS
            ):
                self._discard_expired_clients(cutoff)
                if len(self._request_times) >= MAX_TRACKED_CLIENTS:
                    raise PublicDemoLimitError(
                        503,
                        "The public demo is temporarily at capacity.",
                        60,
                    )
            request_times = self._request_times.setdefault(client_key, deque())
            while request_times and request_times[0] <= cutoff:
                request_times.popleft()
            if len(request_times) >= self.limits.requests_per_minute:
                retry_after = max(1, int(request_times[0] + 60 - now) + 1)
                raise PublicDemoLimitError(
                    429,
                    "Public demo request limit reached. Please try again shortly.",
                    retry_after,
                )
            request_times.append(now)

    def try_acquire_job(self) -> None:
        """Reserve one expensive workflow slot without building an unbounded queue."""
        if not self._jobs.acquire(blocking=False):
            raise PublicDemoLimitError(
                503,
                "The public demo is busy. Please try again shortly.",
                5,
            )

    def release_job(self) -> None:
        """Release one previously acquired workflow slot."""
        self._jobs.release()

    def reserve_llm_calls(self, call_count: int) -> None:
        """Conservatively reserve weighted LLM calls in a rolling 24-hour window."""
        if call_count <= 0:
            return
        now = self.clock()
        cutoff = now - 86_400
        with self._state_lock:
            while self._llm_calls and self._llm_calls[0][0] <= cutoff:
                _, expired_count = self._llm_calls.popleft()
                self._llm_call_total -= expired_count
            if self._llm_call_total + call_count > self.limits.llm_calls_per_day:
                retry_after = (
                    max(1, int(self._llm_calls[0][0] + 86_400 - now) + 1)
                    if self._llm_calls
                    else 86_400
                )
                raise PublicDemoLimitError(
                    429,
                    "The public demo's daily AI budget has been reached.",
                    retry_after,
                )
            self._llm_calls.append((now, call_count))
            self._llm_call_total += call_count

    def _discard_expired_clients(self, cutoff: float) -> None:
        """Remove only clients whose complete rolling history has expired."""
        expired_keys = []
        for client_key, request_times in self._request_times.items():
            while request_times and request_times[0] <= cutoff:
                request_times.popleft()
            if not request_times:
                expired_keys.append(client_key)
        for client_key in expired_keys:
            self._request_times.pop(client_key, None)


def _positive_integer(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
    except ValueError:
        raise RuntimeError(f"{name} must be a positive integer.") from None
    if parsed <= 0:
        raise RuntimeError(f"{name} must be a positive integer.")
    return parsed
