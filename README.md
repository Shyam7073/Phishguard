# PhishGuard

A Chrome extension that tells you whether the page you're on is a phishing
site, and *why* it thinks so.

There's a FastAPI backend behind it that combines three signals into one
verdict, and a small React dashboard for looking back at what got scanned.

The "why" part is the bit I actually cared about. A bare confidence number
is useless to anyone — 87% what? So every verdict comes back with a
sentence:

> Likely phishing, 99.7% — confirmed malicious, found on the URLhaus blocklist.

> Looks safe, 65% — ML model flagged this, but the domain is long-established, likely a false positive.

## Screenshots

| Dashboard | Extension popup |
|---|---|
| ![Dashboard](docs/screenshots/dashboard.png) | ![Popup](docs/screenshots/popup.png) |

## How it works

The extension and the dashboard both talk to the same backend. Every time
you finish navigating somewhere, the background worker fires a `POST /scan`
with the URL. The backend runs three checks concurrently:

1. **ML inference** on 17 lexical features of the URL string. XGBoost, runs
   locally, no network.
2. **URLhaus blocklist lookup** (abuse.ch). One HTTP call, cached 15 minutes.
3. **RDAP domain-age lookup** via `whodap`. One HTTP call, cached 24 hours.

Then `combine_verdict()` in [backend/app/verdict.py](backend/app/verdict.py)
merges them, the scan gets written to the database, and it shows up in
`/history` and `/reports`.

Both network lookups fail soft. Timeout, missing API key, a registry that
doesn't do RDAP, a malformed response — all of it degrades to `"unknown"`
and the verdict falls back to whatever's left, with the degradation spelled
out in the reason text. Neither one can take a scan down.

### The combining rules

They're asymmetric on purpose: a positive hit can override a verdict, but
an *absence* of evidence never inverts one.

A URLhaus hit wins outright and skips everything else — a known-bad URL is
a fact, not a guess. Otherwise the ML score decides at the usual 0.5
threshold, with one exception: if the domain is 365+ days old and the ML
score is under 0.90, the verdict flips back to legitimate. That's the fix
for the false positives described below. A lexical model has no way to know
a domain has been around since 2007.

A brand-new domain does *not* get the mirror treatment. It won't flip a
legitimate call to phishing, it just gets noted in the reason. Flipping
would invent a whole new false-positive class covering every personal site,
side project and startup registered last month, and I have no test data
saying that's a good trade.

## The model

17 features, all computed from the URL string itself. No page fetch, no
network call, nothing that could be slow or dangerous:

- **Lengths** — `url_length`, `hostname_length`, `path_length`
- **Character counts** — dots, hyphens, underscores, slashes, digits,
  special chars, plus `digit_ratio`
- **Structure** — `num_subdomains` (via `tldextract`), `num_query_params`
- **Red flags** — `has_ip_address`, `has_at_symbol`, `is_https`,
  `has_suspicious_word`, `is_url_shortener`

[ml/features.py](ml/features.py) is imported by both the training script and
the backend, so training-time and serving-time features can't drift apart.
That's the whole reason it's a shared module and not two copies.

Training data is 130,000 balanced URLs — 65k legitimate from Tranco's top
1M, 65k verified phishing from PhishTank. Logistic Regression, Random Forest
and XGBoost all get trained and compared on a held-out 20% split. Full table
in [ml/MODEL_REPORT.md](ml/MODEL_REPORT.md).

Shipped model: XGBoost. 91.77% accuracy, 0.9164 F1.

Random Forest actually scores a hair higher on F1 (0.9169), which is inside
the noise on a test set this size. XGBoost wins on the things the test set
doesn't measure — much better recall on real phishing URLs I collected by
hand, and less confidently wrong on the borderline-legit cases. `pick_winner()`
in [ml/train.py](ml/train.py) encodes that rule so a retrain doesn't quietly
swap the model out from under you.

### Why the accuracy kept going *down*

Early runs hit 99.6%. Then 96.5%. Now 91.8%. Every one of those drops was
me removing a way the model was cheating, and honestly this is where most of
the actual engineering in this project went.

