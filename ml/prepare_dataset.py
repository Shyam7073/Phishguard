"""Milestone 2: build a labeled URL dataset from raw Tranco + PhishTank sources.

Reads ml/data/raw/tranco_XN23N.csv (legitimate domains) and
ml/data/raw/verified_online.csv (PhishTank phishing URLs), samples 65k of
each, cleans/dedupes, merges into one labeled CSV, and prints a quick EDA.

Run with: .venv/bin/python ml/prepare_dataset.py
"""

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
# real legitimate page visited through the Chrome extension later). These
# templates add realistic path/query diversity to the legitimate class so
# path-related features reflect genuine phishing lexical patterns instead.
PATH_TEMPLATES = [
    "",
    "/",
    "/about",
    "/contact",
    "/login",
    "/search?q=weather",
    "/products/1234",
    "/blog/2025/best-practices",
    "/category/electronics/laptops",
    "/user/settings",
    "/api/v2/users?page=1&limit=20",
    "/images/logo.png",
    "/docs/getting-started",
    "/checkout/cart",
    "/news/latest-updates",
    "/help/faq",
    "/account/profile?tab=security",
    "/watch?v=dQw4w9WgXcQ",
    "/index.html",
    "/en/support",
]

# Same reasoning as PATH_TEMPLATES: Tranco domains are bare apex domains, so
# without this every legit URL would have num_subdomains == 0 while ~71% of
# phishing URLs have one (attackers abuse subdomains on compromised/free
# hosting since they can't easily buy an exact-match domain). Left alone,
# the model would learn "any subdomain -> phishing", which would misfire on
# everyday legitimate URLs like www.google.com or mail.google.com. "www" is
# repeated to weight it as the most common real-world subdomain.
SUBDOMAIN_TEMPLATES = [
    "",
    "",
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
    paths = pd.Series(rng.choice(PATH_TEMPLATES, size=len(sampled)), index=sampled.index)

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
