# ml/

Offline training pipeline. Nothing here runs in the live request path — it
produces a model artifact (`models/`) that the backend loads.

- `data/raw/` — untouched source datasets: `tranco_XN23N.csv` (Tranco top
  1M, rank+domain, no header) and `verified_online.csv` (PhishTank verified
  export). Gitignored — not committed, re-download if missing.
- `data/processed/dataset.csv` — cleaned, labeled, combined dataset
  (`url,label`; label 1 = phishing, 0 = legitimate). Gitignored, regenerate
  via `prepare_dataset.py`.
- `prepare_dataset.py` — samples 65k legit + 65k phishing URLs from the raw
  sources, cleans/dedupes, merges, prints a quick EDA, and writes
  `data/processed/dataset.csv`. It does **not** just concatenate the two
  sources: Tranco gives bare domains while most phishing URLs have a path, so
  the script synthesises realistic paths, query strings, tracking params and
  hex segments onto the legitimate domains. Without that the model just learns
  "has a path → phishing". Every false positive found in live testing was
  fixed here rather than in the model, and each fix is documented inline
  against the specific URL that exposed it — this is the densest and most
  important file in the pipeline.
- `features.py` — shared feature-extraction logic (17 lexical/domain/
  statistical features per URL). Imported by both this pipeline and
  `backend/app/ml_service`, so training and serving can never drift apart.
  Unit tests in `tests/test_features.py`.
- `train.py` — trains Logistic Regression, Random Forest, and XGBoost,
  compares on a held-out set, exports the best one (by F1) to `models/`.
  Run as a module from the repo root: `.venv/bin/python -m ml.train`.
  **Careful:** the shipped artifact is a *manual* override. Random Forest wins
  on F1 by 0.0005, but XGBoost is far better on real phishing URLs, so
  XGBoost was exported by hand (rationale in `MODEL_REPORT.md`). That override
  lives in prose, not in code — re-running `train.py` as it stands will
  overwrite `model.joblib` with Random Forest.
- `models/` — exported model artifact (`model.joblib`) + `metrics.json`.
  Both are **committed**. `.gitignore` ignores `models/*.joblib`, `*.pkl` and
  `*.onnx` in general and then re-includes this one artifact, because
  `backend/app/ml_service/predictor.py` loads it at import — a deployment with
  no artifact in the repo does not start at all.
- `MODEL_REPORT.md` — auto-generated comparison table, confusion matrix,
  and feature importances for the winning model. Committed (small text
  file, useful to show results without retraining).

Populated through Milestone 4; the generator was revised repeatedly
afterwards as live false positives were diagnosed.
