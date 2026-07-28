# backend/

FastAPI service that serves scan requests, stores history, and generates
reports.

- `app/main.py` — FastAPI app instance, mounts routers, `/health` check,
  creates DB tables on startup
- `app/api/scan.py` — `POST /scan`: runs inference, saves a `ScanRecord`
- `app/api/history.py` — `GET /history?limit=` — most recent scans first
- `app/api/reports.py` — `GET /reports` — CSV export of all scan history
- `app/ml_service/predictor.py` — loads `ml/models/model.joblib` once and
  runs inference (never trains — see `ml/train.py`)
- `app/schemas/scan.py`, `app/schemas/history.py` — Pydantic request/response models
- `app/db/database.py` — SQLite engine/session (`backend/phishguard.db`,
  gitignored); SQLAlchemy is the ORM so switching to Postgres later is just
  a connection-string change
- `app/db/models.py` — `ScanRecord` table (id, url, is_phishing,
  confidence, scanned_at)
- `tests/` — backend unit/integration tests (`TestClient` against an
  in-memory SQLite DB via `conftest.py`, so tests never touch
  `phishguard.db`)

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
  -d '{"url": "http://paypal.com.security-verify-login.tk/account/confirm"}'

curl http://127.0.0.1:8000/history
curl http://127.0.0.1:8000/reports   # downloads a CSV
```

Populated through Milestone 6 (`/scan`, `/history`, `/reports` — all working
against a real SQLite DB).
