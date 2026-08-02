# PhishGuard — Model Comparison Report

Trained on `dataset.csv` (130k URLs, balanced), 80/20 stratified train/test split, seed=42.

| Model | Accuracy | Precision | Recall | F1 |
|---|---|---|---|---|
| Logistic Regression | 0.7829 | 0.7824 | 0.7838 | 0.7831 |
| Random Forest | 0.9170 | 0.9261 | 0.9064 | 0.9161 |
| XGBoost | 0.9191 | 0.9311 | 0.9052 | 0.9180 |

**Winner: XGBoost** (highest F1 on the held-out test set).

Confusion matrix `[[TN, FP], [FN, TP]]`: [[12129, 871], [1232, 11768]]

Top features for the winning model:

- `is_https`: 0.2649
- `hostname_length`: 0.0994
- `has_at_symbol`: 0.0986
- `is_url_shortener`: 0.0889
- `path_length`: 0.0793
- `num_subdomains`: 0.0566
- `num_dots`: 0.0468
- `num_hyphens`: 0.0400
