"""Unit tests for the two threat-intel lookups' fail-soft contract.

Both are documented as best-effort: any failure has to come back as
"unknown" rather than raising, because /scan can still answer from the ML
model alone. These exercise that directly, without going near the network.
"""

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from backend.app.threat_intel import domain_age as domain_age_module
from backend.app.threat_intel import urlhaus as urlhaus_module


@pytest.fixture(autouse=True)
def _clear_caches():
    urlhaus_module._cache._store.clear()
    domain_age_module._cache._store.clear()


def _run(coro):
    return asyncio.run(coro)


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def _patch_urlhaus_response(monkeypatch, payload):
    monkeypatch.setenv("URLHAUS_AUTH_KEY", "test-key")

    class _FakeClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, *args, **kwargs):
            if isinstance(payload, Exception):
                raise payload
            return _FakeResponse(payload)

    monkeypatch.setattr(urlhaus_module.httpx, "AsyncClient", lambda **kw: _FakeClient())


def test_urlhaus_hit_is_listed(monkeypatch):
    _patch_urlhaus_response(monkeypatch, {"query_status": "ok"})
    assert _run(urlhaus_module.check_urlhaus("http://bad.example")) == "listed"


def test_urlhaus_miss_is_not_listed(monkeypatch):
    _patch_urlhaus_response(monkeypatch, {"query_status": "no_results"})
    assert _run(urlhaus_module.check_urlhaus("http://good.example")) == "not_listed"


def test_urlhaus_api_side_error_is_unknown_not_clean(monkeypatch):
    # "invalid_url" means URLhaus declined to answer. Reporting that as
    # "not_listed" would turn an API error into evidence the URL is clean.
    _patch_urlhaus_response(monkeypatch, {"query_status": "invalid_url"})
    assert _run(urlhaus_module.check_urlhaus("http://weird.example")) == "unknown"


def test_urlhaus_unexpected_payload_shape_is_unknown(monkeypatch):
    _patch_urlhaus_response(monkeypatch, ["not", "a", "dict"])
    assert _run(urlhaus_module.check_urlhaus("http://weird2.example")) == "unknown"


def test_urlhaus_transport_failure_is_unknown(monkeypatch):
    _patch_urlhaus_response(monkeypatch, RuntimeError("connection reset"))
    assert _run(urlhaus_module.check_urlhaus("http://down.example")) == "unknown"


def test_urlhaus_missing_key_is_unknown(monkeypatch):
    monkeypatch.delenv("URLHAUS_AUTH_KEY", raising=False)
    assert _run(urlhaus_module.check_urlhaus("http://nokey.example")) == "unknown"


def test_urlhaus_failure_is_cached_only_briefly(monkeypatch):
    _patch_urlhaus_response(monkeypatch, RuntimeError("boom"))
    assert _run(urlhaus_module.check_urlhaus("http://flaky.example")) == "unknown"

    _, expires_at = urlhaus_module._cache._store["http://flaky.example"]
    remaining = expires_at - __import__("time").monotonic()
    # A transient failure must not pin the URL to "unknown" for the full
    # 15-minute success TTL.
    assert remaining <= urlhaus_module.FAILURE_CACHE_TTL_SECONDS
    assert remaining < urlhaus_module.CACHE_TTL_SECONDS


def _patch_rdap(monkeypatch, created_date):
    class _FakeRdapResponse:
        def to_whois_dict(self):
            if isinstance(created_date, Exception):
                raise created_date
            return {"created_date": created_date}

    class _FakeClient:
        async def aio_lookup(self, domain, suffix):
            return _FakeRdapResponse()

    async def _fake_get_client():
        return _FakeClient()

    monkeypatch.setattr(domain_age_module, "_get_client", _fake_get_client)


def test_domain_age_established(monkeypatch):
    _patch_rdap(monkeypatch, datetime.now(timezone.utc) - timedelta(days=4000))
    result = _run(domain_age_module.check_domain_age("https://github.com/anthropics"))
    assert result["domain_age_status"] == "established"
    assert result["domain_age_days"] >= 4000


def test_domain_age_new(monkeypatch):
    _patch_rdap(monkeypatch, datetime.now(timezone.utc) - timedelta(days=3))
    result = _run(domain_age_module.check_domain_age("https://brand-new-domain.com"))
    assert result["domain_age_status"] == "new"


def test_domain_age_naive_creation_date_is_treated_as_utc(monkeypatch):
    # Some registries return a datetime with no tzinfo; subtracting that
    # from an aware `now` raises unless it's normalised first.
    _patch_rdap(monkeypatch, datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=800))
    result = _run(domain_age_module.check_domain_age("https://naive-registry.com"))
    assert result["domain_age_status"] == "established"


def test_domain_age_string_creation_date_is_unknown_not_a_crash(monkeypatch):
    _patch_rdap(monkeypatch, "2011-04-01T00:00:00Z")
    result = _run(domain_age_module.check_domain_age("https://stringy-registry.com"))
    assert result == {"domain_age_days": None, "domain_age_status": "unknown"}


def test_domain_age_lookup_error_is_unknown(monkeypatch):
    _patch_rdap(monkeypatch, RuntimeError("registry said no"))
    result = _run(domain_age_module.check_domain_age("https://broken-registry.com"))
    assert result == {"domain_age_days": None, "domain_age_status": "unknown"}


def test_domain_age_unparseable_url_is_unknown():
    assert _run(domain_age_module.check_domain_age("not-a-url")) == {
        "domain_age_days": None,
        "domain_age_status": "unknown",
    }


def test_domain_age_failure_is_cached_only_briefly(monkeypatch):
    import time

    _patch_rdap(monkeypatch, RuntimeError("timeout"))
    _run(domain_age_module.check_domain_age("https://flaky-registry.com"))

    _, expires_at = domain_age_module._cache._store["flaky-registry.com"]
    remaining = expires_at - time.monotonic()
    # 24 hours of "unknown" off the back of one timeout is the bug here.
    assert remaining <= domain_age_module.FAILURE_CACHE_TTL_SECONDS
    assert remaining < domain_age_module.CACHE_TTL_SECONDS
