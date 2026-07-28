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

## Next up: Milestone 8 — React Dashboard
- [ ] Scan history table
- [ ] One simple stats chart (e.g. phishing vs legit over time)
- [ ] Report export UI (Tailwind styling)

## Milestone 9 — Polish & deployment
- [ ] Dockerize backend
- [ ] Deployment (e.g. Render/Railway/Fly.io)
- [ ] Final README pass, screenshots/demo for resume

## Known issues / open items
- No git commits made yet — repo has untracked scaffolding files only,
  waiting on you to review and commit when ready.
- LICENSE file has a placeholder `<Your Name>` — replace with your actual name.
- Extension and dashboard setup instructions not yet added to root README
  (will be added once Milestones 7/8 land).
