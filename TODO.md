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

## Milestone 10a — URLhaus threat intel (done, 2026-07-31)
- [x] `backend/app/threat_intel/urlhaus.py` — async URLhaus lookup,
      4s timeout, falls back to `"unknown"` on any error/timeout/missing key
- [x] `/scan` made async, calls URLhaus alongside the ML model
- [x] `backend/app/verdict.py` — combines ML phishing-probability +
      URLhaus status into one verdict with a human-readable `verdict_reason`
      (a confirmed URLhaus hit overrides the ML score outright)
- [x] `ScanResponse` extended with `ml_score`, `urlhaus_status`,
      `verdict_reason` (kept `is_phishing`/`confidence` for backward compat)
- [x] Tests: 2 new (`urlhaus listed overrides`, `urlhaus unknown falls back`),
      existing tests updated to monkeypatch `check_urlhaus` so the suite
      never makes a real network call. 11/11 passing.
- [x] **Snag hit and fixed:** URLhaus now requires a free `Auth-Key` header
      (added by abuse.ch after the original "no API key needed" comparison
      was made) — got a free key from auth.abuse.ch, stored in `.env`
      (gitignored) as `URLHAUS_AUTH_KEY`, read via `python-dotenv`. Also
      bumped the timeout from 2s to 4s after a cold first request timed out
      in live testing (TLS handshake overhead on the first connection).
- [x] Extension popup + dashboard now show `verdict_reason`/`urlhaus_status`
      (see Milestone 10b below).

## Typosquat/brand-similarity feature — dropped (2026-07-31)
Considered, briefly deferred, then dropped outright. Not planned anymore.

## Milestone 10b — wire URLhaus verdict into the extension + dashboard (done, 2026-07-31)
- [x] `ScanRecord` DB model extended with nullable `ml_score`,
      `urlhaus_status`, `verdict_reason` columns; existing
      `backend/phishguard.db` migrated in place (`ALTER TABLE`, not a
      dropped/recreated DB) so the 25 pre-existing scan rows weren't lost —
      they just show blank/`—` for the new fields, no migrations tool
      (Alembic) needed for a one-off column add
- [x] `/history` (`ScanRecordOut`) and `/reports` CSV both include the 3
      new fields now
- [x] Extension popup (`extension/popup/`) shows the verdict reason and a
      blocklist status badge (🚫 on blocklist / ✓ not listed / unavailable),
      falling back gracefully for anything cached before this change
- [x] Dashboard `HistoryTable` gained "Reason" and "Blocklist" columns,
      status-colored dot + label following the existing dataviz convention
      (never color alone); manually verified in a real browser against the
      real running backend — new scans show live reason/blocklist values,
      old rows show `—` instead of breaking
- [ ] Popup changes not yet re-verified through the actual loaded Chrome
      extension (only reachable by having the user check manually per the
      known browser-automation limitation on `chrome-extension://` pages) —
      ask user to confirm visually

## Milestone 11 — bare-root/trailing-slash false positive fix (done, 2026-08-01)
- [x] Diagnosed real user-reported false positive (`launchpad.ccbp.in/`,
      72.3% phishing) via contribution analysis — `path_length` 0→1 (a bare
      trailing slash) was the dominant driver, caused by `ml/prepare_dataset.py`
      giving legit URLs only ~4% coverage at that value vs phishing's real 30%
- [x] Fixed in two rounds (each re-verified with the by-class audit):
      weighted the blank-vs-slash split 90/10 then 95/5 toward `"/"`, and
      raised bare-root frequency overall from 8%→20% of all legit URLs to
      better match real homepage-visit frequency
- [x] Caught and fixed a second real gap along the way: `path_length==2`
      was 0% for legit (min random path token was 3 chars) — lowered to 1
- [x] Regenerated dataset, retrained, re-verified against the full battery
      of known cases plus other real bare-root sites found in scan history
      (`web.whatsapp.com/`, `leetcode.com/`, `chatgpt.com/`, `youtube.com/`)
      — all now correctly legit, confirms this was a systemic fix, not
      overfit to one URL
- [x] XGBoost now wins the automatic model comparison outright (no manual
      override needed) — final: acc 92.16% / f1 0.9205
- [x] Known trade-off, not hidden: `twitter.com/anthropicai` regressed to
      borderline-wrong (64.7%) — investigated, confirmed a real but modest
      pre-existing skew (`num_subdomains==0`), same "genuine lexical-model
      ceiling" class as `github.com/anthropics`, not chased further

## Milestone 12 — long tracking-param URL false positive fix (done, 2026-08-01)
- [x] Diagnosed real user-reported false positive: a real Google
      address-bar search URL (317 chars, `rlz`/`gs_lcrp`/etc. params)
      scored 99.9996% phishing — `url_length` was the dominant driver;
      legit training URLs never exceeded 213 chars
- [x] Added `_tracking_blob()` to `ml/prepare_dataset.py` — attaches 1-3
      long randomly-sized query params (mimicking real search-engine/OAuth/
      analytics params) to ~10% of legit URLs. First attempt (single param)
      only partially worked (95% still wrong) — `num_special_chars` became
      the new dominant driver; fixed by stacking multiple params per
      occurrence to match real search URLs' actual shape
