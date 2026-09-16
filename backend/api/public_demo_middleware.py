"""ASGI admission middleware for bounded public-demo requests."""

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from services.public_demo_limits import PublicDemoGuard, PublicDemoLimitError


EXPENSIVE_PATHS = frozenset(
    {
        "/generate",
        "/repository/test-run",
        "/repository/generate",
        "/repository/investigate",
        "/repository/fix-proposal",
        "/repository/fix-verify",
    }
)
LLM_CALL_COSTS = {
    "/generate": 1,
    "/repository/generate": 1,
    "/repository/investigate": 2,
    "/repository/fix-proposal": 3,
}


class PublicDemoMiddleware:
    """Reject oversized or over-budget work before endpoint execution."""

    def __init__(self, app: ASGIApp, *, guard: PublicDemoGuard) -> None:
        self.app = app
        self.guard = guard

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in {
            "POST",
            "PUT",
            "PATCH",
        }:
            await self.app(scope, receive, send)
            return

        try:
            body = await self._read_bounded_body(scope, receive)
            client = scope.get("client")
            client_key = str(client[0]) if client else "unknown"
            self.guard.check_request_rate(client_key)

            path = scope.get("path", "")
            acquired_job = False
            if path in EXPENSIVE_PATHS:
                self.guard.try_acquire_job()
                acquired_job = True
            try:
                self.guard.reserve_llm_calls(LLM_CALL_COSTS.get(path, 0))
                await self.app(scope, _replay_body(body), send)
            finally:
                if acquired_job:
                    self.guard.release_job()
        except PublicDemoLimitError as error:
            headers = (
                {"Retry-After": str(error.retry_after)}
                if error.retry_after is not None
                else None
            )
            response = JSONResponse(
                status_code=error.status_code,
                content={"detail": error.detail},
                headers=headers,
            )
            await response(scope, receive, send)

    async def _read_bounded_body(self, scope: Scope, receive: Receive) -> bytes:
        content_length = _content_length(scope)
        if (
            content_length is not None
            and content_length > self.guard.limits.max_request_bytes
        ):
            raise PublicDemoLimitError(413, "Request body is too large.")

        parts: list[bytes] = []
        total = 0
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                return b""
            body = message.get("body", b"")
            total += len(body)
            if total > self.guard.limits.max_request_bytes:
                raise PublicDemoLimitError(413, "Request body is too large.")
            parts.append(body)
            if not message.get("more_body", False):
                return b"".join(parts)


def _content_length(scope: Scope) -> int | None:
    for name, value in scope.get("headers", ()):
        if name.lower() == b"content-length":
            try:
                parsed = int(value)
            except ValueError:
                raise PublicDemoLimitError(400, "Content-Length is invalid.") from None
            if parsed < 0:
                raise PublicDemoLimitError(400, "Content-Length is invalid.")
            return parsed
    return None


def _replay_body(body: bytes) -> Receive:
    consumed = False

    async def receive():
        nonlocal consumed
        if consumed:
            return {"type": "http.disconnect"}
        consumed = True
        return {"type": "http.request", "body": body, "more_body": False}

    return receive
