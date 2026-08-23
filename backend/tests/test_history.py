CLIENT_ID = "test-client"
OTHER_CLIENT_ID = "other-client"


def test_history_empty_by_default(client):
    response = client.get(f"/history?client_id={CLIENT_ID}")
    assert response.status_code == 200
    assert response.json() == []


def test_scan_then_appears_in_history(client):
    client.post("/scan", json={"url": "http://google.com", "client_id": CLIENT_ID})

    response = client.get(f"/history?client_id={CLIENT_ID}")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["url"] == "http://google.com"
    assert "scanned_at" in body[0]


def test_history_respects_limit(client):
    for i in range(3):
        client.post("/scan", json={"url": f"http://example{i}.com", "client_id": CLIENT_ID})

    response = client.get(f"/history?client_id={CLIENT_ID}&limit=2")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_history_only_returns_own_client_id(client):
    client.post("/scan", json={"url": "http://mine.com", "client_id": CLIENT_ID})
    client.post("/scan", json={"url": "http://theirs.com", "client_id": OTHER_CLIENT_ID})

    response = client.get(f"/history?client_id={CLIENT_ID}")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["url"] == "http://mine.com"


def test_reports_csv_export(client):
    client.post("/scan", json={"url": "http://google.com", "client_id": CLIENT_ID})

    response = client.get(f"/reports?client_id={CLIENT_ID}")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "url" in response.text
    assert "google.com" in response.text


def test_reports_csv_empty_still_has_header(client):
    response = client.get(f"/reports?client_id={CLIENT_ID}")
    assert response.status_code == 200
    assert (
        response.text.strip()
        == "id,client_id,url,is_phishing,confidence,ml_score,urlhaus_status,domain_age_days,"
        "domain_age_status,verdict_reason,scanned_at"
    )
