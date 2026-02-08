"""
API Gateway Rate Limiting - Per user and per IP.

Plan: Auth 10/min per IP; general API 100/min per user (or IP); AI 20/hour per user.
"""

import time
from collections import defaultdict
from typing import Callable, Optional, Tuple

from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

from src.config import get_settings


def _get_client_ip(request: Request) -> str:
    """Get client IP from request (X-Forwarded-For or direct)."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _get_user_id_from_jwt(request: Request) -> Optional[str]:
    """Extract user id from Bearer JWT if present. No verification here (auth runs later)."""
    auth = request.headers.get("authorization")
    if not auth or not auth.lower().startswith("bearer "):
        return None
    token = auth[7:].strip()
    if not token:
        return None
    try:
        from jose import jwt
        settings = get_settings()
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
            options={"verify_exp": True},
        )
        return str(payload.get("sub") or payload.get("user_id"))
    except Exception:
        return None


class InMemoryRateLimitStore:
    """Fixed-window in-memory store. Key -> (count, window_start_ts)."""

    def __init__(self):
        self._data: dict[str, Tuple[int, float]] = {}
        self._window_sec: dict[str, int] = {}

    def _key(self, scope: str, identifier: str) -> str:
        return f"{scope}:{identifier}"

    def check_and_incr(
        self,
        scope: str,
        identifier: str,
        limit: int,
        window_seconds: int,
    ) -> bool:
        """Returns True if under limit (and increments). False if over limit (no increment)."""
        key = self._key(scope, identifier)
        now = time.monotonic()
        if key not in self._data:
            self._data[key] = (1, now)
            self._window_sec[key] = window_seconds
            return True
        count, start = self._data[key]
        win = self._window_sec.get(key, window_seconds)
        if now - start >= win:
            self._data[key] = (1, now)
            self._window_sec[key] = window_seconds
            return True
        if count >= limit:
            return False
        self._data[key] = (count + 1, start)
        return True

    def cleanup_old(self, max_age_seconds: int = 3600):
        """Remove entries older than max_age_seconds to avoid unbounded growth."""
        now = time.monotonic()
        to_remove = [k for k, (_, start) in self._data.items() if now - start > max_age_seconds]
        for k in to_remove:
            self._data.pop(k, None)
            self._window_sec.pop(k, None)


# Module-level store (single process). For multi-worker use Redis in Phase 3.
_store: Optional[InMemoryRateLimitStore] = None


def get_store() -> InMemoryRateLimitStore:
    global _store
    if _store is None:
        _store = InMemoryRateLimitStore()
    return _store


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limit by scope:
    - auth: /api/v1/auth POST -> per IP, 10/min
    - api: other /api/v1 -> per user (or IP), 100/min
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        settings = get_settings()
        if not settings.rate_limit_enabled:
            return await call_next(request)

        path = request.url.path or ""
        if not path.startswith(settings.api_v1_prefix):
            return await call_next(request)

        store = get_store()
        # Periodic cleanup
        store.cleanup_old(max_age_seconds=7200)

        # Auth: login/register by IP
        if path.startswith(f"{settings.api_v1_prefix}/auth") and request.method == "POST":
            limit = settings.rate_limit_auth_per_minute
            identifier = _get_client_ip(request)
            scope = "auth"
            window = 60
        else:
            # General API: by user if authenticated, else by IP
            limit = settings.rate_limit_api_per_minute
            user_id = _get_user_id_from_jwt(request)
            identifier = user_id if user_id else _get_client_ip(request)
            scope = "api"
            window = 60

        allowed = store.check_and_incr(scope, identifier, limit, window)
        if not allowed:
            return Response(
                content='{"detail":"Too many requests. Please try again later."}',
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                media_type="application/json",
            )
        return await call_next(request)
