import time

from backend.app.threat_intel.cache import TTLCache


def test_cache_returns_stored_value_before_expiry():
    cache = TTLCache(ttl_seconds=60)
    cache.set("key", "value")
    assert cache.get("key") == "value"


def test_cache_returns_none_for_missing_key():
    cache = TTLCache(ttl_seconds=60)
    assert cache.get("missing") is None


def test_cache_expires_entries_after_ttl():
    cache = TTLCache(ttl_seconds=0.05)
    cache.set("key", "value")
    time.sleep(0.1)
    assert cache.get("key") is None
