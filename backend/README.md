# backend/

FastAPI service that serves scan requests, stores history, and generates
reports. Deployed on Render at `https://phishguard-api-yjr8.onrender.com`
(see root `README.md` → Deployment); this section covers running it locally.

- `app/main.py` — FastAPI app instance, mounts routers, `/health` check,
  creates DB tables on startup
- `app/api/scan.py` — `POST /scan` (requires `client_id`): checks
  `trusted_hosts.is_trusted_host()` first and short-circuits to a safe
  verdict if matched (skipping ML/URLhaus/RDAP entirely); otherwise runs
  the full inference pipeline and saves a `ScanRecord`
- `app/api/history.py` — `GET /history?client_id=...&limit=` — that
  client's scans only, most recent first
- `app/api/reports.py` — `GET /reports?client_id=...` — CSV export scoped
  to that client
- `app/trusted_hosts.py` — `TRUSTED_HOSTS` env var allowlist (comma-
  separated hostnames); always trusts `localhost`/`127.0.0.1`. Exists
  because free PaaS subdomains and non-HTTPS URLs both structurally
  resemble phishing to the lexical model
- `app/ml_service/predictor.py` — loads `ml/models/model.joblib` once and
  runs inference (never trains — see `ml/train.py`)
- `app/schemas/scan.py`, `app/schemas/history.py` — Pydantic request/response models
- `app/db/database.py` — engine/session. Uses Postgres (Neon) via
  `DATABASE_URL` when set — required for deployment, since free hosts like
  Render wipe local disk on every restart. Falls back to a local SQLite
  file (`backend/phishguard.db`, gitignored) when `DATABASE_URL` is unset.
  **Dev-machine guard:** `DATABASE_URL` also lives in the local `.env` (it
  is needed to run `seed_demo.py --deployed`), which used to mean running
  `uvicorn` locally wrote real rows into the deployed Neon database. A
  remote `DATABASE_URL` seen while a `.env` file is present is now treated
  as a dev machine holding a production credential, and SQLite is used
  instead with a warning on stdout. The deployment has no `.env` — Render
  supplies `DATABASE_URL` through its own environment — so the guard never
  engages there and no Render configuration is needed. Override on a dev
  machine with `PHISHGUARD_DEPLOYED=1` when writing to the deployed
  database is genuinely the intent
- `app/db/models.py` — `ScanRecord` table (id, `client_id` (indexed), url,
  is_phishing, confidence, ml_score, urlhaus_status, domain_age_days,
  domain_age_status, verdict_reason, scanned_at)
- `tests/` — backend unit/integration tests (`TestClient` against an
  in-memory SQLite DB via `conftest.py`, so tests never touch
  `phishguard.db`/Neon)

## Running it

Run as a module from the **repo root** (not from inside `backend/`) so both
the `backend` and `ml` packages resolve correctly — this mirrors how
`ml/train.py` is run:

```bash
.venv/bin/python -m uvicorn backend.app.main:app --reload
```

Then try it:

```bash
curl -X POST http://127.0.0.1:8000/scan \
  -H "Content-Type: application/json" \
  -d '{"url": "http://paypal.com.security-verify-login.tk/account/confirm", "client_id": "test"}'

curl "http://127.0.0.1:8000/history?client_id=test"
curl "http://127.0.0.1:8000/reports?client_id=test"   # downloads a CSV
```

`client_id` can be any string locally — the extension generates a real
UUID per install in production (see `extension/client-id.js`).

Populated through Milestone 6 (`/scan`, `/history`, `/reports` — all working
against a real SQLite DB). Multi-tenant `client_id` scoping, Postgres
support, and `trusted_hosts.py` added in Milestone 15.
