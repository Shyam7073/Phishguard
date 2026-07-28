def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_scan_returns_verdict(client):
    response = client.post("/scan", json={"url": "http://google.com"})
    assert response.status_code == 200
    body = response.json()
    assert body["url"] == "http://google.com"
    assert isinstance(body["is_phishing"], bool)
    assert 0.0 <= body["confidence"] <= 1.0


def test_scan_flags_ip_address_login_url(client):
    response = client.post("/scan", json={"url": "http://192.168.1.1/login/verify-account"})
    assert response.status_code == 200
    assert response.json()["is_phishing"] is True


def test_scan_rejects_empty_url(client):
    response = client.post("/scan", json={"url": ""})
    assert response.status_code == 422
