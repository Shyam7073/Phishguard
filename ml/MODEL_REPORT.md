# PhishGuard — Model Comparison Report

Trained on `dataset.csv` (130k URLs, balanced), 80/20 stratified train/test split, seed=42.

| Model | Accuracy | Precision | Recall | F1 |
|---|---|---|---|---|
| Logistic Regression | 0.8073 | 0.8026 | 0.8152 | 0.8088 |
| Random Forest | 0.9381 | 0.9449 | 0.9304 | 0.9376 |
| XGBoost | 0.9408 | 0.9510 | 0.9295 | 0.9401 |

**Winner: XGBoost** (highest F1 on the held-out test set).

Confusion matrix `[[TN, FP], [FN, TP]]`: [[12377, 623], [917, 12083]]

Top features for the winning model:

- `is_https`: 0.2072
- `num_digits`: 0.1818
- `is_url_shortener`: 0.1044
- `path_length`: 0.1013
- `has_at_symbol`: 0.0756
- `hostname_length`: 0.0664
- `num_subdomains`: 0.0534
- `num_hyphens`: 0.0472
