# PhishGuard — Project Progress

Last updated: 2026-07-28

## Completed milestones

- **Milestone 0 — Architecture & design.** Full system architecture agreed:
  Chrome Extension + React Dashboard → FastAPI backend → ML inference →
  Database. Offline ML training pipeline (`ml/`) kept fully decoupled from
  the live serving path (`backend/`). (Originally included a threat-intel
  aggregator; dropped 2026-07-28, see decision 8 below.)
- **Milestone 1 — Repo scaffolding.** Git repo initialized, full folder
  structure created, dependency files split by concern, tooling (Makefile,
  ruff/black config) added, virtual environment created and all dependencies
  installed and import-verified.
- **Milestone 2 — Dataset collection & cleaning.** `ml/prepare_dataset.py`
  loads `ml/data/raw/tranco_XN23N.csv` (Tranco top 1M) and
  `ml/data/raw/verified_online.csv` (PhishTank verified export), randomly
  samples 65k legitimate domains + 65k verified/online phishing URLs (seed
  42 for reproducibility), dedupes, shuffles, and writes a merged
  `url,label` CSV to `ml/data/processed/dataset.csv` (130,000 rows total,
  balanced 65k/65k, zero missing values, zero duplicate URLs after merge).
  EDA showed phishing URLs are on average ~3x longer than legitimate ones
  (mean 57.9 vs 20.8 chars) and have far higher variance (a couple of
  extreme outliers over 25,000 chars — real phishing kits embedding a
  base64-encoded fake page in the URL fragment, not bad data) — URL length
  is likely to be a strong feature for Milestone 3. Also noted: Tranco's
  top-1M includes some low-quality/parked-looking domains (e.g. numeric
  `.xyz` domains), a known limitation of using domain popularity as a proxy
  for "legitimate" — not fixed, just worth mentioning if asked in an
  interview.
- **Milestone 3 — Feature engineering.** `ml/features.py` implements 17
  lexical/domain/statistical features computed directly from the URL string
  (no network calls): length-based (`url_length`, `hostname_length`,
  `path_length`), character-count based (dots, hyphens, digits, special
  chars), structural (`num_subdomains` via `tldextract`, `num_query_params`),
  and rule-based red flags (`has_ip_address`, `has_at_symbol`, `is_https`,
  `has_suspicious_word` against a small keyword list, `is_url_shortener`
  against a small known-shortener list). `FEATURE_NAMES` is a fixed ordered
  list so training and serving always build the feature vector identically.
  9 unit tests in `ml/tests/test_features.py` cover each rule-based feature
  (IP detection, `@` redirect trick, shortener detection, subdomain
  counting, query param counting). All pass.
  **Bug caught during this milestone:** sanity-checking feature means by
  class showed `is_https` at 0% for legit URLs vs 93% for phishing — not a
  real signal, an artifact of Milestone 2's dataset build (Tranco domains
  were prefixed `http://` since Tranco gives bare domains with no scheme).
  Fixed by prefixing legit domains with `https://` instead (realistic —
  virtually all top-ranked sites serve HTTPS today), which also required
  regenerating `ml/data/processed/dataset.csv`. Worth remembering: **always
  sanity-check feature distributions by class before training** — a feature
  that looks "too good" is often a data collection artifact, not a real
  signal, and would have inflated Milestone 4's accuracy numbers on paper
  while producing a model that fails in the real world.

- **Milestone 4 — Model training & evaluation.** `ml/train.py` trains
  Logistic Regression (with `StandardScaler`, since it's the only one of
  the three sensitive to feature scale), Random Forest, and XGBoost on an
  80/20 stratified split (seed=42), evaluates accuracy/precision/recall/F1
  on the held-out set, picks the highest-F1 model, exports it to
  `ml/models/model.joblib` (gitignored, regenerate via `python -m
  ml.train`), and writes `ml/MODEL_REPORT.md` with the comparison table,
  confusion matrix, and top feature importances.

  **Two dataset artifacts caught and fixed before trusting the numbers**
  (both the same root cause: Tranco only gives bare apex domains, so the
  legit class had zero structural diversity):
  1. First training run: 99.6-99.7% accuracy/F1 across *all three* models —
     suspiciously high and suspiciously uniform. Investigated: 100% of
     legit URLs had `path_length == 0` (bare domain, no path) vs 94% of
     phishing URLs having a path, so "has a path -> phishing" alone
     explained most of the accuracy. Fixed in `ml/prepare_dataset.py` by
     appending a randomly chosen realistic path/query string
     (`PATH_TEMPLATES`, 20 options including a blank one) to each legit
     URL.
  2. Retrained: XGBoost's top feature was then `num_subdomains` at 88% of
     total importance. Investigated: 100% of legit URLs had zero
     subdomains (Tranco never includes `www.`) vs 71% of phishing URLs
     having one, so the model was really learning "any subdomain ->
     phishing" — which would misfire on everyday real URLs like
     `www.google.com` or `mail.google.com` once this ships in the Chrome
     extension. Fixed the same way: `SUBDOMAIN_TEMPLATES` in
     `ml/prepare_dataset.py` randomly prefixes legit domains with `www`
     (weighted most common), `mail`, `blog`, `docs`, etc., or nothing.

  **Final, trustworthy results** (after both fixes, `ml/data/processed/dataset.csv`
  regenerated): Logistic Regression 79.6% acc / 0.785 F1, Random Forest
  96.15% acc / 0.9616 F1, **XGBoost 96.51% acc / 0.9653 F1 (winner)**. The
  meaningful gap between the linear model and the tree ensembles (not
  present in the first, artifact-driven run) is itself a good result to
  explain: it shows the real phishing signal here is non-linear feature
  interactions, which XGBoost/Random Forest capture and plain Logistic
  Regression can't. Top features for the winner are spread out sensibly
  (no longer one feature dominating): `num_digits` (18%), `is_https`
  (13%), `path_length` (10%), `num_subdomains` (9%), `num_slashes` (9%),
  `is_url_shortener` (7%), `hostname_length` (7%), `num_hyphens` (6%) — all
  established phishing lexical indicators, not artifacts.

  **Lesson worth remembering for the interview**: a model that looks "too
  good" usually is — always check *why* it's doing well (feature
  importances, ablation) before trusting the number, especially when a
  dataset is partly synthetic/constructed rather than fully organic.

