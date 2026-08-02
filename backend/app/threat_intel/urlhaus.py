"""Live blocklist lookup against abuse.ch's URLhaus.

Picked over VirusTotal (free tier is rate-limited too tightly for a "scan
every page browsed" use case) -- see PROJECT_PROGRESS.md for the comparison.
abuse.ch added a required `Auth-Key` header across their APIs after that
comparison was made; the key is still free (sign up at auth.abuse.ch) and is
read from the `URLHAUS_AUTH_KEY` env var via `.env` (gitignored, never
committed).

This is a best-effort signal, not a dependency /scan can block on: a missing
key, network error, or timeout all fall back to "unknown" so a slow,
unreachable, or unconfigured URLhaus never prevents a verdict from coming
back.
"""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

URLHAUS_API_URL = "https://urlhaus-api.abuse.ch/v1/url/"
TIMEOUT_SECONDS = 4.0


async def check_urlhaus(url: str) -> str:
    """Returns "listed", "not_listed", or "unknown" (lookup failed)."""
    auth_key = os.environ.get("URLHAUS_AUTH_KEY")
    if not auth_key:
        return "unknown"

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
            response = await client.post(
                URLHAUS_API_URL,
                data={"url": url},
                headers={"Auth-Key": auth_key},
            )
            response.raise_for_status()
            body = response.json()
    except (httpx.HTTPError, ValueError):
        return "unknown"

    return "listed" if body.get("query_status") == "ok" else "not_listed"
