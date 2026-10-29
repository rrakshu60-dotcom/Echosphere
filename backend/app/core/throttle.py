"""
In-memory sliding-window counters for sign-in failures and per-user AI calls.

The backend runs as a single instance, so process memory is the right place for these counters;
they reset on restart, which only ever loosens a limit for a few minutes.
"""

import threading
import time
from collections import deque
from typing import Deque, Dict, Hashable, Optional

from fastapi import HTTPException, status


class SlidingWindow:
    def __init__(self, limit: int, window_seconds: float):
        self.limit = limit
        self.window = window_seconds
        self._hits: Dict[Hashable, Deque[float]] = {}
        self._lock = threading.Lock()

    def _trim(self, key: Hashable, now: float) -> Deque[float]:
        hits = self._hits.get(key)
        if hits is None:
            hits = self._hits[key] = deque()
        while hits and now - hits[0] >= self.window:
            hits.popleft()
        return hits

    def retry_after(self, key: Hashable) -> Optional[int]:
        """Seconds until the key may try again, or None when it is under the limit."""
        now = time.monotonic()
        with self._lock:
            hits = self._trim(key, now)
            if len(hits) < self.limit:
                if not hits:
                    self._hits.pop(key, None)
                return None
            return max(1, int(self.window - (now - hits[0])) + 1)

    def add(self, key: Hashable) -> None:
        now = time.monotonic()
        with self._lock:
            self._trim(key, now).append(now)
            if len(self._hits) > 50_000:
                # Drop idle keys so a flood of made-up identifiers cannot grow memory without bound
                for k in [k for k, v in self._hits.items() if not v or now - v[-1] >= self.window]:
                    self._hits.pop(k, None)

    def hit(self, key: Hashable) -> Optional[int]:
        """Count one call; returns the retry delay if it went over the limit (the call is not counted then)."""
        wait = self.retry_after(key)
        if wait is None:
            self.add(key)
        return wait

    def reset(self, key: Hashable) -> None:
        with self._lock:
            self._hits.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._hits.clear()


def too_many(wait: int, detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=detail,
        headers={"Retry-After": str(wait)},
    )


# Sign-in failures. Campus Wi-Fi puts many students behind one address, so the tight limit is per
# address *and* account; the per-address and per-account limits are much looser.
SIGN_IN_FAILS_PER_ACCOUNT_AND_ADDRESS = SlidingWindow(limit=8, window_seconds=15 * 60)
SIGN_IN_FAILS_PER_ADDRESS = SlidingWindow(limit=60, window_seconds=15 * 60)
SIGN_IN_FAILS_PER_ACCOUNT = SlidingWindow(limit=30, window_seconds=15 * 60)

# AI calls per signed-in user protect the shared model quotas. Every AI request counts towards the
# loose limit (the app fetches summaries per card); model-heavy ones (chat, drafting, speech, voice
# dictation) also count towards the tight one. Both are far above what a person types or clicks.
AI_CALLS_PER_USER = SlidingWindow(limit=120, window_seconds=60)
AI_HEAVY_CALLS_PER_USER = SlidingWindow(limit=20, window_seconds=60)


def check_ai_quota(user_id: int, heavy: bool = False) -> None:
    wait = AI_CALLS_PER_USER.hit(user_id)
    if wait is None and heavy:
        wait = AI_HEAVY_CALLS_PER_USER.hit(user_id)
    if wait:
        raise too_many(wait, "Too many AI requests. Please wait a moment and try again.")


def _account_key(identifier: str) -> str:
    return (identifier or "").strip().lower()[:254]


def check_sign_in_allowed(identifier: str, address: Optional[str]) -> None:
    account = _account_key(identifier)
    addr = address or "unknown"
    wait = (
        SIGN_IN_FAILS_PER_ACCOUNT_AND_ADDRESS.retry_after((addr, account))
        or SIGN_IN_FAILS_PER_ADDRESS.retry_after(addr)
        or SIGN_IN_FAILS_PER_ACCOUNT.retry_after(account)
    )
    if wait:
        raise too_many(wait, f"Too many failed sign-in attempts. Try again in {max(1, round(wait / 60))} minute(s).")


def record_sign_in_failure(identifier: str, address: Optional[str]) -> None:
    account = _account_key(identifier)
    addr = address or "unknown"
    SIGN_IN_FAILS_PER_ACCOUNT_AND_ADDRESS.add((addr, account))
    SIGN_IN_FAILS_PER_ADDRESS.add(addr)
    SIGN_IN_FAILS_PER_ACCOUNT.add(account)


def record_sign_in_success(identifier: str, address: Optional[str]) -> None:
    SIGN_IN_FAILS_PER_ACCOUNT_AND_ADDRESS.reset((address or "unknown", _account_key(identifier)))


def reset_all() -> None:
    for window in (SIGN_IN_FAILS_PER_ACCOUNT_AND_ADDRESS, SIGN_IN_FAILS_PER_ADDRESS, SIGN_IN_FAILS_PER_ACCOUNT, AI_CALLS_PER_USER, AI_HEAVY_CALLS_PER_USER):
        window.clear()