- **Milestone 5 — Backend core (`/scan`, ML only).** FastAPI app
  (`backend/app/main.py`) with a `POST /scan` route
  (`backend/app/api/scan.py`) backed by Pydantic request/response schemas
  (`backend/app/schemas/scan.py`) and an ML service module
  (`backend/app/ml_service/predictor.py`) that loads
  `ml/models/model.joblib` once at import time and reuses
  `ml.features.extract_features` for inference — the exact same feature
  logic used at training time, imported directly from `ml/`, not
  duplicated. A `/health` endpoint was added too (cheap, standard, useful
  for later deployment checks). 4 tests in `backend/tests/test_scan.py`
  using FastAPI's `TestClient` (health check, a real verdict comes back
  with a valid confidence, an IP-address+login URL is flagged phishing,
  empty URL is rejected with 422).

  **Import/run convention decided here:** both `backend/` and `ml/` are
  now proper Python packages (`__init__.py` added throughout, including
  `backend/`, `backend/app/`, and each subpackage). Everything is run as a
  module from the **repo root** — `python -m uvicorn backend.app.main:app`
  and `python -m ml.train` — so `from ml.features import ...` and `from
  backend.app... import ...` always resolve the same way in tests, in the
  dev server, and (later) in whatever runs it in production. Running
  `python backend/app/main.py` directly or `cd`-ing into `backend/` first
  would break these imports — worth remembering if something suddenly
  can't find the `ml` or `backend` module.

  **Manually smoke-tested against the real running server** (not just
  `TestClient`): a real Google search URL
  (`https://www.google.com/search?q=hello`) correctly comes back
  `is_phishing: false` (99.95% confidence), and a fake PayPal-lookalike URL
  (`http://paypal.com.security-verify-login.tk/account/confirm?id=12345`)
  correctly comes back `is_phishing: true` (99.96% confidence).

- **Milestone 6 — Persistence layer.** `backend/app/db/database.py` sets
  up a SQLite engine/session (`backend/phishguard.db`, gitignored) with a
  `get_db()` FastAPI dependency; `backend/app/db/models.py` defines
  `ScanRecord` (id, url, is_phishing, confidence, scanned_at). `POST /scan`
  now saves a record on every call. Added `GET /history?limit=` (most
  recent first, capped 1-500) and `GET /reports` (streams a CSV export
  using the stdlib `csv`/`io` modules — no pandas needed on the backend).
  Tables are created on startup via `Base.metadata.create_all()` in
  `main.py` — no migrations tool (Alembic etc.) since a single-table SQLite
  schema doesn't need one at this scale.

  **Testing decision:** rather than hitting the real `phishguard.db` file
  in tests, `backend/tests/conftest.py` overrides FastAPI's `get_db`
  dependency with an in-memory SQLite DB (`StaticPool` so every session in
  a test shares the same in-memory connection — otherwise each new session
  would see an empty database). Tables are created fresh and dropped after
  every test function, so tests are isolated from each other and from the
  real database. This is the standard FastAPI pattern for testing DB-backed
  routes, not a project-specific invention — worth knowing that phrase if
  asked about it.

  Manually smoke-tested against the real running server end-to-end: two
  `/scan` calls, then `/history` returned both (most recent first), then
  `/reports` returned a correctly-formatted CSV with both rows.

