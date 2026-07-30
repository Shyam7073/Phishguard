# PhishGuard

A phishing URL detection system that analyzes visited URLs in real time using
a machine learning model, surfaced through a Chrome extension and a React
dashboard.

## Architecture

```
Chrome Extension ──┐
                    ├──> FastAPI Backend ──> ML Inference (URL -> phishing/legit)
React Dashboard ────┘                    └──> Database (scan history)
```

The ML training pipeline (`ml/`) runs offline and is fully decoupled from the
live serving path (`backend/`) — the backend only ever loads a trained model
artifact and runs inference on it. The system is a pure ML classifier by
design (no external threat-intel APIs) — this keeps the whole request path
easy to reason about and explain end to end.

## Repo layout

| Path | Purpose |
|---|---|
| `ml/` | Offline dataset prep, feature engineering, model training/evaluation |
| `backend/` | FastAPI service: `/scan`, `/history`, `/reports` |
| `extension/` | Chrome extension (Manifest V3) — popup + background worker |
| `dashboard/` | React + Tailwind dashboard for scan history and reports |

## Project status

- [x] Milestone 0 — Architecture & design
- [x] Milestone 1 — Repo scaffolding
- [x] Milestone 2 — Dataset collection & cleaning
- [x] Milestone 3 — Feature engineering
- [x] Milestone 4 — Model training & evaluation
- [x] Milestone 5 — Backend core (`/scan`)
- [x] Milestone 6 — Persistence layer (`/history`, `/reports`)
- [x] Milestone 7 — Chrome extension MVP
- [x] Milestone 8 — React dashboard
- [ ] Final polish (README/screenshots) — no Docker/deployment planned, keeping this a local-run resume project

## Local setup

```bash
make setup   # creates .venv and installs ml + backend + dev dependencies
make lint    # ruff + black --check
make format  # black (auto-fix)
make test    # pytest
```

Run the backend (from the repo root, so both `backend` and `ml` resolve as packages):

```bash
.venv/bin/python -m uvicorn backend.app.main:app --reload
```

Retrain the model (regenerates `ml/data/processed/dataset.csv` and
`ml/models/model.joblib` — both gitignored):

```bash
.venv/bin/python ml/prepare_dataset.py
.venv/bin/python -m ml.train
```

Load the Chrome extension: with the backend running, open
`chrome://extensions`, enable **Developer mode**, click **Load unpacked**,
and select the `extension/` folder. See `extension/README.md` for details.

Run the dashboard (with the backend running at `127.0.0.1:8000`):

```bash
cd dashboard
npm install
npm run dev
```

Then open the printed `localhost` URL. The dashboard shows scan history, a
legitimate-vs-phishing breakdown, and a CSV export button, all backed by the
same `/history` and `/reports` endpoints the extension uses.
