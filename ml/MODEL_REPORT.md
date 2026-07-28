# PhishGuard — Model Comparison Report

Trained on `dataset.csv` (130k URLs, balanced), 80/20 stratified train/test split, seed=42.

| Model | Accuracy | Precision | Recall | F1 |
|---|---|---|---|---|
| Logistic Regression | 0.7958 | 0.8288 | 0.7455 | 0.7850 |
| Random Forest | 0.9615 | 0.9571 | 0.9662 | 0.9616 |
| XGBoost | 0.9651 | 0.9604 | 0.9702 | 0.9653 |

**Winner: XGBoost** (highest F1 on the held-out test set).

Confusion matrix `[[TN, FP], [FN, TP]]`: [[12480, 520], [387, 12613]]

Top features for the winning model:

- `num_digits`: 0.1819
- `is_https`: 0.1316
- `path_length`: 0.1018
- `num_subdomains`: 0.0933
- `num_slashes`: 0.0875
- `is_url_shortener`: 0.0692
- `hostname_length`: 0.0691
- `num_hyphens`: 0.0576
