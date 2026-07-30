# PhishGuard — TODO

## Milestone 2 — Dataset collection & cleaning (done)
- [x] Download Tranco Top 1M list, sample 65,000 legitimate URLs
- [x] Obtain PhishTank dataset, sample 65,000 phishing URLs
- [x] Clean and normalize both sources (dedupe, consistent URL format)
- [x] Merge into a single labeled dataset, save to `ml/data/processed/`
- [x] Quick sanity EDA (class balance, obvious data quality issues)

## Milestone 3 — Feature engineering (done)
- [x] Design lexical/domain/statistical URL features
- [x] Implement shared `ml/features.py` (importable by both `ml/` and `backend/`)
- [x] Unit tests for feature extraction

## Milestone 4 — Model training & evaluation (done)
- [x] Train Logistic Regression, Random Forest, XGBoost baselines
- [x] Compare on held-out set, pick winner (target >=95% accuracy) — XGBoost won, 96.5% accuracy / 0.9653 F1
- [x] Export model artifact to `ml/models/`
- [x] Write metrics/comparison report (`ml/MODEL_REPORT.md`)

## Milestone 5 — Backend core (`/scan`) (done)
- [x] FastAPI app skeleton in `backend/app/`
- [x] Pydantic request/response schemas
- [x] `/scan` endpoint: extract features, run ML inference, return verdict
- [x] Basic tests (4 tests, `TestClient`)

## Milestone 6 — Persistence layer (done)
- [x] SQLAlchemy models for scan history (`ScanRecord`)
- [x] `/history` endpoint (most recent first, `?limit=`)
- [x] `/reports` endpoint + CSV export

## Milestone 7 — Chrome Extension MVP (done)
- [x] Manifest V3 `manifest.json`
- [x] Background service worker calling `/scan` on navigation
- [x] Popup UI showing verdict

## Milestone 8 — React Dashboard (done)
- [x] Scan history table
- [x] One simple stats chart (verdict breakdown: phishing vs legit counts)
- [x] Report export UI (Tailwind styling)

## Milestone 8 follow-up — model false-positive fix (done)
- [x] Diagnose `mail.google.com`/`github.com/anthropics` false positives
      (feature-contribution analysis, not guessing)
- [x] Rewrite synthetic legit-URL path/subdomain generation in
      `ml/prepare_dataset.py` to close the coverage gaps found
- [x] Systematic audit for remaining phishing-only feature values, regenerate
      dataset, retrain — XGBoost now 94.08% acc / 0.9401 F1 (down from
      96.51%, expected: that number was inflated by the same artifact class)
- [x] Re-verify against 15 real legit + 7 real-shaped phishing URLs, all 18
      existing unit tests still pass

## Milestone 8 extension re-test (done, 2026-07-31)
- [x] Restarted backend with retrained model, confirmed extension code
      itself needs no changes (it only calls `/scan`, model lives server-side)
- [x] Re-tested 3 real navigations through the actual loaded Chrome
      extension (not just direct model calls): `github.com/anthropics`
      (83.8% phishing, matches direct test — known residual case, see
      below), a real Reddit thread (99.9% legit, previously a false
      positive — confirmed fixed on real traffic, not just the synthetic
      test string), and a fake PayPal phishing URL (99.98% phishing,
      confirms recall intact)

## Decision, 2026-07-31: reversing part of the "pure ML classifier" scope
call. Project will add a threat-intel/forensics layer after all — see
`PROJECT_PROGRESS.md` for the comparison of options considered
(typosquat feature vs URLhaus vs VirusTotal vs WHOIS vs Google Safe
Browsing) and why.

## Next up — Milestone 10: typosquatting + URLhaus (in progress)
- [ ] Typosquat/brand-similarity feature: edit-distance from the URL's
      domain to a small curated list of well-known brand domains; new
      feature in `ml/features.py`, retrain
- [ ] URLhaus blocklist check called from `/scan` (no API key needed for
      basic lookups) — needs `/scan` to become async with a timeout +
      graceful fallback to ML-only verdict if the call fails/times out
- [ ] Combine ML score + typosquat flag + URLhaus hit into one explainable
      verdict (not just a single raw ML confidence number) — the bigger
      value-add of this milestone, shows *why* a verdict was reached
- [ ] Later, once the above lands: WHOIS domain-age signal (deliberately
      last — slowest/flakiest network call, easiest to bolt on once the
      combine/fallback logic already exists)
- [ ] Final README pass, screenshots/demo for resume (still last)
- [ ] LICENSE file has a placeholder `<Your Name>` — replace with your actual name.

## Known issues / open items
- A residual few bare-domain-plus-generic-path legit URLs
  (`github.com/anthropics`, `linkedin.com/in/...`) still land borderline
  (55-85% confidence) rather than confidently correct. Confirmed via
  systematic audit this is *not* a data artifact — it's the genuine
  ceiling of a 17-feature lexical-only classifier with no domain
  age/reputation/whois signal. This is exactly what Milestone 10's
  typosquat feature + WHOIS domain age are meant to address (a brand-
  similarity match or an old domain-age reading would resolve
  `github.com/anthropics` directly) — not worth chasing further by
  hand-tuning synthetic data to specific adversarial examples.
- Dashboard dev server's Vite was pinned to `^5.4.20` (not the newer
  rolldown-powered Vite 8 that `npm create vite@latest` installs by
  default) — that version requires Node `^20.19` or `>=22.12` and its
  native rolldown binding failed to load on this machine's Node v20.12.2.
  Revisit the pin if the dev machine's Node version is upgraded.
