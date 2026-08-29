"""Domain-registration-age lookup via RDAP -- the modern, JSON-based
successor to WHOIS, picked over parsing raw WHOIS text. Targets the ceiling
of the lexical-only ML model: an old, established domain like `github.com`
serving an unusual-looking path shouldn't be judged the same way as a
lookalike domain registered last week.

Same best-effort contract as urlhaus.py: a domain not found, an unsupported
TLD (RDAP coverage isn't universal), a timeout, or
any network error all fall back to "unknown" rather than blocking /scan.

**Snag hit and fixed in live testing**: `whodap.aio_lookup_domain()`
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
boundaries. Failed lookups are deliberately *not* cached -- see
check_domain_age below.
"""

import asyncio
from datetime import datetime, timezone

import httpx
import tldextract
import whodap

from backend.app.threat_intel.cache import TTLCache

TIMEOUT_SECONDS = 4.0
NEW_DOMAIN_THRESHOLD_DAYS = 30
ESTABLISHED_DOMAIN_THRESHOLD_DAYS = 365
CACHE_TTL_SECONDS = 24 * 60 * 60

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
        return {"domain_age_days": None, "domain_age_status": "unknown"}

    cache_key = f"{extracted.domain}.{extracted.suffix}"
    cached = _cache.get(cache_key)
    if cached is not None:
        return cached

    result = await _lookup_domain_age(extracted.domain, extracted.suffix)
    # Only cache a real answer. Caching "unknown" would let one transient
    # timeout blind the domain-age signal for a full 24 hours -- and this
    # signal is exactly what rescues established domains from a false
    # positive, so a cached failure costs a wrong verdict, not just a
    # missing field. (urlhaus.py caches its "unknown" on purpose: its TTL
    # is 15 minutes, short enough that throttling a down API wins.)
    if result["domain_age_status"] != "unknown":
        _cache.set(cache_key, result)
    return result


async def _lookup_domain_age(domain: str, suffix: str) -> dict:
    try:
        client = await asyncio.wait_for(_get_client(), timeout=TIMEOUT_SECONDS)
        response = await asyncio.wait_for(
            client.aio_lookup(domain, suffix),
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
