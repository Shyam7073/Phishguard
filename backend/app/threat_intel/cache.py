"""A tiny in-memory TTL cache shared by both threat-intel lookups.

Not a general-purpose caching library on purpose -- just a dict that
forgets old entries. Process-local (resets on restart, not shared across
workers), which is fine for this project's single-process scope.
"""

import time


class TTLCache:
    def __init__(self, ttl_seconds: float):
        self._ttl = ttl_seconds
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

    def set(self, key, value) -> None:
        self._store[key] = (value, time.monotonic() + self._ttl)
