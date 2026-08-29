import asyncio

import backend.app.api.scan as scan_module

CLIENT_ID = "test-client"


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_scan_returns_verdict(client):
    response = client.post("/scan", json={"url": "http://google.com", "client_id": CLIENT_ID})
    assert response.status_code == 200
    body = response.json()
    assert body["url"] == "http://google.com"
    assert isinstance(body["is_phishing"], bool)
    assert 0.0 <= body["confidence"] <= 1.0
    assert 0.0 <= body["ml_score"] <= 1.0
    assert body["urlhaus_status"] == "not_listed"
    assert body["domain_age_status"] == "unknown"
    assert body["domain_age_days"] is None
    assert body["verdict_reason"]


def test_scan_flags_ip_address_login_url(client):
    response = client.post(
        "/scan", json={"url": "http://192.168.1.1/login/verify-account", "client_id": CLIENT_ID}
    )
    assert response.status_code == 200
    assert response.json()["is_phishing"] is True


def test_scan_rejects_empty_url(client):
    response = client.post("/scan", json={"url": "", "client_id": CLIENT_ID})
    assert response.status_code == 422


def test_scan_urlhaus_hit_overrides_ml_score(client, monkeypatch):
    async def _fake_listed(url: str) -> str:
        return "listed"

    monkeypatch.setattr(scan_module, "check_urlhaus", _fake_listed)

    # A URL the ML model alone would call legitimate -- URLhaus should still
    # force the verdict to phishing with high confidence.
    response = client.post("/scan", json={"url": "http://google.com", "client_id": CLIENT_ID})
    assert response.status_code == 200
    body = response.json()
    assert body["is_phishing"] is True
    assert body["confidence"] >= 0.99
    assert body["urlhaus_status"] == "listed"
    assert "URLhaus" in body["verdict_reason"]


def test_scan_urlhaus_unknown_falls_back_to_ml_only(client, monkeypatch):
    async def _fake_unknown(url: str) -> str:
        return "unknown"

    monkeypatch.setattr(scan_module, "check_urlhaus", _fake_unknown)

    response = client.post("/scan", json={"url": "http://google.com", "client_id": CLIENT_ID})
    assert response.status_code == 200
    body = response.json()
    assert body["urlhaus_status"] == "unknown"
    assert "unavailable" in body["verdict_reason"]


def _fake_predict(phishing_probability: float):
    def _inner(url: str) -> dict:
        return {
            "is_phishing": phishing_probability >= 0.5,
            "phishing_probability": phishing_probability,
        }

    return _inner


def test_scan_established_domain_rescues_borderline_phishing_call(client, monkeypatch):
    # A borderline ML score (0.7, well under the 0.9 override ceiling) on a
    # long-established domain -- exactly the github.com/anthropics-style
    # false positive this signal was added to fix.
    monkeypatch.setattr(scan_module, "predict", _fake_predict(0.7))

    async def _fake_established(url: str) -> dict:
        return {"domain_age_days": 5000, "domain_age_status": "established"}

    monkeypatch.setattr(scan_module, "check_domain_age", _fake_established)

    response = client.post(
        "/scan", json={"url": "http://github.com/anthropics", "client_id": CLIENT_ID}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_phishing"] is False
    assert body["domain_age_status"] == "established"
    assert body["domain_age_days"] == 5000
    assert "long-established" in body["verdict_reason"]


def test_scan_established_domain_does_not_rescue_confident_phishing_call(client, monkeypatch):
    # A very confident ML phishing score (0.95, at/above the override
    # ceiling) should NOT be rescued just because the domain is old --
    # e.g. a compromised or purpose-aged domain hosting real phishing.
    monkeypatch.setattr(scan_module, "predict", _fake_predict(0.95))

    async def _fake_established(url: str) -> dict:
        return {"domain_age_days": 5000, "domain_age_status": "established"}

    monkeypatch.setattr(scan_module, "check_domain_age", _fake_established)

    response = client.post(
        "/scan", json={"url": "http://example.com/login", "client_id": CLIENT_ID}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["is_phishing"] is True


def test_scan_new_domain_is_annotated_but_not_auto_flagged(client, monkeypatch):
    # A confidently-legit ML score on a brand-new domain is NOT flipped to
    # phishing (avoids new false positives on genuine new sites) -- just
    # noted in the reason so a human can weigh it.
    monkeypatch.setattr(scan_module, "predict", _fake_predict(0.1))

    async def _fake_new(url: str) -> dict:
        return {"domain_age_days": 3, "domain_age_status": "new"}

    monkeypatch.setattr(scan_module, "check_domain_age", _fake_new)

    response = client.post("/scan", json={"url": "http://example.com", "client_id": CLIENT_ID})
    assert response.status_code == 200
    body = response.json()
    assert body["is_phishing"] is False
    assert "registered very recently" in body["verdict_reason"]


def test_scan_trusted_host_bypasses_model(client, monkeypatch):
    def _fail_if_called(*args, **kwargs):
        raise AssertionError("should not be called for a trusted host")

    async def _async_fail_if_called(*args, **kwargs):
        raise AssertionError("should not be called for a trusted host")

    monkeypatch.setattr(scan_module, "predict", _fail_if_called)
    monkeypatch.setattr(scan_module, "check_urlhaus", _async_fail_if_called)
    monkeypatch.setattr(scan_module, "check_domain_age", _async_fail_if_called)

    response = client.post("/scan", json={"url": "http://localhost:5173/", "client_id": CLIENT_ID})
    assert response.status_code == 200
    body = response.json()
    assert body["is_phishing"] is False
    assert body["ml_score"] is None
    assert body["urlhaus_status"] is None
    assert body["domain_age_status"] is None
    assert "Trusted" in body["verdict_reason"]


def test_scan_domain_age_unknown_is_noted_in_reason(client):
    # Default conftest fake already returns "unknown" -- confirm it's
    # surfaced rather than silently ignored.
    response = client.post("/scan", json={"url": "http://google.com", "client_id": CLIENT_ID})
    assert response.status_code == 200
    assert "domain age unavailable" in response.json()["verdict_reason"]


def test_scan_runs_threat_intel_lookups_concurrently(client, monkeypatch):
    # Run one after the other, the two lookups stack their 4s timeouts and a
    # single slow scan takes 8s+. Rather than time the request (flaky), count
    # how many lookups are in flight at once: awaited sequentially the peak is
    # 1, gathered it's 2.
    state = {"in_flight": 0, "peak": 0}

    async def _tracked(result):
        state["in_flight"] += 1
        state["peak"] = max(state["peak"], state["in_flight"])
        await asyncio.sleep(0.05)
        state["in_flight"] -= 1
        return result

    async def _slow_urlhaus(url: str) -> str:
        return await _tracked("not_listed")

    async def _slow_domain_age(url: str) -> dict:
        return await _tracked({"domain_age_days": None, "domain_age_status": "unknown"})

    monkeypatch.setattr(scan_module, "check_urlhaus", _slow_urlhaus)
    monkeypatch.setattr(scan_module, "check_domain_age", _slow_domain_age)

    response = client.post("/scan", json={"url": "http://google.com", "client_id": CLIENT_ID})
    assert response.status_code == 200
    assert state["peak"] == 2
