from datetime import datetime

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


def test_history_timestamps_are_timezone_aware(client):
    # Without an offset, `new Date(...)` in the dashboard parses the string
    # as local time and shows every scan shifted by the viewer's UTC offset.
    client.post("/scan", json={"url": "http://google.com", "client_id": CLIENT_ID})

    scanned_at = client.get(f"/history?client_id={CLIENT_ID}").json()[0]["scanned_at"]
    assert scanned_at.endswith("Z") or "+" in scanned_at[10:]

    parsed = datetime.fromisoformat(scanned_at)
    assert parsed.tzinfo is not None


def test_history_ordering_is_stable_for_same_timestamp_scans(client):
    # Several scans inside one clock tick is the normal case (a page load
    # plus its redirects), and scanned_at alone leaves their order
    # arbitrary -- so a LIMIT could drop a newer row and keep an older one.
    urls = [f"http://burst{i}.com" for i in range(5)]
    for url in urls:
        client.post("/scan", json={"url": url, "client_id": CLIENT_ID})

    full = [r["url"] for r in client.get(f"/history?client_id={CLIENT_ID}").json()]
    limited = [r["url"] for r in client.get(f"/history?client_id={CLIENT_ID}&limit=3").json()]

    assert full == list(reversed(urls))
    assert limited == full[:3]


def test_reports_csv_timestamps_carry_a_utc_offset(client):
    client.post("/scan", json={"url": "http://google.com", "client_id": CLIENT_ID})

    row = client.get(f"/reports?client_id={CLIENT_ID}").text.strip().splitlines()[1]
    scanned_at = row.rsplit(",", 1)[-1]
    assert datetime.fromisoformat(scanned_at).tzinfo is not None