The root cause is always the same shape. Tranco hands you bare apex domains
(`github.com`), not URLs. So the synthetic legitimate URLs I generated from
them had structural tells that the real web doesn't have, and the model
learned the tells instead of learning phishing.

| # | What I saw | What was actually wrong | Fix |
|---|---|---|---|
| 1 | 99.6% across all three models | 100% of legit URLs had no path at all | Generate realistic paths |
| 2 | `num_subdomains` was 88% of feature importance | Tranco never includes `www.` | Add subdomain prefixes |
| 3 | `mail.google.com/mail/u/0/` flagged | `num_slashes >= 6` appeared in 0% of legit rows | Compositional path generator |
| 4 | `launchpad.ccbp.in/` at 72% phishing | Bare trailing slash badly under-represented | Reweight bare-root shapes |
| 5 | A real Google search URL at 99.9996% | No legit URL in training exceeded 213 chars | Add tracking-param blobs |
| 6 | A GitHub commit URL at 98.9% | `digit_ratio >= 0.6` was 120x rarer in legit rows | Add hex + numeric token shapes |

Numbers 4, 5 and 6 came from people actually using the thing and telling me
it was wrong, not from anything I'd have caught on my own.

Each one got diagnosed with per-feature contribution analysis
(`booster.predict(..., pred_contribs=True)`) rather than guessing, then
confirmed with a by-class coverage audit: look for any feature value that
shows up in 0.5%+ of one class and literally 0% of the other. That gap is
the bug, every single time. It has never once not been the bug.

Every fix went into the data generator
([ml/prepare_dataset.py](ml/prepare_dataset.py)). The model itself never got
more complicated. Each drop in accuracy is a fake signal being taken away,
which makes the lower number the more trustworthy one.

## Repo layout

```
ml/                            offline only — dataset prep, features, training
backend/                       FastAPI: /scan, /history, /reports, /health
  app/threat_intel/            URLhaus + RDAP lookups, shared TTL cache
  app/trusted_hosts.py         allowlist that bypasses the model entirely
extension/                     Chrome extension (MV3), background worker + popup
dashboard/                     React + Tailwind
```

Training and serving are fully decoupled. `ml/` produces a model artifact,
`backend/` only ever loads and runs it — it has no training code path at
all. Dependencies are split the same way (`ml/requirements.txt` vs
`backend/requirements.txt`) so the deployed API never installs pandas or
matplotlib.

## Setup

```bash
make setup   # .venv + ml + backend + dev dependencies
```

Then a `.env` in the repo root (it's gitignored):

```
URLHAUS_AUTH_KEY=      # free, from auth.abuse.ch
DATABASE_URL=          # Postgres connection string; unset = local SQLite file
TRUSTED_HOSTS=         # comma-separated hostnames that skip all three checks
```

All three are optional. Without `URLHAUS_AUTH_KEY` the blocklist lookup just
reports `"unknown"` and you get ML + domain age. Without `DATABASE_URL` you
get a SQLite file next to the code, which is fine locally and useless on
Render (free dynos wipe the disk on restart, so deployment needs Postgres).
`localhost` and `127.0.0.1` are always trusted regardless of what's in
`TRUSTED_HOSTS`.

### Train the model

The processed dataset is gitignored (the trained model isn't — the backend
loads it at runtime, so it has to ship). To regenerate from scratch, drop
the Tranco and PhishTank CSVs into `ml/data/raw/` and:

```bash
.venv/bin/python ml/prepare_dataset.py   # -> ml/data/processed/dataset.csv
.venv/bin/python -m ml.train             # -> ml/models/model.ubj + MODEL_REPORT.md
```

### Run everything

Backend, from the repo root so `backend` and `ml` both resolve as packages:

```bash
.venv/bin/python -m uvicorn backend.app.main:app --reload
```

API docs land at `http://127.0.0.1:8000/docs`.

Dashboard:

```bash
cd dashboard && npm install && npm run dev
```

Extension: `chrome://extensions` → Developer mode → Load unpacked → pick the
`extension/` folder. Note that `API_BASE` and `DASHBOARD_URL` in
`background.js` and `popup.js` point at the deployed Render and Vercel URLs
by default. Switch them to `http://127.0.0.1:8000` and your Vite dev server
if you're testing locally. More detail in
[extension/README.md](extension/README.md).

## Tests

```bash
make test
make lint    # ruff + black --check
```

Backend tests run FastAPI's `TestClient` against an in-memory SQLite
database (`StaticPool`, dependency-overridden in `conftest.py`), so they
never touch the real database. Both threat-intel lookups are monkeypatched
too, which means zero network calls and a suite that doesn't break when a
blocklist changes underneath it.

Worth saying that mocks have limits and this project hit them twice. A naive
`datetime` crash on certain RDAP registries, and `whodap` re-fetching IANA's
bootstrap registry on *every single call* and blowing past the timeout —
neither of those was ever going to show up in a mocked test. Both only
turned up in live smoke tests against real domains. So every milestone gets
checked end-to-end against a running backend, not just the test suite.

## Known limitations

Not hidden in a footnote. These are the real edges:

- **RDAP coverage isn't universal.** Solid for gTLDs (it's mandatory for
  `.com`/`.org`/`.net`), patchy for some ccTLDs. Falls back to `"unknown"`.
