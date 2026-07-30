"""Milestone 2: build a labeled URL dataset from raw Tranco + PhishTank sources.

Reads ml/data/raw/tranco_XN23N.csv (legitimate domains) and
ml/data/raw/verified_online.csv (PhishTank phishing URLs), samples 65k of
each, cleans/dedupes, merges into one labeled CSV, and prints a quick EDA.

Run with: .venv/bin/python ml/prepare_dataset.py
"""

import string
from pathlib import Path

import numpy as np
import pandas as pd

RAW_DIR = Path(__file__).parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).parent / "data" / "processed"
SAMPLE_SIZE = 65_000
SEED = 42

# Tranco only gives bare domains, but real browsing obviously hits pages
# with paths/query strings too (google.com/search?q=..., not just
# google.com). Without this, every legit URL would have path_length == 0
# while ~94% of phishing URLs have a path -- the model would then just
# learn "has a path -> phishing", a fake signal from how the dataset was
# built, not a real phishing pattern (and it would misfire on almost every
# real legitimate page visited through the Chrome extension later).
#
# Bug found post-Milestone-8 (dashboard smoke test), and it took two
# attempts to actually fix: a first pass just added a fixed list of longer
# path *templates* (literal strings). That helped some cases but not all --
# https://mail.google.com/mail/u/0/ got fixed, but
# https://twitter.com/anthropicai still misfired. Digging into XGBoost's
# per-feature contribution for that one showed `path_length` alone
# contributing +8 toward "phishing", because a *fixed* template list only
# ever produces a handful of discrete path_length values (however many
# templates you write), never a smooth range -- real dynamic path segments
# (usernames, video IDs, doc IDs, hashes) vary in length every single time,
# so a handful of literal examples still leaves gaps a tree model can carve
# a spurious "legit never has this length/slash-count" rule around.
#
# Fixed properly below with a small generator instead of a fixed list:
# each path is built from a random number of segments (so num_slashes
# varies smoothly, including a real tail into deep multi-segment routes
# like Gmail/Docs/GitHub/admin dashboards -- not capped at 2-3 segments),
# where each segment is either a common route word or a random-length
# alphanumeric token (mimicking real usernames/slugs/hashes/video-ids).
PATH_WORDS = [
    "about", "contact", "login", "search", "products", "category",
    "electronics", "laptops", "blog", "user", "settings", "api", "v1", "v2",
    "users", "images", "docs", "getting-started", "checkout", "cart",
    "news", "help", "faq", "account", "profile", "watch", "index", "support",
    "mail", "document", "edit", "dashboard", "reports", "orders", "invoice",
    "issues", "pull", "tree", "blob", "main", "releases", "compare",
    "notifications", "messages", "tickets", "videos", "tutorials",
    "advanced",
]  # fmt: skip

# Non-blank query strings only -- how often a query string gets appended at
# all is controlled separately below (see _random_path), not by list
# composition, so the rate is exact and auditable rather than "count the
# blanks in a list until the ratio looks right" (that's exactly how the
# first pass at this function got the rate backwards -- see below).
QUERY_STRINGS = [
    "?q=weather",
    "?page=1&limit=20",
    "?tab=security",
    "?v=dQw4w9WgXcQ",
    "?id=12345",
    "?ref=homepage",
    # A couple of 3-4 param strings too -- without these, `num_query_params`
    # of 3+ only ever showed up in phishing rows (tracking-heavy links),
    # which isn't realistic (UTM params, pagination+filter combos, etc. are
    # everyday legit query strings).
    "?utm_source=newsletter&utm_medium=email&utm_campaign=spring",
    "?category=laptops&sort=price&page=2&in_stock=true",
]

_ALPHABET = list(string.ascii_letters + string.digits)

# Path depth in "/"-separated segments, weighted toward shallow (typical
# browsing) but with a real tail into deep routes -- unlike the old fixed
# template list, depth 4+ (which is where num_slashes >= 6 lives) is a
# regular occurrence here, not something that only appears in phishing URLs.
_DEPTH_WEIGHTS = [0.08, 0.28, 0.27, 0.17, 0.10, 0.06, 0.03, 0.01]


def _random_segment(rng: np.random.Generator) -> str:
    roll = rng.random()
    if roll < 0.45:
        # A single route word (about, login, docs, ...).
        return rng.choice(PATH_WORDS)
    if roll < 0.65:
        # A multi-word slug (best-practices, how-to-fix-a-bug, some_title,
        # ...) -- real blog/SEO/docs/Reddit-style URLs are full of these,
        # joined by either a hyphen or an underscore. Without this branch
        # `num_hyphens`/`num_underscores` in legit paths would stay
        # near-zero (single PATH_WORDS entries rarely have either), making
        # "2+ hyphens" or "any underscore at all" look like a phishing-only
        # pattern even though both are everyday slug shapes.
        word_count = rng.integers(2, 5)
        separator = "-" if rng.random() < 0.7 else "_"
        return separator.join(rng.choice(PATH_WORDS) for _ in range(word_count))
    # A variable-length random alphanumeric token (mimicking real
    # usernames/slugs/hashes/video-ids, which differ in length every time).
    length = rng.integers(3, 25)
    return "".join(rng.choice(_ALPHABET, size=length))


