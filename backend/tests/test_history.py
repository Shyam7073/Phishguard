def test_history_empty_by_default(client):
    response = client.get("/history")
    assert response.status_code == 200
    assert response.json() == []


def test_scan_then_appears_in_history(client):
    client.post("/scan", json={"url": "http://google.com"})

    response = client.get("/history")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["url"] == "http://google.com"
    assert "scanned_at" in body[0]


def test_history_respects_limit(client):
    for i in range(3):
        client.post("/scan", json={"url": f"http://example{i}.com"})

    response = client.get("/history?limit=2")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_reports_csv_export(client):
    client.post("/scan", json={"url": "http://google.com"})

    response = client.get("/reports")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "url" in response.text
    assert "google.com" in response.text


def test_reports_csv_empty_still_has_header(client):
    response = client.get("/reports")
    assert response.status_code == 200
    assert response.text.strip() == "id,url,is_phishing,confidence,scanned_at"
