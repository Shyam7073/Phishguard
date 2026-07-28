"""Loads the trained model artifact once and runs inference.

This module never trains -- ml/train.py is the only place training
happens. It just loads the exported ml/models/model.joblib and turns a URL
into a verdict using the exact same feature extraction (ml/features.py)
that was used at training time, so train-time and serve-time features can
never drift apart.
"""

from pathlib import Path

import joblib

from ml.features import FEATURE_NAMES, extract_features

MODEL_PATH = Path(__file__).resolve().parents[3] / "ml" / "models" / "model.joblib"
_model = joblib.load(MODEL_PATH)


def predict(url: str) -> dict:
    features = extract_features(url)
    vector = [[features[name] for name in FEATURE_NAMES]]

    label = int(_model.predict(vector)[0])
    confidence = float(_model.predict_proba(vector)[0][label])

    return {"is_phishing": bool(label), "confidence": confidence}
