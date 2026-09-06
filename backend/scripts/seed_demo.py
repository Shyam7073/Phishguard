"""Seeds the reserved `demo` client_id so the deployed dashboard shows a
populated history to anyone opening the link without the extension.

Every row is produced by the real pipeline -- the same predict() +
check_urlhaus() + check_domain_age() + combine_verdict() calls /scan makes
-- so the demo is genuine model output, not hand-written fixture data. Only
the timestamps are synthetic, spread over the last few days so the table
reads like a browsing session instead of one bulk insert.

The dashboard does NOT depend on this script: what someone without the
extension sees is dashboard/src/demoData.json, a fixed checked-in fixture
that renders with no backend involved (the API is on a free tier that spins
down when idle, and a cold start is far longer than anyone opening a link
off a resume will wait). This script is the optional server-side version --
seed the demo id and the dashboard picks those rows up live instead. It
deliberately does not write demoData.json, so re-running can't clobber the
fixture.

Run against local SQLite (safe, what you want for regenerating the snapshot):
    DATABASE_URL="" .venv/bin/python -m backend.scripts.seed_demo

Run against the deployed Neon database (DATABASE_URL from .env). Both the
env var and the flag are required: database.py withholds the deployed
database from a dev machine unless PHISHGUARD_DEPLOYED is set, and this
script additionally refuses to touch it without --deployed.
    PHISHGUARD_DEPLOYED=1 .venv/bin/python -m backend.scripts.seed_demo --deployed
"""

import argparse
import asyncio
import os
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import desc

from backend.app.db.database import Base, SessionLocal, engine
from backend.app.db.models import ScanRecord
from backend.app.demo import DEMO_CLIENT_ID
from backend.app.ml_service.predictor import predict
from backend.app.threat_intel.domain_age import check_domain_age
from backend.app.threat_intel.urlhaus import check_urlhaus
from backend.app.verdict import combine_verdict

URLHAUS_RECENT_URL = "https://urlhaus-api.abuse.ch/v1/urls/recent/limit/5/"
HOURS_BETWEEN_SCANS = 7
# RDAP servers are flaky enough that a single 4s attempt occasionally comes
# back "unknown" for a domain that plainly has a creation date. That's fine
# at serving time (the verdict degrades gracefully), but this is offline
# batch work seeding a showcase, so it's worth being patient. Failed lookups
# aren't cached, so a retry really does re-query.
DOMAIN_AGE_ATTEMPTS = 3

# Ordinary browsing, plus the cases that make the verdict policy visible in
# the table: an IP-literal login page and a shortener (both flagged on
# lexical shape alone), and github.com/anthropics + twitter.com/anthropicai,
# the exact false positives the domain-age rescue in verdict.py exists for
# (see MODEL_REPORT.md). The last two are illustrative phishing *shapes*,
# not live sites -- what's real is the verdict the model returns for them.
DEMO_URLS = [
    "https://www.google.com/search?q=phishing+detection",
    "https://github.com/anthropics",
    "https://mail.google.com/mail/u/0/",
    "https://en.wikipedia.org/wiki/Phishing",
    "https://twitter.com/anthropicai",
    "https://docs.python.org/3/library/asyncio.html",
    "https://www.amazon.in/gp/css/order-history",
    "http://192.168.0.1/login/verify-account.php",
    "https://bit.ly/3xR9kQm",
    "http://secure-login-appleid-verify.tk/account/billing/update.php",
]


async def recent_urlhaus_urls(limit: int = 3) -> list[str]:
    """URLs on the blocklist *right now*, so the demo shows the URLhaus
    override branch with a genuine hit rather than a stale hard-coded one.

    Best-effort, same as the lookup itself: no key or no network just means
    the demo leans on the ML-only rows.
    """
    auth_key = os.environ.get("URLHAUS_AUTH_KEY")
    if not auth_key:
        return []
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(URLHAUS_RECENT_URL, headers={"Auth-Key": auth_key})
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError):
        return []
    return [entry["url"] for entry in payload.get("urls", [])[:limit] if entry.get("url")]


async def lookup_domain_age_patiently(url: str) -> dict:
    for attempt in range(DOMAIN_AGE_ATTEMPTS):
        result = await check_domain_age(url)
        if result["domain_age_status"] != "unknown":
            return result
        if attempt < DOMAIN_AGE_ATTEMPTS - 1:
            await asyncio.sleep(1.0)
    return result


