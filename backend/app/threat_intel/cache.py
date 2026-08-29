"""A tiny in-memory TTL cache shared by both threat-intel lookups.

Not a general-purpose caching library on purpose -- just a dict that
forgets old entries. Process-local (resets on restart, not shared across
workers), which is fine for this project's single-process scope.

Bounded, though: the URLhaus cache is keyed by full URL, and a backend
serving a handful of always-on extensions sees a effectively unlimited
stream of distinct URLs. Expired entries are only dropped when that exact
key is read again, so without a cap the dict would grow for the lifetime
of the process and never shrink.
"""

import time

# Enough to cover the working set of a browsing session many times over,
# while keeping the worst case to a few MB rather than unbounded.
DEFAULT_MAX_ENTRIES = 5_000


class TTLCache:
    def __init__(self, ttl_seconds: float, max_entries: int = DEFAULT_MAX_ENTRIES):
        self._ttl = ttl_seconds
        self._max_entries = max_entries
        self._store: dict = {}

    def get(self, key):
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key, value, ttl_seconds: float | None = None) -> None:
        """Store `value`, optionally with a shorter TTL than the default.

        The per-call TTL is what lets both lookups cache a *failed* lookup
        briefly (to absorb a burst of retries) without a single transient
        timeout pinning a domain to "unknown" for the full success TTL.
        """
        if len(self._store) >= self._max_entries:
            self._evict()
        ttl = self._ttl if ttl_seconds is None else ttl_seconds
        self._store[key] = (value, time.monotonic() + ttl)

    def _evict(self) -> None:
        """Drop expired entries; if that frees nothing, drop the oldest half.

        dicts preserve insertion order, so the first keys are the
        least-recently-inserted -- close enough to LRU for a cache this
        small, without tracking access times.
        """
        now = time.monotonic()
        expired = [key for key, (_, expires_at) in self._store.items() if now > expires_at]
        for key in expired:
            del self._store[key]

        if self._store and len(self._store) >= self._max_entries:
            for key in list(self._store)[: len(self._store) // 2]:
                del self._store[key]