def _random_path(rng: np.random.Generator) -> str:
    depth = rng.choice(len(_DEPTH_WEIGHTS), p=_DEPTH_WEIGHTS)
    if depth == 0:
        path = rng.choice(["", "/"])
    else:
        segments = [_random_segment(rng) for _ in range(depth)]
        path = "/" + "/".join(segments)
        if rng.random() < 0.15:
            path += "/"
    # Real PhishTank phishing URLs have no query string ~84% of the time
    # (a bare suspicious path is enough) -- legit browsing needs to match
    # that same "mostly no query string" shape, or `num_query_params == 0`
    # ends up *more* associated with phishing than legit and inverts the
    # signal the model should be learning.
    if rng.random() < 0.2:
        path += rng.choice(QUERY_STRINGS)
    return path

# Same reasoning as PATH_TEMPLATES: Tranco domains are bare apex domains, so
# without this every legit URL would have num_subdomains == 0 while ~71% of
# phishing URLs have one (attackers abuse subdomains on compromised/free
# hosting since they can't easily buy an exact-match domain). Left alone,
# the model would learn "any subdomain -> phishing", which would misfire on
# everyday legitimate URLs like www.google.com or mail.google.com. "www" is
# repeated to weight it as the most common real-world subdomain.
#
# Bug found post-Milestone-8: "" (no subdomain) was only 13% of this list,
# so bare-domain URLs (num_subdomains == 0) were under-represented in legit
# training rows (13%) versus phishing rows (29%) -- the model leaned
# "no subdomain -> phishing" and misfired on https://github.com/anthropics.
# Bare-domain browsing (github.com/user, twitter.com/handle) is extremely
# common in practice, so "" is now weighted equally with "www" (25% each)
# instead of being the rare case.
SUBDOMAIN_TEMPLATES = [
    "",
    "",
    "",
    "",
    "",
    "www",
    "www",
    "www",
    "www",
    "www",
    "mail",
    "blog",
    "shop",
    "support",
    "app",
    "docs",
    "news",
    "m",
    "en",
    "api",
    # A couple of two-level subdomains (m.en, mail.corp, ...) -- without
    # these, `num_subdomains == 2` and `num_dots` of 5-6 only ever showed up
    # in phishing rows, another 0%-vs-real-world gap the same as the ones
    # above.
    "m.en",
    "mail.corp",
    "shop.us",
]


def load_legitimate_urls() -> pd.DataFrame:
    tranco = pd.read_csv(RAW_DIR / "tranco_XN23N.csv", header=None, names=["rank", "domain"])
    tranco = tranco.dropna(subset=["domain"]).drop_duplicates(subset=["domain"])
    sampled = tranco.sample(n=SAMPLE_SIZE, random_state=SEED)

    # Almost all real top-ranked sites serve HTTPS by default today, so
    # "https://" is the realistic scheme choice (see module docstring above
    # for why "http://" would have been a fake signal too).
    rng = np.random.default_rng(SEED)
    subdomains = pd.Series(rng.choice(SUBDOMAIN_TEMPLATES, size=len(sampled)), index=sampled.index)
    paths = pd.Series([_random_path(rng) for _ in range(len(sampled))], index=sampled.index)

    hosts = sampled["domain"].where(subdomains == "", subdomains + "." + sampled["domain"])
    urls = "https://" + hosts + paths
    return pd.DataFrame({"url": urls, "label": 0})


def load_phishing_urls() -> pd.DataFrame:
    phishtank = pd.read_csv(RAW_DIR / "verified_online.csv")
    phishtank = phishtank[(phishtank["verified"] == "yes") & (phishtank["online"] == "yes")]
    phishtank = phishtank.dropna(subset=["url"]).drop_duplicates(subset=["url"])
    sampled = phishtank.sample(n=SAMPLE_SIZE, random_state=SEED)
    return pd.DataFrame({"url": sampled["url"].str.strip(), "label": 1})


def build_dataset() -> pd.DataFrame:
    legit = load_legitimate_urls()
    phishing = load_phishing_urls()
    dataset = pd.concat([legit, phishing], ignore_index=True)
    dataset = dataset.drop_duplicates(subset=["url"])
    return dataset.sample(frac=1, random_state=SEED).reset_index(drop=True)


def run_eda(dataset: pd.DataFrame) -> None:
    print("Class balance:")
    print(dataset["label"].value_counts())
    print(f"\nMissing values: {dataset.isnull().sum().sum()}")
    print(f"Duplicate URLs: {dataset['url'].duplicated().sum()}")

    url_lengths = dataset["url"].str.len()
    print("\nURL length by class:")
    print(dataset.assign(url_length=url_lengths).groupby("label")["url_length"].describe())


def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    dataset = build_dataset()
    run_eda(dataset)

    out_path = PROCESSED_DIR / "dataset.csv"
    dataset.to_csv(out_path, index=False)
    print(f"\nSaved {len(dataset)} rows to {out_path}")


if __name__ == "__main__":
    main()
