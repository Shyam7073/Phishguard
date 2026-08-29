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
  compares on a held-out set, exports the winner to `models/`. Winner is
  highest F1, except that an F1 gap under `F1_TIE_MARGIN` (0.001) counts as
  a tie and falls to `PREFERRED_MODEL` — see `pick_winner()` and the module
  docstring for why (it's the difference between shipping the model that was
  checked against real phishing URLs and the one that won by 0.0005 on a
  metric that can't tell them apart). Run as a module from the repo root:
  `.venv/bin/python -m ml.train`.
- `models/` — the exported artifact + `metrics.json`. The artifact **is**
  tracked in git (see the negations in `.gitignore`): the backend loads it at
  runtime, so it has to ship for deployment to work. Format depends on which
  model won — `model.ubj` (XGBoost's own versioned format, which is what
  currently ships) or `model.joblib` for a plain scikit-learn winner. See
  `export_model()` for why XGBoost doesn't get pickled: XGBoost makes no
  promise that a pickle stays loadable across versions, and this file gets
  read by whatever xgboost pip resolves at deploy time.
- `MODEL_REPORT.md` — auto-generated comparison table, confusion matrix,
  and feature importances for the winning model. Committed (small text
  file, useful to show results without retraining).

Populated through Milestone 4.
