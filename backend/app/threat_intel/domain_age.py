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

Results are also cached for 24 hours, keyed by registrable domain (not the
full URL -- age is a property of the domain, so every path on the same
domain shares one entry). Long TTL is safe here: a domain's creation date
never changes, and its age bucket only matters near the 30/365-day
boundaries.

That reasoning only holds for a *successful* lookup, though. A failed one
("unknown") is cached for 5 minutes instead: a creation date never changes,
but a timeout is a property of that one moment, and caching it for 24 hours
would mean a single slow RDAP call costs a domain its age signal for the
rest of the day.
"""

import asyncio
from datetime import datetime, timezone

import tldextract
import whodap

from backend.app.threat_intel.cache import TTLCache

TIMEOUT_SECONDS = 4.0
NEW_DOMAIN_THRESHOLD_DAYS = 30
ESTABLISHED_DOMAIN_THRESHOLD_DAYS = 365
CACHE_TTL_SECONDS = 24 * 60 * 60
FAILURE_CACHE_TTL_SECONDS = 5 * 60

UNKNOWN_RESULT = {"domain_age_days": None, "domain_age_status": "unknown"}

_client: whodap.DNSClient | None = None
_client_lock = asyncio.Lock()
# Keyed by registrable domain, not the full URL -- age is a property of the
# domain, so /login and /account on the same domain share one cache entry.
_cache = TTLCache(ttl_seconds=CACHE_TTL_SECONDS)


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
        return dict(UNKNOWN_RESULT)

    cache_key = f"{extracted.domain}.{extracted.suffix}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    result = await _lookup_domain_age(extracted.domain, extracted.suffix)
    failed = result["domain_age_status"] == "unknown"
    _cache.set(cache_key, result, ttl_seconds=FAILURE_CACHE_TTL_SECONDS if failed else None)
    return result


async def _lookup_domain_age(domain: str, suffix: str) -> dict:
    # Deliberately broad, and deliberately covering the parsing below as
    # well as the network calls. RDAP responses are not uniform across
    # registries -- `to_whois_dict()` can raise, and `created_date` comes
    # back as a string (rather than a datetime) from some of them. Every
    # one of those is "we could not determine the age", not a reason to
    # 500 a scan the ML model can still answer. (`Exception` rather than an
    # explicit tuple also sidesteps asyncio.TimeoutError only being an alias
    # for builtin TimeoutError on Python 3.11+. CancelledError is a
    # BaseException, so real cancellation still propagates.)
    try:
        client = await asyncio.wait_for(_get_client(), timeout=TIMEOUT_SECONDS)
        response = await asyncio.wait_for(
            client.aio_lookup(domain, suffix),
            timeout=TIMEOUT_SECONDS,
        )

        creation_date = response.to_whois_dict().get("created_date")
        if not isinstance(creation_date, datetime):
            return dict(UNKNOWN_RESULT)

        # Some registries return a naive datetime (no tzinfo) -- assume UTC
        # rather than letting the subtraction below raise.
        if creation_date.tzinfo is None:
            creation_date = creation_date.replace(tzinfo=timezone.utc)

        age_days = (datetime.now(timezone.utc) - creation_date).days
    except Exception:
        return dict(UNKNOWN_RESULT)

    # A creation date in the future means the registry gave us something we
    # can't reason about; don't let it fall into the "new" bucket.
    if age_days < 0:
        return dict(UNKNOWN_RESULT)

    if age_days < NEW_DOMAIN_THRESHOLD_DAYS:
        status = "new"
    elif age_days >= ESTABLISHED_DOMAIN_THRESHOLD_DAYS:
        status = "established"
    else:
        status = "moderate"

    return {"domain_age_days": age_days, "domain_age_status": status}
