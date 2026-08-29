# backend/

FastAPI service that serves scan requests, stores history, and generates
reports. Deployed on Render at `https://phishguard-api-yjr8.onrender.com`
(see root `README.md` → Deployment); this section covers running it locally.

- `app/main.py` — FastAPI app instance, mounts routers, `/health` check,
  creates DB tables on startup
- `app/api/scan.py` — `POST /scan` (requires `client_id`): checks
  `trusted_hosts.is_trusted_host()` first and short-circuits to a safe
  verdict if matched (skipping ML/URLhaus/RDAP entirely); otherwise runs
  all three signals concurrently (`asyncio.gather`, with ML inference on a
  thread since it's synchronous) and saves a `ScanRecord`. Concurrency
  matters here: run one after the other, the two lookups stack their 4s
  timeouts and one slow scan takes 8s+
- `app/api/history.py` — `GET /history?client_id=...&limit=` — that
  client's scans only, most recent first
- `app/api/reports.py` — `GET /reports?client_id=...` — CSV export scoped
  to that client
- `app/trusted_hosts.py` — `TRUSTED_HOSTS` env var allowlist (comma-
  separated hostnames); always trusts `localhost`/`127.0.0.1`. Exists
  because free PaaS subdomains and non-HTTPS URLs both structurally
  resemble phishing to the lexical model — see `PROJECT_PROGRESS.md`
  Milestone 15
- `app/ml_service/predictor.py` — loads the model artifact from `ml/models/`
  once at import (`model.ubj` for XGBoost, `model.joblib` for a scikit-learn
  winner) and runs inference (never trains — see `ml/train.py`)
- `app/schemas/scan.py`, `app/schemas/history.py` — Pydantic request/response models
- `app/db/database.py` — engine/session. Uses Postgres (Neon) via
  `DATABASE_URL` when set — required for deployment, since free hosts like
  Render wipe local disk on every restart. Falls back to a local SQLite
  file (`backend/phishguard.db`, gitignored) when `DATABASE_URL` is unset
- `app/db/models.py` — `ScanRecord` table (id, `client_id` (indexed), url,
  is_phishing, confidence, ml_score, urlhaus_status, domain_age_days,
  domain_age_status, verdict_reason, scanned_at). `scanned_at` is a
  timezone-aware column; `ScanRecordOut` also re-stamps UTC onto rows written
  before it was, since an offset-less timestamp gets read as *local* time by
  the dashboard
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
