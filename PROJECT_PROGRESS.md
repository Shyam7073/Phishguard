# PhishGuard — Project Progress

Last updated: 2026-08-03

## Milestone 13 — RDAP domain-age signal (done, 2026-08-03)

The last open item from Milestone 8's false-positive investigation was a
small, honestly-documented ceiling: a handful of legitimate URLs
(`github.com/anthropics` ~80% phishing, `twitter.com/anthropicai` ~55%)
stayed borderline/wrong no matter how the synthetic dataset was tuned,
because a 17-feature lexical-only model has no way to know a domain is
old and reputable versus a lookalike registered last week. This milestone
adds that missing signal.

**Why RDAP, not raw WHOIS**: researched both before building. Raw WHOIS is
a plain-text protocol with no fixed schema -- every registrar/TLD formats
its response differently, so reliably parsing a creation date out of free
text needs per-registrar handling. RDAP (the ICANN-mandated JSON successor
to WHOIS) returns the same structured fields regardless of registry, which
directly removes that parsing burden. Trade-off checked and accepted:
RDAP coverage is strong for gTLDs (~85%+, and mandatory for `.com`/`.org`/
`.net`) but patchier for ccTLDs (~40-60%, some like `.de`/`.cn`/`.jp` still
WHOIS-only) -- acceptable since phishing overwhelmingly targets brands on
gTLDs, and the existing "unknown" fallback pattern already handles the
rest gracefully.

**Design**: `backend/app/threat_intel/domain_age.py` looks up a domain's
RDAP creation date via the `whodap` library and buckets the result into
`domain_age_status`: "new" (<30 days), "moderate", "established" (>=365
days), or "unknown" (lookup failed/unsupported TLD). `backend/app/
verdict.py` folds this into the combined verdict with a deliberately
**asymmetric** rule, following the same asymmetry principle URLhaus already
established (a positive hit overrides, an absence of evidence doesn't
invert):
- An **established** domain overrides a *borderline* ML phishing call
  (probability < 0.9, `ESTABLISHED_OVERRIDE_CEILING`) to legitimate --
  this is the fix. A genuinely confident ML phishing score (>=90%) is
  *not* overridden just because the domain is old, so a compromised or
  deliberately aged old domain hosting real phishing is still caught.
- A **new** domain does *not* auto-flip a confidently-legit ML call to
  phishing -- deliberately asymmetric, to avoid introducing a fresh class
  of false positives on genuinely new legitimate sites (personal pages,
  startups), which are common and untested here. It's only noted in the
  reason text for a human to weigh, not acted on automatically.

