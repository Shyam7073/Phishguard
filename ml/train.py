"""Milestone 4: train and compare candidate models, export the winner.

Trains Logistic Regression, Random Forest, and XGBoost on the feature
matrix from ml/features.py, evaluates each on a held-out test set, and
exports the winner to ml/models/ so the backend can load it and run
inference without ever training (see export_model for the format).

"Winner" is highest F1, with one tie-break rule (see pick_winner): when two
models land within F1_TIE_MARGIN of each other, the held-out F1 isn't
telling them apart, and the pick falls to PREFERRED_MODEL -- the one that
was checked against real phishing/borderline URLs by hand. That is not a
hypothetical: the shipped run has Random Forest at 0.9169 and XGBoost at
0.9164, a gap of 0.0005, while XGBoost has far better real-world recall
(99.3-100% vs 73.5-93% on the real phishing URLs in Milestone 14) and is
much less confidently wrong on the residual borderline-legit cases.
XGBoost is what ships, so the export step has to encode that rule -- until
it did, re-running this script silently replaced the tested, documented
model with Random Forest and overwrote the note in MODEL_REPORT.md
explaining why it shouldn't.

Run with: .venv/bin/python -m ml.train   (must run as a module, from the
repo root, so `ml` resolves as a package the same way it will for the
backend later)
"""

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier

from ml.features import FEATURE_NAMES, build_feature_matrix

DATA_PATH = Path(__file__).parent / "data" / "processed" / "dataset.csv"
MODELS_DIR = Path(__file__).parent / "models"
REPORT_PATH = Path(__file__).parent / "MODEL_REPORT.md"
SEED = 42

# An F1 gap smaller than this is noise on a 26k-row test set, not a real
# quality difference -- see the module docstring.
F1_TIE_MARGIN = 0.001
PREFERRED_MODEL = "XGBoost"


def load_data():
    df = pd.read_csv(DATA_PATH)
    X = build_feature_matrix(df["url"])
    y = df["label"]
    return train_test_split(X, y, test_size=0.2, random_state=SEED, stratify=y)


def candidate_models():
    return {
        # Logistic Regression needs scaled inputs (features here range from
        # 0/1 flags to url_length in the hundreds) -- tree-based models
        # don't care about feature scale, so only this one gets a scaler.
        "Logistic Regression": Pipeline(
            [
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(max_iter=1000, random_state=SEED)),
            ]
        ),
        "Random Forest": RandomForestClassifier(n_estimators=200, random_state=SEED, n_jobs=-1),
        "XGBoost": XGBClassifier(
            n_estimators=200, eval_metric="logloss", random_state=SEED, n_jobs=-1
        ),
    }


def pick_winner(results: dict) -> tuple[str, str | None]:
    """Highest F1, unless the preferred model is within F1_TIE_MARGIN of it.

    Returns (winner_name, tie_break_note); the note is None when the plain
    F1 ranking decided it, and a sentence for MODEL_REPORT.md when the
    tie-break did.
    """
    ranked = max(results, key=lambda name: results[name]["f1"])
    if ranked == PREFERRED_MODEL or PREFERRED_MODEL not in results:
        return ranked, None

    gap = results[ranked]["f1"] - results[PREFERRED_MODEL]["f1"]
    if gap >= F1_TIE_MARGIN:
        return ranked, None

    note = (
        f"{PREFERRED_MODEL} ships despite {ranked} taking the F1 ranking "
        f"({results[ranked]['f1']:.4f} vs {results[PREFERRED_MODEL]['f1']:.4f}, "
        f"a gap of {gap:.4f} -- under the {F1_TIE_MARGIN} tie margin). A gap "
        f"that small doesn't separate the two on held-out data, so the pick "
        f"falls to the model checked by hand against real phishing and "
        f"borderline-legit URLs. See PROJECT_PROGRESS.md Milestone 14."
    )
    return PREFERRED_MODEL, note


