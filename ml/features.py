"""Shared URL feature extraction.

Imported by both the offline training pipeline (`ml/train.py`) and the
live backend (`backend/app/ml_service`) so the exact same features are
computed at training time and at inference time — the model never sees a
feature at serving time that it wasn't trained on, or vice versa.

All features are simple lexical/domain/statistical properties of the URL
string itself (no network calls, no external lookups) — that's what keeps
inference fast and the whole pipeline easy to reason about.
"""

import re
from urllib.parse import urlparse

import tldextract

# Words phishing pages commonly use to look legitimate/urgent.
SUSPICIOUS_WORDS = [
    "login",
    "verify",
    "account",
    "secure",
    "update",
    "confirm",
    "signin",
    "bank",
    "password",
    "billing",
    "suspend",
]

# A handful of well-known URL shorteners; phishers use these to hide the
# real destination domain.
URL_SHORTENERS = {
    "bit.ly",
    "tinyurl.com",
    "goo.gl",
    "t.co",
    "ow.ly",
    "is.gd",
    "buff.ly",
    "adf.ly",
    "cutt.ly",
    "rebrand.ly",
}

IP_ADDRESS_RE = re.compile(r"^(\d{1,3}\.){3}\d{1,3}$")

# Fixed order so training and serving always build the feature vector the
# same way.
FEATURE_NAMES = [
    "url_length",
    "hostname_length",
    "path_length",
    "num_dots",
    "num_hyphens",
    "num_underscores",
    "num_slashes",
    "num_digits",
    "num_special_chars",
    "num_subdomains",
    "has_ip_address",
    "has_at_symbol",
    "is_https",
    "digit_ratio",
    "num_query_params",
    "has_suspicious_word",
    "is_url_shortener",
]


def extract_features(url: str) -> dict:
    """Compute the feature dict for a single URL."""
    parsed = urlparse(url)
    hostname = parsed.hostname or ""
    ext = tldextract.extract(url)

    num_letters = sum(c.isalpha() for c in url)
    num_digits = sum(c.isdigit() for c in url)

    return {
        "url_length": len(url),
        "hostname_length": len(hostname),
        "path_length": len(parsed.path),
        "num_dots": url.count("."),
        "num_hyphens": url.count("-"),
        "num_underscores": url.count("_"),
        "num_slashes": url.count("/"),
        "num_digits": num_digits,
        "num_special_chars": sum(not c.isalnum() for c in url),
        "num_subdomains": len(ext.subdomain.split(".")) if ext.subdomain else 0,
        "has_ip_address": int(bool(IP_ADDRESS_RE.match(hostname))),
        "has_at_symbol": int("@" in url),
        "is_https": int(parsed.scheme == "https"),
        "digit_ratio": num_digits / num_letters if num_letters else 0.0,
        "num_query_params": parsed.query.count("&") + 1 if parsed.query else 0,
        "has_suspicious_word": int(any(word in url.lower() for word in SUSPICIOUS_WORDS)),
        "is_url_shortener": int(ext.top_domain_under_public_suffix in URL_SHORTENERS),
    }


def build_feature_matrix(urls):
    """Vectorized helper for the training pipeline: list/Series of URLs -> DataFrame.

    Only used offline by `ml/train.py` — kept out of the hot inference path
    and out of the backend's dependencies (pandas isn't a serving dependency).
    """
    import pandas as pd

    rows = [extract_features(url) for url in urls]
    return pd.DataFrame(rows, columns=FEATURE_NAMES)
