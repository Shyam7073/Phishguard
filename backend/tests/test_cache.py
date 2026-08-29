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


def test_cache_honours_a_per_entry_ttl_override():
    cache = TTLCache(ttl_seconds=600)
    cache.set("short", "value", ttl_seconds=0.05)
    time.sleep(0.1)
    assert cache.get("short") is None


def test_cache_evicts_instead_of_growing_without_bound():
    # The URLhaus cache is keyed by full URL, so an always-on extension
    # feeds it an effectively unlimited stream of distinct keys.
    cache = TTLCache(ttl_seconds=600, max_entries=10)
    for i in range(100):
        cache.set(f"key-{i}", i)
    assert len(cache._store) <= 10


def test_cache_eviction_prefers_expired_entries():
    cache = TTLCache(ttl_seconds=600, max_entries=3)
    cache.set("stale", "old", ttl_seconds=0.01)
    cache.set("keep-1", 1)
    cache.set("keep-2", 2)
    time.sleep(0.05)
    cache.set("keep-3", 3)
    assert cache.get("stale") is None
    assert cache.get("keep-1") == 1
    assert cache.get("keep-3") == 3
