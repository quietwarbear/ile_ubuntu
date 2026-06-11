"""Lightweight in-memory rate limiting (no external dependency).

Sliding-window counter keyed by (bucket, client IP). Limits are per worker
process, so with N uvicorn workers the effective ceiling is up to N x the
configured limit — sized accordingly for credential-stuffing protection,
not precise quota accounting.
"""

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request

_lock = threading.Lock()
_hits: dict[tuple, deque] = defaultdict(deque)


def client_ip(request: Request) -> str:
    """Client IP, honoring the first hop of X-Forwarded-For (set by Railway's proxy)."""
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def rate_limit(request: Request, bucket: str, max_requests: int, window_seconds: int):
    """Raise 429 if this IP exceeded max_requests in the window for this bucket."""
    key = (bucket, client_ip(request))
    now = time.monotonic()
    cutoff = now - window_seconds
    with _lock:
        q = _hits[key]
        while q and q[0] < cutoff:
            q.popleft()
        if len(q) >= max_requests:
            raise HTTPException(
                status_code=429,
                detail="Too many attempts. Please wait a moment and try again.",
            )
        q.append(now)
