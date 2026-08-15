"""Sign-in rate limiting, per account **and** per IP (SEC-A-005).

`runtime-and-scale.md` §1: 5 per account per 10 minutes, 20 per IP per minute, 429 with
`Retry-After` on either.

**The per-account half is the one that matters.** An IP-only limit is walked straight past
by a distributed attempt, and this is the only account system standing in front of
critical-infrastructure data. STEST-004 proves it by making all six attempts from six
different addresses.

State is in memory rather than in the store. That is a deliberate limit and worth naming:
a restart clears the counters, and a second process would keep its own. Both are acceptable
at one process and under 50 users (ADR-001, ADR-002) and neither would be if the platform
were reachable from outside SGW's network — which is the same threshold
`runtime-and-scale.md` §1 already sets for revisiting the write-endpoint limits.
"""

import time
from collections import defaultdict, deque
from threading import Lock

ACCOUNT_LIMIT = 5
ACCOUNT_WINDOW_SECONDS = 10 * 60
IP_LIMIT = 20
IP_WINDOW_SECONDS = 60


class RateLimiter:
    def __init__(
        self,
        account_limit: int = ACCOUNT_LIMIT,
        account_window_seconds: int = ACCOUNT_WINDOW_SECONDS,
        ip_limit: int = IP_LIMIT,
        ip_window_seconds: int = IP_WINDOW_SECONDS,
    ) -> None:
        self.account_limit = account_limit
        self.account_window_seconds = account_window_seconds
        self.ip_limit = ip_limit
        self.ip_window_seconds = ip_window_seconds
        self._account_failures: dict[str, deque[float]] = defaultdict(deque)
        self._ip_failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    @staticmethod
    def _prune(attempts: deque[float], window_seconds: int, now: float) -> None:
        while attempts and attempts[0] <= now - window_seconds:
            attempts.popleft()

    def retry_after(self, account_key: str, ip: str, now: float | None = None) -> int | None:
        """Seconds to wait, or None when the attempt may proceed."""
        now = time.monotonic() if now is None else now
        with self._lock:
            waits = []
            buckets = (
                (
                    self._account_failures[account_key],
                    self.account_limit,
                    self.account_window_seconds,
                ),
                (self._ip_failures[ip], self.ip_limit, self.ip_window_seconds),
            )
            for attempts, limit, window in buckets:
                self._prune(attempts, window, now)
                if len(attempts) >= limit:
                    waits.append(attempts[0] + window - now)
            if not waits:
                return None
            return max(1, int(max(waits)) + 1)

    def record_failure(self, account_key: str, ip: str, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        with self._lock:
            self._account_failures[account_key].append(now)
            self._ip_failures[ip].append(now)

    def clear_account(self, account_key: str) -> None:
        """A successful sign-in clears the account's count, never the address's.

        Otherwise one valid sign-in from a machine would reset the limit protecting every
        other account reachable from it.
        """
        with self._lock:
            self._account_failures.pop(account_key, None)
