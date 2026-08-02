"""Domain-registration-age lookup via RDAP -- the modern, JSON-based
successor to WHOIS (see PROJECT_PROGRESS.md for why RDAP was picked over
parsing raw WHOIS text). Targets the ceiling of the lexical-only ML model
documented in Milestone 8: an old, established domain like `github.com`
serving an unusual-looking path shouldn't be judged the same way as a
lookalike domain registered last week.

Same best-effort contract as urlhaus.py: a domain not found, an unsupported
TLD (RDAP coverage isn't universal -- see PROJECT_PROGRESS.md), a timeout, or
any network error all fall back to "unknown" rather than blocking /scan.

**Snag hit and fixed during Milestone 13**: `whodap.aio_lookup_domain()`
creates a fresh `DNSClient` and re-fetches IANA's RDAP bootstrap registry
(a second network round trip) on every single call -- against real domains
this occasionally pushed a single lookup past a 4s timeout outright (timed
out on both `github.com` and `twitter.com` in live testing). Fixed by
caching one `DNSClient` at module level (bootstrap fetched once, lazily, on
first use) and reusing it -- every call after the first is then a single
RDAP round trip, same shape as the URLhaus call.
"""

import asyncio
from datetime import datetime, timezone

import httpx
import tldextract
import whodap

TIMEOUT_SECONDS = 4.0
NEW_DOMAIN_THRESHOLD_DAYS = 30
ESTABLISHED_DOMAIN_THRESHOLD_DAYS = 365

_client: whodap.DNSClient | None = None
_client_lock = asyncio.Lock()


async def _get_client() -> whodap.DNSClient:
    global _client
    if _client is None:
        async with _client_lock:
            if _client is None:
                _client = await whodap.DNSClient.new_aio_client()
    return _client


async def check_domain_age(url: str) -> dict:
    """Returns {"domain_age_days": int | None, "domain_age_status": str}.

    domain_age_status is one of "new" (<30 days), "established" (>=365
    days), "moderate" (in between), or "unknown" (lookup failed/unavailable).
    """
    extracted = tldextract.extract(url)
    if not extracted.domain or not extracted.suffix:
        return {"domain_age_days": None, "domain_age_status": "unknown"}

    try:
        client = await asyncio.wait_for(_get_client(), timeout=TIMEOUT_SECONDS)
        response = await asyncio.wait_for(
            client.aio_lookup(extracted.domain, extracted.suffix),
            timeout=TIMEOUT_SECONDS,
        )
    except (whodap.errors.WhodapError, NotImplementedError, httpx.HTTPError, TimeoutError):
        return {"domain_age_days": None, "domain_age_status": "unknown"}

    creation_date = response.to_whois_dict().get("created_date")
    if creation_date is None:
        return {"domain_age_days": None, "domain_age_status": "unknown"}

    # Some registries return a naive datetime (no tzinfo) -- assume UTC
    # rather than letting the subtraction below raise.
    if creation_date.tzinfo is None:
        creation_date = creation_date.replace(tzinfo=timezone.utc)

    age_days = (datetime.now(timezone.utc) - creation_date).days

    if age_days < NEW_DOMAIN_THRESHOLD_DAYS:
        status = "new"
    elif age_days >= ESTABLISHED_DOMAIN_THRESHOLD_DAYS:
        status = "established"
    else:
        status = "moderate"

    return {"domain_age_days": age_days, "domain_age_status": status}
