import asyncio
import time

from backend.app.threat_intel import domain_age
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


def test_domain_age_caches_a_real_answer(monkeypatch):
    calls = []

    async def _lookup(domain, suffix):
        calls.append((domain, suffix))
        return {"domain_age_days": 4000, "domain_age_status": "established"}

    monkeypatch.setattr(domain_age, "_lookup_domain_age", _lookup)
    monkeypatch.setattr(domain_age, "_cache", TTLCache(ttl_seconds=60))

    asyncio.run(domain_age.check_domain_age("https://example.com/login"))
    asyncio.run(domain_age.check_domain_age("https://example.com/account"))

    # Keyed by registrable domain, so the second path is a cache hit.
    assert len(calls) == 1


def test_domain_age_does_not_cache_a_failed_lookup(monkeypatch):
    """A transient RDAP failure must not blind the domain-age signal for the
    full 24-hour TTL -- that signal is what rescues established domains from
    a false positive, so a cached failure costs a wrong verdict."""
    calls = []

    async def _flaky(domain, suffix):
        calls.append((domain, suffix))
        if len(calls) == 1:
            return {"domain_age_days": None, "domain_age_status": "unknown"}
        return {"domain_age_days": 4000, "domain_age_status": "established"}

    monkeypatch.setattr(domain_age, "_lookup_domain_age", _flaky)
    monkeypatch.setattr(domain_age, "_cache", TTLCache(ttl_seconds=60))

    first = asyncio.run(domain_age.check_domain_age("https://example.com/a"))
    second = asyncio.run(domain_age.check_domain_age("https://example.com/b"))
    asyncio.run(domain_age.check_domain_age("https://example.com/c"))

    assert first["domain_age_status"] == "unknown"
    assert second["domain_age_status"] == "established"
    assert len(calls) == 2  # the third call was served from the cache