- **The domain-age rescue only applies to borderline calls.** A compromised
  or deliberately aged domain hosting real phishing still needs a confident
  ML score or a URLhaus hit to get caught. That's the trade, and I'd make it
  again.
- **Tranco rank isn't legitimacy.** The top 1M contains parked and junk
  domains, so some fraction of the "legitimate" labels are just wrong.
- **Lexical features can't see content.** No page fetch, no DOM, no favicon
  or visual similarity. That's on purpose — safely fetching arbitrary
  possibly-malicious pages is a much harder problem than it sounds like, and
  it isn't this project.
- **`http://` is a 100%-confidence blind spot.** There are zero legitimate
  `http://` examples in the training data, so the model learned an absolute
  rule off zero counterexamples instead of a probabilistic one. Known, not
  fixed, documented in `PROJECT_PROGRESS.md` Milestone 15.
- **Free PaaS subdomains score as phishing.** `*.vercel.app`,
  `*.onrender.com`, `*.netlify.app` — lexically they're indistinguishable
  from brand-squatting on free hosting, because structurally they *are* the
  same thing. Worked around for this project's own dashboard with the
  `TRUSTED_HOSTS` allowlist rather than by retraining.
- **No Docker.** Render and Vercel both build straight from the repo. A
  scope call, not an oversight.
- **CORS is wide open and there's no auth.** `client_id` is identification,
  not authentication. Fine for something shared with a handful of friends,
  nowhere near fine for a public API.

## Deployment

| Component | Platform | URL |
|---|---|---|
| Backend | Render | `phishguard-api-yjr8.onrender.com` |
| Database | Neon (Postgres) | — |
| Dashboard | Vercel | `phishguard-gray.vercel.app` |

There's no login. Each extension install generates a random `client_id`
(`crypto.randomUUID()`) on first run, stashes it in `chrome.storage.local`,
and sends it with every scan. `/history` and `/reports` filter on it, so
several people can run the extension against the same backend and each only
sees their own scans.

Again — identification, not authentication. Clearing extension storage or
reinstalling gives you a fresh `client_id` and orphans the old history. At
this scale that's an acceptable trade; at any other scale it obviously
isn't.

`PROJECT_PROGRESS.md` Milestone 15 has the full write-up, including the two
false-positive classes I only found *because* I deployed it (the `http://`
scheme one and the free-PaaS-subdomain one) and why both got mitigated
rather than retrained away.

## Status

All 15 milestones done and live. `TODO.md` has the task-level breakdown,
`PROJECT_PROGRESS.md` is the full per-milestone engineering log with every
false-positive investigation written up as it happened.