- **Milestone 7 — Chrome Extension MVP.** `extension/manifest.json` (MV3):
  `permissions: ["storage", "tabs"]` and `host_permissions` scoped just to
  `localhost:8000`/`127.0.0.1:8000` — no content script, no access to page
  contents, no broad `<all_urls>`. `background.js` is a service worker that
  calls `POST /scan` on every completed navigation to an `http(s)` URL and
  caches the verdict in `chrome.storage.local` keyed by tab ID.
  `popup/popup.js` shows the cached verdict instantly if available, or
  scans on demand (same code path, so it works even if the background
  scan hasn't finished or missed a page) and shows a clear error if the
  backend isn't reachable rather than failing silently.

  **CORS added to the backend as a prerequisite** (`app.add_middleware
  (CORSMiddleware, allow_origins=["*"], ...)` in `backend/app/main.py`):
  the extension's popup/background worker run as browser contexts calling
  a different origin, so without either CORS or `host_permissions` the
  fetch would be blocked. Permissive `allow_origins=["*"]` is fine here —
  local resume project, not a hardened public API — and this same change
  is needed again for Milestone 8's React dashboard, which is a normal web
  page (not a privileged extension context) and *only* has CORS as an
  option, not `host_permissions`.

  **Browser automation testing limitation hit and worked around**: Chrome
  extension pages (`chrome://extensions`, `chrome-extension://...`) can't
  be driven by the available browser automation tooling (blocked as
  browser-internal). Verified correctness a different way instead: had the
  user load the unpacked extension manually, then confirmed via the
  backend's own request log and `GET /history` that real navigation events
  triggered correct `POST /scan` calls end-to-end, and had the user
  visually confirm the popup's two states — navigating to `example.com`/
  `example.org` produced "✓ Looks safe" (~51% confidence — appropriately
  unconfident on generic domains unlike anything in the training data),
  and navigating to `example.com/login/verify-account?id=12345&session=abc`
  (a URL lexically shaped like a phishing link) produced "⚠ Likely
  phishing" at 98.5% confidence, both matching what the backend returned.

## Current project status

Repo is scaffolded, local dev environment is fully working, a clean labeled
dataset (130k URLs, balanced, with realistic path/subdomain diversity on
the legit side) exists at `ml/data/processed/dataset.csv`, a trained
XGBoost model (96.5% held-out accuracy) is exported to
`ml/models/model.joblib` with results documented in `ml/MODEL_REPORT.md`,
the FastAPI backend serves real verdicts end-to-end via `POST /scan`,
persists them to SQLite, and exposes them via `GET /history` and `GET
/reports` (CSV), and the Chrome extension (Manifest V3) scans on
navigation and shows a verdict popup — verified working against the real
backend in an actual loaded Chrome extension, not just unit tests.
Application code so far: `ml/prepare_dataset.py`, `ml/features.py`,
`ml/train.py`, `ml/tests/test_features.py`; the full `backend/app/`
package (`main.py`, `api/{scan,history,reports}.py`,
`schemas/{scan,history}.py`, `ml_service/predictor.py`,
`db/{database,models}.py`) with `backend/tests/` (`conftest.py`,
`test_scan.py`, `test_history.py`, 18 tests total); and
`extension/` (`manifest.json`, `background.js`, `popup/`). Nothing has
been committed to git yet (working tree has untracked files only, by
design — commits are left to you).

## Next milestone

**Milestone 8 — React Dashboard**: scan history table, one simple stats
chart, and a report export button — talking to the same backend
(`/history`, `/reports`) the extension uses, now that CORS is already
enabled.

## Important design decisions made today

1. **Training/serving separation.** `ml/` trains offline and exports a model
   artifact; `backend/` only loads and runs that artifact — never trains live.
2. **Shared feature-extraction module (planned for Milestone 3).**
   `ml/features.py` will be imported by both the training pipeline and
   `backend/app/ml_service`, so train-time and serve-time features can never
   drift apart (the most common real-world ML bug).
3. **Model strategy: compare, don't assume.** Logistic Regression, Random
   Forest, and XGBoost will all be trained; XGBoost is favored for the
   <500ms inference budget, but the final pick will be justified by
   held-out evaluation, not just following the spec.
4. **Split dependency files.** `ml/requirements.txt` and
   `backend/requirements.txt` are separate so the deployed API container
   never needs to install training-only libraries. `requirements-dev.txt`
   holds shared tooling (pytest, black, ruff). One shared `.venv` is used
   locally for convenience.
5. **SQLite now, Postgres-ready later.** Using SQLAlchemy as the ORM so the
   only future change needed to move to Postgres is the connection string.
6. **Manifest V3 for the Chrome extension**, using a background service
   worker (current Chrome standard, not the deprecated persistent background
   page model).
7. **Monolithic FastAPI backend**, not microservices — right complexity
   level for this project's scale; internal module boundaries
   (`api/`, `ml_service/`, `db/`, `schemas/`) keep it organized without the
   operational overhead of splitting services.
8. **Pure ML classifier — no external threat-intel APIs (VirusTotal/URLHaus
   dropped), decided 2026-07-28.** This is a resume/final-year project, not
   a production security product, so the priority is a system the author can
   fully build and explain end to end rather than maximum feature coverage.
   Dropping threat intel removes API keys, rate limits, async retry logic,
   and a caching layer — all real engineering, but not essential to the core
   "ML classifies a URL" story. `backend/app/threat_intel/` scaffold folder
   removed accordingly. Can be re-added later as a stretch goal if time
   allows, since the architecture (verdict returned by `/scan`) doesn't
   preclude it.

## Reference

See conversation history for the full architecture diagram and per-milestone
rationale. See `TODO.md` for the concrete remaining task list.