**Two real snags hit and fixed during live testing** (mocked tests didn't
catch either, since they don't touch the real RDAP network path):
1. Some registries return a naive `datetime` (no tzinfo) for `created_date`
   -- crashed `(datetime.now(timezone.utc) - creation_date)` with a
   `TypeError` on `twitter.com`'s real RDAP response, even though
   `google.com`'s worked fine. Fixed by assuming UTC when tzinfo is absent.
2. `whodap.aio_lookup_domain()` re-fetches IANA's RDAP bootstrap registry
   (a second network round trip, to find which RDAP server owns a given
   TLD) on *every single call* -- this alone pushed real lookups for both
   `github.com` and `twitter.com` past a 4-second timeout in back-to-back
   live testing. Fixed by caching one `whodap.DNSClient` at module level
   (bootstrap fetched once, lazily, on first use) so every call after the
   first is a single RDAP round trip -- same *shape* of fix as URLhaus's
   cold-connection timeout bump in Milestone 10a (a live smoke test catching
   something mocked tests structurally can't), but the actual fix here was
   eliminating redundant work rather than just raising a number.

**Result, verified live end-to-end against the real backend** (not just
mocked tests): `github.com/anthropics` -- ML score 80.2% phishing, RDAP age
6872 days (~18.8 years) -- **rescued to legitimate**, reason: "ML model
flagged this, but the domain is long-established — likely a false
positive". `twitter.com/anthropicai` -- ML 55.5% phishing, RDAP age 9690
days (~26.5 years) -- **also rescued**, resolving the last open residual
case from Milestone 8/11/12. Fake PayPal phishing URL -- still 99.7%
phishing, RDAP unavailable for that domain as expected, confirms recall is
untouched. Real Google search URL -- RDAP age 10548 days, correctly stayed
legitimate. Dashboard's `HistoryTable` gained a "Domain age" column
(colored dot + `Nd (status)` label, same status-color convention as the
other badges), confirmed rendering correctly in a real browser against the
real backend. Extension popup gained the same badge in code but still
needs the user's manual visual confirmation (known `chrome-extension://`
browser-automation limitation, same as every previous extension change).

**Testing**: 4 new tests added via monkeypatching `scan_module.predict`
and `scan_module.check_domain_age` (established-domain rescues a borderline
call, established-but-confident-phishing is *not* rescued, new-domain is
annotated but not auto-flagged, unknown-domain-age is noted in the reason)
-- no real RDAP network calls in the suite, same pattern as URLhaus's
mocked "listed"/"unknown" tests. 24/24 tests passing. `backend/phishguard.db`
migrated in place via `ALTER TABLE` (all 131 pre-existing rows preserved,
same approach as Milestone 10b).

## Milestone 12 — real-world false positive fix: long tracking-param URLs (done, 2026-08-01)

User reported a second real false positive right after Milestone 11: a real
Google search URL typed into Chrome's address bar
(`https://www.google.com/search?q=codeshef&rlz=...&gs_lcrp=...&sourceid=chrome&...`,
317 chars) scored **99.9996% phishing**. Diagnosed via contribution
analysis: `url_length` alone contributed +5.83, the dominant driver by far.
Root cause, confirmed by checking the actual training distribution: legit
synthetic URLs **never exceeded 213 characters** (zero rows past 250) while
phishing had real coverage there (1.03%) -- any legit URL that happened to
be long, which every single browser-address-bar search is, was guaranteed
to be misclassified with high confidence, because the model had literally
never seen a legit example that long. Same root cause class as Milestone 11
(synthetic data not matching real browsing), but broader-impact: long
tracking/analytics query strings are extremely common in everyday
legitimate browsing (any search engine, e-commerce filters, OAuth
redirects), not a rare edge case.

**Fix**: added `_tracking_blob()` to `ml/prepare_dataset.py` -- one to three
long, randomly-sized query params (mimicking Google's real `rlz`/`oq`/
`gs_lcrp`, OAuth `state`/`token`, session/signature blobs), attached to
~10% of all legit URLs. First attempt (single param, 7% of legit URLs) only
partially worked -- dropped the reported URL from 99.9996% to ~95%, still
wrong. Diagnosed why via a second contribution-analysis pass:
`num_special_chars` (each extra `=`/`&` per param) had become the new
dominant driver, and legit coverage at high `num_special_chars` was still
thin (0.24% vs phishing's 3.19%). Fixed by making the blob generator
stack multiple params at once (matching how a real Google search URL
actually looks -- five-plus tracking params together, not one), which
pushed legit coverage to 0.76% and closed enough of the gap.

**Result**: XGBoost score on the reported URL -> **3.0% phishing (confidently
correct)**, confirmed live end-to-end through the real backend. Full
by-class coverage audit re-run and clean (no new 0%-only-in-one-class
gaps). Re-verified against the entire Milestone 11 battery: all previously
fixed cases stayed fixed, `github.com/anthropics` unchanged (known
residual, ~80%), `twitter.com/anthropicai` moved to right at the boundary
(XGBoost 55.5%, technically still wrong but no longer a confident
misfire -- RF actually gets this one right at 3.6%, a genuine trade-off
noted, not chased further). XGBoost retained as the shipped model --
still wins the automatic F1 comparison (0.9180 vs RF's 0.9161) and has
much stronger, more reliable phishing-recall margins (99.7-100% vs RF's
81-82% on the same real phishing test cases) despite occasionally being
less generous on the hardest borderline legit cases.

**Process note**: per [[phishguard_model_selection]], re-ran the RF-vs-XGBoost
edge-case comparison at every retrain in this milestone since the F1 gap
stayed under 0.002 each time -- confirmed XGBoost remained the right
practical choice throughout, not just the F1-optimal one on paper.

## Milestone 11 — real-world false positive fix: bare-root/trailing-slash bug (done, 2026-08-01)

User reported a real false positive from actual browsing: `https://launchpad.ccbp.in/`
(a genuine course platform) scored 72.3% phishing. Diagnosed via the same
per-feature contribution analysis used in the Milestone 8 follow-up (not
guessed at): `path_length` going from 0 (bare domain) to 1 (just a trailing
slash) contributed +2.47 on its own -- by far the largest driver. Root
cause: `_random_path` in `ml/prepare_dataset.py` treated `""` (no path) and
`"/"` (trailing slash) as a 50/50 coin flip for synthetic legit URLs, giving
legit only ~4% coverage at `path_length==1` vs PhishTank's real 29.9% for
phishing -- but real browsers virtually always normalize a homepage visit to
include the trailing slash, so `path_length==1` should be the dominant case
for real legit traffic, not a rare one. Same class of bug as the
`num_slashes`/`num_subdomains` fixes in Milestone 8 (dataset construction
methodology not matching real browsing behavior), just not caught until a
real user hit it.

**Fixed in two rounds**, each re-verified with the project's established
audit method (check every feature value present in one class at >=0.5% but
0% in the other) before trusting the result:
1. Weighted the `""`/`"/"` split 90/10 toward `"/"` -- moved the reported
   URL from 72.3% to 58.8% phishing. Real improvement, not yet enough to
   flip the verdict.
2. Went further: raised `_DEPTH0_WEIGHT` (how often a legit URL gets *any*
   bare-root shape) from 8% to 20%, since PhishTank's real bare-root rate is
   35.6% and a homepage-only visit is at least as common in real legitimate
   browsing (opening a known site directly, not a deep link). Also pushed
   the `""`/`"/"` split to 95/5. This surfaced and fixed a second real gap
   the same audit caught along the way: `path_length==2` was 0% for legit
   (the shortest random path-segment token was 3 chars; real phishing URLs
   have 1-2 char segments too) -- fixed by lowering the token's minimum
   length from 3 to 1 in `_random_segment`.

**Result**: `launchpad.ccbp.in/` -> **37% phishing (correctly legit)**,
confirmed live end-to-end through the real running backend and dashboard.
Cross-validated against other real bare-root sites surfaced in the
dashboard's own scan history that had the same unreported bug (`web.whatsapp.com/`
71.6%->34%, `leetcode.com/` 50.1%->25%, `chatgpt.com/` 63.2%->17%,
`www.youtube.com/` similarly) -- confirms this was a broad, systemic fix,
not something narrowly overfit to the one reported URL.

**Trade-off, reported honestly, not hidden**: `twitter.com/anthropicai`
(fixed in the Milestone 8 follow-up) regressed from borderline-correct
(50.1% legit) to borderline-wrong (64.7% phishing). Investigated via
contribution analysis: not a new artifact -- `num_subdomains==0` (no
subdomain) is a real, modest, pre-existing skew (21.7% legit vs 28.6%
phishing, both well-represented, not a coverage gap) that became more
decisive once `path_length`'s outsized influence was corrected. This is the
same class of "genuine ceiling of a 17-feature lexical-only classifier" as
the already-accepted `github.com/anthropics` case (unchanged at 78.1%, one
of the few cases XGBoost still gets wrong) -- not chased further, per the
project's standing rule against hand-tuning synthetic data to defeat
specific adversarial examples.

**Model re-comparison**: retraining after each fix produced an extremely
close RF-vs-XGBoost F1 race. After round 1, the automatic "highest F1"
picker chose Random Forest (0.9336 vs XGBoost's 0.9323) -- manually
overrode this after a head-to-head test on real cases showed XGBoost's
probabilities are far better calibrated (phishing recall 99.95-100% vs RF's
79-86%; much better on `github.com/anthropics`, 78% vs RF's 100%). After
round 2, XGBoost won the automatic F1 comparison outright (0.9205 vs RF's
0.9189), so `ml.train`'s normal picker now agrees with the manual override
-- no standing override needed going forward. Final metrics: XGBoost acc
92.16% / prec 0.9338 / rec 0.9076 / f1 0.9205 (down from the earlier
94.08%, expected and correct: that number was inflated by exactly the
`path_length` artifact just fixed).

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

- **Milestone 8 — React Dashboard.** `dashboard/` is a Vite + React 19 app
  styled with Tailwind CSS v4 (`@tailwindcss/vite` plugin, no config file
  needed — v4 is CSS-first). Three components, all reading from the same
  backend the extension already talks to:
  - `HistoryTable` — `GET /history?limit=100`, most-recent-first, with a
    verdict badge (colored dot + label, never color alone), confidence
    percentage, and a formatted timestamp. Shows an empty state ("No scans
    yet...") rather than a blank table when history is empty.
  - `VerdictBarChart` — a small horizontal bar chart comparing legitimate
    vs phishing counts. Built by hand in plain HTML/CSS (no charting
    library — two bars didn't justify one), following the project's
    dataviz skill: status colors (`good` #0ca30c / `critical` #d03b3b,
    the fixed, never-themed status palette) rather than arbitrary
    categorical hues, since "legitimate vs phishing" is a status
    distinction, not series identity; 4px rounded data-end/square baseline
    bar spec; identity carried by icon-dot + direct label, never color
    alone.
  - `StatTiles` — four stat tiles (total scans, legitimate, phishing,
    phishing rate) above the chart.
  - `ExportButton` — plain `<a href=".../reports" download>`, no JS needed
    since the backend already sets `Content-Disposition: attachment`.

  App-level state is a single `fetchHistory()` call on mount plus a manual
  Refresh button — no polling, no global state library; this is a
  single-page read-only dashboard, not an app with writes to synchronize.

  **Dependency snag hit and fixed:** `npm create vite@latest` now scaffolds
  with Vite 8, which ships a Rust/rolldown bundler core requiring Node
  `^20.19`/`>=22.12`; on this machine's Node v20.12.2 the native
  `@rolldown/binding-darwin-arm64` binding failed to load and `vite build`
  crashed outright. Fixed by pinning back to `vite@^5.4.20` +
  `@vitejs/plugin-react@^4` (the classic esbuild/rollup Vite, well past
  stable) — worth revisiting if the dev machine's Node is ever upgraded
  past 20.19.

  **Manually smoke-tested against the real running backend** (not just a
  build check): started both `python -m uvicorn backend.app.main:app` and
  `npm run dev`, seeded a handful of real `/scan` calls (a legitimate
  Google search URL, a fake PayPal-lookalike, an IP-address login URL,
  `mail.google.com`, `github.com/anthropics`), loaded the dashboard in
  Chrome, and confirmed the stat tiles, bar chart, and table all rendered
  and updated correctly on Refresh. Also clicked Export CSV for real and
  confirmed the downloaded file matched what `/reports` returns.
  **Bonus confirmation, not a dashboard bug:** the Chrome extension from
  Milestone 7 is still loaded in this browser, and its background worker
  scanned the dashboard's own `http://localhost:5173/` tab on navigation —
  visible as an extra row in the history table. That's expected behavior
  (the extension scans every `http(s)` navigation, dashboard included),
  not something to fix, but worth remembering when taking demo
  screenshots (either unload the extension first, or expect a
  `localhost:5173` row to show up).

- **Milestone 8 follow-up — model false-positive investigation & fix.**
  The `mail.google.com`/`github.com/anthropics` false positives surfaced
  above turned out to be three separate instances of the same root cause
  (synthetic legit-URL generation not covering the real range of a
  feature), confirmed with per-feature evidence each time rather than
  guessed at:

  1. **`num_slashes` >= 6 was 0% of legit training rows** (the old 20
     literal `PATH_TEMPLATES` topped out at 3 path segments) vs ~12% of
     real phishing rows -- XGBoost learned "deep path -> certainly
     phishing" and misfired on `mail.google.com/mail/u/0/` and
     `docs.google.com/document/d/.../edit`.
  2. A first fix attempt (add more literal deep-path template strings)
     only partially worked -- `https://twitter.com/anthropicai` still
     misfired, and XGBoost's per-feature contribution (via
     `booster.predict(..., pred_contribs=True)`) showed `path_length`
     alone contributing +8 toward phishing. A **fixed list of literal
     strings, no matter how many, only ever produces a handful of exact
     `path_length` values** -- real usernames/slugs/IDs vary in length
     every time. Replaced the literal template list with a small
     compositional generator (`_random_path`/`_random_segment` in
     `ml/prepare_dataset.py`): random path depth (weighted shallow but
     with a real tail into deep routes) built from either a common route
     word, a hyphen/underscore-joined multi-word slug, or a variable-length
     random alphanumeric token -- giving `path_length` and `num_slashes` a
     smooth, continuous distribution instead of discrete gaps.
  3. That generator itself introduced a *new*, opposite-direction
     artifact: query strings were attached 60% of the time, but real
     PhishTank phishing URLs have **no** query string ~84% of the time --
     so `num_query_params == 0` ended up more associated with phishing
     than legit, inverting the intended signal. Fixed by making "no query
     string" the ~80% common case for legit too (matching PhishTank's
     real rate) rather than picking an arbitrary ratio.

  After each fix, ran a **systematic audit** (not just re-testing the same
  hand-picked URLs): for every feature, find any value that appears in
  >=0.5% of phishing training rows but 0% of legit training rows -- the
  exact shape of the bug each time. That caught two more real gaps
  (`num_underscores` and 2-level subdomains/`num_dots` >= 5) and confirmed
  the rest of the remaining gaps are either sampling noise on
  high-cardinality features or deliberate, defensible signals (`@`
  symbol, `is_https`, known URL shorteners are genuinely near-absent in
  legitimate URLs and shouldn't be forced into the synthetic data).

  **Result:** XGBoost accuracy moved from 96.51% to **94.08%** (precision
  0.9510 / recall 0.9295 / F1 0.9401) -- a *drop*, and that's expected and
  correct: the earlier, higher number was inflated by the same class of
  synthetic-data shortcut caught twice already in Milestone 4. Feature
  importances now read as genuine phishing indicators (`is_https` 20.7%,
  `num_digits` 18.2%, `is_url_shortener` 10.4%, `has_at_symbol` 7.6%)
  rather than an artifact dominating (previously `num_slashes` alone was
  23%). All 18 existing unit tests still pass unmodified (they test
  `ml/features.py`, which wasn't touched). Re-tested against 15 hand-picked
  real legitimate URLs and 7 real-shaped phishing URLs: phishing recall
  held at 7/7, and legit false positives dropped from confidently-wrong
  (99%+) to either fixed outright or borderline-uncertain (55-65%) for a
  residual few bare-domain-plus-generic-path cases (`github.com/anthropics`,
  `linkedin.com/in/...`) -- a genuine, honestly-reported limitation of a
  17-feature lexical-only classifier (no domain age/reputation/whois
  signal), not a data artifact, and not worth chasing further by hand-
  tuning synthetic data to specific adversarial examples.

## Current project status (as of 2026-08-03)

The FastAPI backend now combines **three signals** into one explainable
verdict via `POST /scan`: the ML phishing probability, a live URLhaus
blocklist check, and a live RDAP domain-age check (`backend/app/
verdict.py`) -- `is_phishing`/`confidence`/`ml_score`/`urlhaus_status`/
`domain_age_days`/`domain_age_status`/`verdict_reason`. The domain-age
signal (Milestone 13, above) resolved the last open residual false-positive
case (`twitter.com/anthropicai`) and the previously-known one
(`github.com/anthropics`). Persistence, `/history`, `/reports`, the
extension popup, and the dashboard's history table all carry the full
7-field breakdown now. 24 backend/ml tests passing.

## Previous project status snapshot (as of end of day 2026-08-01)

Repo is scaffolded, local dev environment is fully working. Dataset
(`ml/data/processed/dataset.csv`, 130k URLs, balanced) has been regenerated
several times since Milestone 4 to close real coverage gaps found via a
by-class audit (path/subdomain diversity in Milestone 8; bare-root/trailing-
slash and long-tracking-param-URL coverage in Milestones 11-12). The
currently shipped model is **XGBoost, acc 91.94% / F1 0.9180**
(`ml/models/model.joblib`, results in `ml/MODEL_REPORT.md`) — lower than
earlier headline numbers on paper, and that's expected: each drop
corresponds to a real synthetic-data artifact being removed, not the model
getting worse at anything real.

The FastAPI backend serves a **combined, explainable verdict** (not just a
raw ML number) via `POST /scan`: ML phishing-probability +
URLhaus blocklist check, combined in `backend/app/verdict.py` into
`is_phishing`/`confidence`/`ml_score`/`urlhaus_status`/`verdict_reason`.
Persists to SQLite (`ScanRecord`, all 5 fields) and exposes `GET /history`
and `GET /reports` (CSV), both with the full explainability breakdown. The
Chrome extension (Manifest V3) popup and the React dashboard's history
table both show the verdict reason and blocklist status now, not just a
confidence percentage — verified in an actual loaded Chrome extension and
a real browser session, not just unit tests. 20 backend/ml tests passing.

Application code: `ml/prepare_dataset.py`, `ml/features.py`, `ml/train.py`,
`ml/tests/test_features.py`; `backend/app/` (`main.py`,
`api/{scan,history,reports}.py`, `schemas/{scan,history}.py`,
`ml_service/predictor.py`, `db/{database,models}.py`,
`threat_intel/urlhaus.py`, `verdict.py`) with `backend/tests/`
(`conftest.py`, `test_scan.py`, `test_history.py`); `extension/`
(`manifest.json`, `background.js`, `popup/`); `dashboard/src/` (`App.jsx`,
`api.js`, `components/{StatTiles,VerdictBarChart,HistoryTable,
ExportButton}.jsx`). `.env` (gitignored) holds `URLHAUS_AUTH_KEY`.

- **Milestone 8 extension re-test (2026-07-31).** After the false-positive
  fix above, re-verified through the *actual loaded Chrome extension*
  (not just direct model calls) — confirmed the extension itself needed
  no changes (it only calls `/scan`; the model lives entirely server-side,
  so only the backend needed a restart to load the retrained
  `model.joblib`). Three real navigations tested: `github.com/anthropics`
  (83.8% phishing through the real extension, matching the direct-model
  test exactly — the known residual case, see below), a real live Reddit
  thread URL (99.9% legit — previously a false positive, confirmed fixed
  on genuine traffic, not just the synthetic test string), and a fake
  PayPal phishing URL (99.98% phishing — confirms recall wasn't
  collateral damage from the retrain).

- **Decision, 2026-07-31: partially reversing the "pure ML classifier, no
  threat-intel" call from decision 8 below.** The `github.com/anthropics`-
  style residual false positives (documented above as "a genuine ceiling
  of a lexical-only classifier") are real and the user wants to address
  them with more than dataset tuning. Options compared:
  - **Typosquat/brand-similarity feature** (edit-distance from a domain to
    a curated list of well-known brands) — offline, no network call, stays
    inside the existing `ml/features.py` pattern. Cheapest, and directly
    targets exactly the blind spot found (a lexical-only model can't tell
    "this domain impersonates a brand" or, conversely, "this domain *is*
    the brand" without an explicit similarity check).
  - **URLhaus vs VirusTotal vs Google Safe Browsing** (live blocklist
    checks) — URLhaus picked as easiest: no account/API key needed for
    basic lookups, single `POST`/immediate JSON, no meaningful rate limit
    for real-time browsing. VirusTotal's free tier (~4 req/min) is too
    tight for a "scans every page" use case. Google Safe Browsing (10k/day
    free, same blocklist Chrome uses) was noted as a strong alternative if
    more polish/name-recognition is wanted later, but needs a Google Cloud
    API key vs URLhaus's zero setup.
  - **WHOIS domain age** (`python-whois`) — the signal most directly
    relevant to the `github.com`-style gap (old, reputable domain vs a
    lexically-similar-looking new one), but it's a live, sometimes-slow,
    inconsistently-formatted network call — deliberately sequenced last,
    added once the multi-signal combine/fallback logic already exists.
  - Rejected for now: fetching page content/DOM (form actions, password
    fields) and favicon/visual-similarity hashing — both meaningfully
    more complex (safe fetching of arbitrary/possibly-malicious pages,
    image hashing + a brand-favicon database) for the correctness gained
    relative to the options above.

  **The plan is not just to bolt these on independently but to combine
  them into one explainable multi-signal verdict** (ML score + typosquat
  flag + blocklist hit, shown with *why*, not one raw confidence number)
  — the bigger value-add, and it directly fixes today's binary-verdict
  problem (a borderline ML score plus "not on any blocklist" plus "no
  brand-name match" reads very differently from a borderline score alone).

- **Milestone 10a — URLhaus threat intel (done, 2026-07-31).** Typosquat
  feature deliberately deferred (user chose to ship URLhaus first). Added
  `backend/app/threat_intel/urlhaus.py` (async blocklist lookup, 4s
  timeout) and `backend/app/verdict.py` (combines ML phishing-probability +
  URLhaus status into one verdict with a human-readable `verdict_reason` —
  a confirmed URLhaus hit overrides the ML score outright, otherwise the
  ML score decides and the reason notes whether URLhaus was checked). `/scan`
  is now `async def`; `ScanResponse` gained `ml_score`, `urlhaus_status`,
  `verdict_reason` alongside the existing `is_phishing`/`confidence`.
  `predictor.predict()` now always returns the raw phishing-class
  probability (`_model.classes_` confirmed `[0, 1]`, so index 1 is always
  P(phishing)) instead of "confidence in whichever class was predicted",
  since the combine logic needs the actual phishing probability regardless
  of which side of 0.5 it fell on.

  **Snag hit and fixed**: URLhaus's API now requires a free `Auth-Key`
  header — abuse.ch added mandatory auth across their APIs at some point
  after the 07-31 comparison (which assumed "no API key needed", confirmed
  via `curl` returning `401 {"error": "Unauthorized"}` with no key). Still
  free — got one from `auth.abuse.ch`, stored as `URLHAUS_AUTH_KEY` in
  `.env` (already gitignored, `python-dotenv` was already a dependency).
  The graceful-fallback design meant this degraded safely even before the
  key was added (401 → caught as an `httpx.HTTPError` → `"unknown"`, never
  a broken endpoint) — confirms the fallback-first design was the right
  call. Also bumped the lookup timeout from an initial 2s to 4s after live
  testing showed the very first request from a cold connection (TLS
  handshake overhead) timed out at 2s but succeeded well within 4s.

  **Testing approach**: existing tests updated so the `client` fixture
  monkeypatches `check_urlhaus` to a fake async function returning
  `"not_listed"` by default (`backend/tests/conftest.py`) — the test suite
  never makes a real network call. Two new tests cover the `"listed"`
  (overrides ML score, confidence forced ≥0.99) and `"unknown"` (falls back
  to ML-only, reason notes unavailability) paths explicitly via
  monkeypatch, rather than depending on URLhaus's live, constantly-changing
  blocklist contents (which would make a "listed" test flaky). 11/11 tests
  passing. Manually smoke-tested against the real running backend with the
  real key: a clean HTTPS Google search URL and a fake PayPal-lookalike
  domain both returned correct `urlhaus_status: "not_listed"` alongside the
  expected ML verdict.

  **Resolved 2026-07-31 (Milestone 10b)**: extension popup and dashboard
  now both surface `verdict_reason`/`urlhaus_status` — see Milestone 10b
  above for details (DB migration, popup badges, dashboard columns).

## Next milestone

**Done as of 2026-08-03**: the RDAP domain-age signal planned here shipped
as Milestone 13 (see top of this file) — resolved both previously-open
residual cases. What's left is no longer feature work: a final README pass
+ screenshots/demo for the resume, and replacing the `<Your Name>`
placeholder in `LICENSE`. Typosquat/brand-similarity feature was
considered, briefly deferred, then dropped outright (2026-07-31) — not
planned. See `TODO.md` for the concrete task breakdown and current status
of everything.

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
   removed accordingly.
   **Partially reversed 2026-07-31** (see Milestone 10 above) — the
   false-positive investigation surfaced a genuine, honestly-documented
   ceiling for a lexical-only model, and the user decided the project
   should be "more than just an ML model." URLhaus (not VirusTotal) is
   going back in, plus a typosquat feature and (later) WHOIS domain age.
   Docker/deployment (the rest of what "Milestone 9" originally meant)
   is explicitly still out of scope — this reversal is about detection
   depth, not deployment infra.

## Reference

See conversation history for the full architecture diagram and per-milestone
rationale. See `TODO.md` for the concrete remaining task list.