def export_model(model) -> Path:
    """Write the winning model in the most durable format it supports.

    XGBoost gets `save_model` (a versioned UBJSON file) rather than a
    pickle. XGBoost's own docs are explicit that pickle compatibility is
    not guaranteed across versions -- and the backend commits this artifact
    to git while installing an unpinned xgboost at deploy time, so a
    rebuild that resolves a newer version could stop being able to load it.
    `save_model`/`load_model` is the format that *is* guaranteed to keep
    working, and it round-trips the sklearn wrapper's attributes too.

    The other two candidates are plain scikit-learn estimators with no such
    format, so they still go out as joblib. predictor.py loads whichever of
    the two is present.
    """
    if hasattr(model, "save_model"):
        path = MODELS_DIR / "model.ubj"
        model.save_model(path)
        # Don't leave a stale pickle from a previous run next to the new
        # artifact -- predictor.py would have two candidates to choose from.
        (MODELS_DIR / "model.joblib").unlink(missing_ok=True)
        return path

    path = MODELS_DIR / "model.joblib"
    joblib.dump(model, path)
    (MODELS_DIR / "model.ubj").unlink(missing_ok=True)
    return path


def evaluate(model, X_test, y_test):
    preds = model.predict(X_test)
    return {
        "accuracy": accuracy_score(y_test, preds),
        "precision": precision_score(y_test, preds),
        "recall": recall_score(y_test, preds),
        "f1": f1_score(y_test, preds),
        # [[TN, FP], [FN, TP]] since labels are sorted [0, 1]
        "confusion_matrix": confusion_matrix(y_test, preds).tolist(),
    }


def top_features(model, n=8):
    """Feature importances (trees) or |coefficient| (logistic regression)."""
    clf = model.named_steps["clf"] if hasattr(model, "named_steps") else model
    if hasattr(clf, "feature_importances_"):
        scores = clf.feature_importances_
    elif hasattr(clf, "coef_"):
        scores = abs(clf.coef_[0])
    else:
        return []
    ranked = sorted(zip(FEATURE_NAMES, scores), key=lambda pair: pair[1], reverse=True)
    return ranked[:n]


def write_report(results, winner_name, winner_features, tie_break_note=None):
    lines = [
        "# PhishGuard — Model Comparison Report",
        "",
        f"Trained on `{DATA_PATH.name}` (130k URLs, balanced), 80/20 "
        f"stratified train/test split, seed={SEED}.",
        "",
        "| Model | Accuracy | Precision | Recall | F1 |",
        "|---|---|---|---|---|",
    ]
    for name, metrics in results.items():
        lines.append(
            f"| {name} | {metrics['accuracy']:.4f} | {metrics['precision']:.4f} "
            f"| {metrics['recall']:.4f} | {metrics['f1']:.4f} |"
        )
    lines += [
        "",
        f"**Winner: {winner_name}**"
        + (
            f" -- {tie_break_note}" if tie_break_note else " (highest F1 on the held-out test set)."
        ),
        "",
        f"Confusion matrix `[[TN, FP], [FN, TP]]`: " f"{results[winner_name]['confusion_matrix']}",
        "",
        "Top features for the winning model:",
        "",
    ]
    for feat, score in winner_features:
        lines.append(f"- `{feat}`: {score:.4f}")
    REPORT_PATH.write_text("\n".join(lines) + "\n")


def main():
    X_train, X_test, y_train, y_test = load_data()
    models = candidate_models()

    results = {}
    fitted = {}
    for name, model in models.items():
        print(f"Training {name}...")
        model.fit(X_train, y_train)
        fitted[name] = model
        results[name] = evaluate(model, X_test, y_test)

    print("\nResults:")
    for name, metrics in results.items():
        print(
            f"  {name:20s} acc={metrics['accuracy']:.4f} "
            f"prec={metrics['precision']:.4f} rec={metrics['recall']:.4f} "
            f"f1={metrics['f1']:.4f}"
        )

    winner_name, tie_break_note = pick_winner(results)
    winner_model = fitted[winner_name]
    print(f"\nWinner: {winner_name} (f1={results[winner_name]['f1']:.4f})")
    if tie_break_note:
        print(f"  tie-break: {tie_break_note}")

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model_path = export_model(winner_model)
    print(f"Saved winning model to {model_path}")

    metrics_path = MODELS_DIR / "metrics.json"
    metrics_path.write_text(
        json.dumps(
            {"winner": winner_name, "tie_break": tie_break_note, "results": results}, indent=2
        )
    )

    winner_features = top_features(winner_model)
    write_report(results, winner_name, winner_features, tie_break_note)
    print(f"Wrote comparison report to {REPORT_PATH}")


if __name__ == "__main__":
    main()