- [x] Re-ran full by-class audit after each round — clean, no new gaps
- [x] Retrained, re-verified against the full Milestone 11 battery — all
      previously-fixed cases still fixed; reported URL now 3.0% phishing
      (confidently correct), confirmed live end-to-end
- [x] `twitter.com/anthropicai` moved to right at the boundary (55.5%,
      technically still wrong but no longer confidently wrong) — RF
      actually handles this one better (3.6%) but has worse phishing-recall
      margins elsewhere; XGBoost kept per [[phishguard_model_selection]]
- [x] XGBoost wins the automatic F1 comparison again (0.9180 vs RF's
      0.9161) — no standing override needed

## Milestone 13 — RDAP domain-age signal (done, 2026-08-03)
- [x] `backend/app/threat_intel/domain_age.py` — async RDAP lookup via the
      `whodap` library (RDAP chosen over raw WHOIS parsing: structured JSON,
      no per-registrar format inconsistency — see PROJECT_PROGRESS.md for
      the comparison). Returns `domain_age_days` + a bucketed
      `domain_age_status` ("new" <30d, "moderate", "established" >=365d,
      "unknown" on any failure/unsupported TLD)
- [x] `backend/app/verdict.py` extended: an **established** domain overrides
      a *borderline* ML phishing call (probability < 0.9) to legitimate —
      directly targets the documented residual false positives
      (`github.com/anthropics`, `twitter.com/anthropicai`). A **new** domain
      does *not* auto-flip a legit call to phishing (asymmetric by design,
      same pattern as URLhaus's "not_listed" — avoids a new false-positive
      class on genuinely new legitimate sites), just annotated in the reason
- [x] `ScanResponse`/`ScanRecordOut`/CSV export/`ScanRecord` all gained
      `domain_age_days`, `domain_age_status`; existing `phishguard.db`
      migrated in place (`ALTER TABLE`, 131 pre-existing rows preserved)
- [x] Extension popup + dashboard `HistoryTable` show a domain-age badge
      (dashboard confirmed visually in a real browser against the real
      backend; popup still needs the user's manual visual check per the
      known `chrome-extension://` automation limitation)
- [x] Tests: 4 new (established-domain rescue, established-but-confident-
      phishing not rescued, new-domain annotated-not-flipped,
      unknown-domain-age noted in reason), all via monkeypatch — no real
      RDAP network calls in the suite. 24/24 passing.
- [x] **Two snags hit and fixed during live testing** (not caught by
      mocked tests, only by hitting the real backend with real domains):
      1. Some RDAP registries return a naive `datetime` (no tzinfo) for
         `created_date` — crashed the age subtraction. Fixed by assuming
         UTC when tzinfo is missing.
      2. `whodap.aio_lookup_domain()` re-fetches the IANA RDAP bootstrap
         registry (a second network round trip) on *every* call — this
         alone pushed single lookups past a 4s timeout on real domains
         (`github.com`, `twitter.com` both timed out in testing). Fixed by
         caching one `whodap.DNSClient` at module level (bootstrap fetched
         once, lazily) — same fix shape as URLhaus's timeout bump, but the
         actual problem here was redundant work, not just a short timeout.
- [x] Verified live end-to-end against the real backend: `github.com/
      anthropics` (ML 80.2% phishing, domain 6872 days old → rescued to
      legitimate), `twitter.com/anthropicai` (ML 55.5% phishing, domain
      9690 days old → rescued to legitimate — the last open residual case,
      now resolved), fake PayPal phishing URL (still 99.7% phishing,
      domain age unavailable as expected, recall unaffected), real Google
      search URL (domain 10548 days old, still correctly legitimate)

## Next up
- [ ] Final README pass, screenshots/demo for resume (still last)
- [ ] LICENSE file has a placeholder `<Your Name>` — replace with your actual name.
- [ ] Ask user to visually confirm the extension popup's new domain-age
      badge through the actual loaded Chrome extension (known automation
      limitation on `chrome-extension://` pages)

## Known issues / open items
- **Resolved by Milestone 13's RDAP domain-age signal**: the residual
  bare-domain-plus-generic-path false positives (`github.com/anthropics`
  ~80%, `twitter.com/anthropicai` ~55%) are now correctly rescued to
  legitimate, since both are old, established domains. `linkedin.com/in/...`
  not yet re-tested but expected to resolve the same way (also a
  long-established domain). A domain this new-vs-old distinction only kicks
  in for *borderline* ML calls (<90% phishing) — a genuinely compromised or
  purpose-aged old domain hosting real phishing would still need a
  confident-enough ML/URLhaus signal to be caught, which is an accepted,
  honest trade-off, not a gap introduced by this fix.
- RDAP coverage isn't universal — solid for gTLDs (`.com`/`.org`/`.net`),
  patchier for some ccTLDs. Falls back to `"unknown"` gracefully in that
  case, same as URLhaus.
- Dashboard dev server's Vite was pinned to `^5.4.20` (not the newer
  rolldown-powered Vite 8 that `npm create vite@latest` installs by
  default) — that version requires Node `^20.19` or `>=22.12` and its
  native rolldown binding failed to load on this machine's Node v20.12.2.
  Revisit the pin if the dev machine's Node version is upgraded.
