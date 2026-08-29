"""Loads the trained model artifact once and runs inference.

This module never trains -- ml/train.py is the only place training
happens. It just loads the exported artifact from ml/models/ and turns a
URL into a verdict using the exact same feature extraction (ml/features.py)
that was used at training time, so train-time and serve-time features can
never drift apart.

Two formats are supported, in preference order:

- `model.ubj`, XGBoost's own versioned format, which is what ml/train.py
  writes when XGBoost wins. This is the one that ships. It's used in
  preference to a pickle because XGBoost does not guarantee pickle
  compatibility across versions, and this artifact is committed to git and
  then loaded by whatever xgboost version pip resolves at deploy time.
- `model.joblib`, for the two plain scikit-learn candidates, which have no
  equivalent native format.
"""

from pathlib import Path

from ml.features import FEATURE_NAMES, extract_features

MODELS_DIR = Path(__file__).resolve().parents[3] / "ml" / "models"
XGBOOST_MODEL_PATH = MODELS_DIR / "model.ubj"
SKLEARN_MODEL_PATH = MODELS_DIR / "model.joblib"


def _load_model():
    if XGBOOST_MODEL_PATH.exists():
        from xgboost import XGBClassifier

        model = XGBClassifier()
        model.load_model(XGBOOST_MODEL_PATH)
        return model

    if SKLEARN_MODEL_PATH.exists():
        import joblib

        return joblib.load(SKLEARN_MODEL_PATH)

    raise FileNotFoundError(
        f"No model artifact in {MODELS_DIR}. Run `python -m ml.train` to create one."
    )


_model = _load_model()


def predict(url: str) -> dict:
    features = extract_features(url)
    vector = [[features[name] for name in FEATURE_NAMES]]

    # _model.classes_ is [0, 1] (legit, phishing), so index 1 is always the
    # phishing-class probability regardless of which class predict() picks.
    phishing_probability = float(_model.predict_proba(vector)[0][1])

    return {
        "is_phishing": phishing_probability >= 0.5,
        "phishing_probability": phishing_probability,
    }