async def scan_all(urls: list[str]) -> list[ScanRecord]:
    now = datetime.now(timezone.utc)
    rows = []
    for offset, url in enumerate(urls):
        ml_result = predict(url)
        urlhaus_status = await check_urlhaus(url)
        domain_age = await lookup_domain_age_patiently(url)
        verdict = combine_verdict(
            ml_result["phishing_probability"], urlhaus_status, domain_age["domain_age_status"]
        )
        print(f"  {url[:70]:<70} -> {verdict['verdict_reason'][:50]}")
        rows.append(
            ScanRecord(
                client_id=DEMO_CLIENT_ID,
                url=url,
                is_phishing=verdict["is_phishing"],
                confidence=verdict["confidence"],
                ml_score=ml_result["phishing_probability"],
                urlhaus_status=urlhaus_status,
                domain_age_days=domain_age["domain_age_days"],
                domain_age_status=domain_age["domain_age_status"],
                verdict_reason=verdict["verdict_reason"],
                scanned_at=now - timedelta(hours=offset * HOURS_BETWEEN_SCANS),
            )
        )
    return rows


async def build_rows(extra_urls: list[str]) -> list[ScanRecord]:
    # The recent-URLs feed lives on the same host as the lookup API, so when
    # that host is down (expired cert, outage) there's no automatic source of
    # currently-blocklisted URLs. --url is the manual fallback: pick them off
    # urlhaus.abuse.ch yourself, but let the pipeline judge them.
    listed = await recent_urlhaus_urls()
    return await scan_all(DEMO_URLS + listed + extra_urls)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--deployed",
        action="store_true",
        help="Required to write to a non-SQLite (i.e. the deployed Neon) database.",
    )
    parser.add_argument(
        "--url",
        action="append",
        default=[],
        metavar="URL",
        help=(
            "Extra URL to scan into the demo, repeatable. Useful for adding "
            "known-blocklisted URLs read off urlhaus.abuse.ch by hand when the "
            "recent-URLs API is unreachable -- the URL is picked manually, but "
            "the verdict is still whatever the real pipeline returns."
        ),
    )
    args = parser.parse_args()

    is_sqlite = engine.url.get_backend_name() == "sqlite"
    if not is_sqlite and not args.deployed:
        parser.error(
            f"DATABASE_URL points at {engine.url.get_backend_name()} "
            f"({engine.url.host}) -- pass --deployed to seed it, or run with "
            'DATABASE_URL="" to seed a local SQLite file instead.'
        )
    if is_sqlite and args.deployed:
        # Without this, the dev-machine guard in database.py would hand back a
        # SQLite engine and --deployed would quietly seed the wrong database.
        parser.error(
            "--deployed was passed but the engine resolved to local SQLite. "
            "The dev-machine guard in backend/app/db/database.py withholds the "
            "deployed database unless you opt in explicitly -- re-run as:\n"
            "    PHISHGUARD_DEPLOYED=1 .venv/bin/python -m backend.scripts.seed_demo --deployed"
        )

    print(f"Seeding '{DEMO_CLIENT_ID}' history into {engine.url.get_backend_name()}...")
    Base.metadata.create_all(bind=engine)
    rows = asyncio.run(build_rows(args.url))

    db = SessionLocal()
    try:
        removed = db.query(ScanRecord).filter(ScanRecord.client_id == DEMO_CLIENT_ID).delete()
        db.add_all(rows)
        db.commit()

        stored = (
            db.query(ScanRecord)
            .filter(ScanRecord.client_id == DEMO_CLIENT_ID)
            .order_by(desc(ScanRecord.scanned_at))
            .all()
        )
    finally:
        db.close()

    # A --url passed for its blocklist status is worse than useless if the
    # lookup didn't land: URLhaus payload URLs are lexically unremarkable, so
    # without the hit they seed as "Looks safe" -- a false negative on a known
    # malicious URL, sitting in the showcase.
    missed = [row.url for row in stored if row.url in args.url and row.urlhaus_status != "listed"]
    if missed:
        print("\nWARNING: URLhaus did not confirm these --url entries:")
        for url in missed:
            print(f"  {url}")
        print(
            "They are seeded with whatever the ML model said on its own. If you "
            "added them for the blocklist branch, re-run once URLhaus answers."
        )

    phishing = sum(1 for row in stored if row.is_phishing)
    print(
        f"\nReplaced {removed} row(s) with {len(stored)} "
        f"({phishing} phishing / {len(stored) - phishing} legitimate)."
    )
    if not is_sqlite:
        print("Seeded the deployed database -- the dashboard will serve these live.")


if __name__ == "__main__":
    main()
