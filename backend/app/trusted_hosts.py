"""Allowlist for PhishGuard's own first-party hosts.

The lexical ML model has no notion of "this domain is us" -- it judges
every URL purely on lexical shape, so it can (and does) misfire on
PhishGuard's own dashboard, the same way it misfires on any other
hyphenated free-hosting subdomain (see MODEL_REPORT.md / verdict.py for
the broader false-positive class). Rather than fight the model with more
features or retraining, a short explicit allowlist of our own hosts is
simpler and more honest: we already know these are safe, no inference
needed.
"""

import os

_DEV_HOSTS = {"localhost", "127.0.0.1"}


def _load_trusted_hosts() -> set[str]:
    extra = os.environ.get("TRUSTED_HOSTS", "")
    extra_hosts = {h.strip().lower() for h in extra.split(",") if h.strip()}
    return _DEV_HOSTS | extra_hosts


TRUSTED_HOSTS = _load_trusted_hosts()


def is_trusted_host(hostname: str | None) -> bool:
    return bool(hostname) and hostname.lower() in TRUSTED_HOSTS
