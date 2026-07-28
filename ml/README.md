# ml/

Offline training pipeline. Nothing here runs in the live request path — it
produces a model artifact (`models/`) that the backend loads.

- `data/raw/` — untouched source datasets: `tranco_XN23N.csv` (Tranco top
  1M, rank+domain, no header) and `verified_online.csv` (PhishTank verified
  export). Gitignored — not committed, re-download if missing.
- `data/processed/dataset.csv` — cleaned, labeled, combined dataset
  (`url,label`; label 1 = phishing, 0 = legitimate). Gitignored, regenerate
  via `prepare_dataset.py`.
- `prepare_dataset.py` — Milestone 2: samples 65k legit + 65k phishing URLs
  from the raw sources, cleans/dedupes, merges, prints a quick EDA, and
  writes `data/processed/dataset.csv`.
- `features.py` — shared feature-extraction logic (17 lexical/domain/
  statistical features per URL). Imported by both this pipeline and
  `backend/app/ml_service`, so training and serving can never drift apart.
  Unit tests in `tests/test_features.py`.
- `train.py` — trains Logistic Regression, Random Forest, and XGBoost,
  compares on a held-out set, exports the best one (by F1) to `models/`.
  Run as a module from the repo root: `.venv/bin/python -m ml.train`.
- `models/` — exported model artifact (`model.joblib`) + `metrics.json`.
  Gitignored (regenerate via `train.py`).
- `MODEL_REPORT.md` — auto-generated comparison table, confusion matrix,
  and feature importances for the winning model. Committed (small text
  file, useful to show results without retraining).

Populated through Milestone 4.
