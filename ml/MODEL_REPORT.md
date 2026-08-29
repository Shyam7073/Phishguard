# PhishGuard — Model Comparison Report

Trained on `dataset.csv` (130k URLs, balanced), 80/20 stratified train/test split, seed=42.

| Model | Accuracy | Precision | Recall | F1 |
|---|---|---|---|---|
| Logistic Regression | 0.7638 | 0.7553 | 0.7806 | 0.7677 |
| Random Forest | 0.9179 | 0.9281 | 0.9060 | 0.9169 |
| XGBoost | 0.9177 | 0.9307 | 0.9026 | 0.9164 |

**Winner: XGBoost** -- manually overridden despite Random Forest's narrower F1
win (0.9169 vs 0.9164, a gap under 0.001). Per project policy, an F1 gap
this small is re-checked against real test cases before trusting the
automatic pick: XGBoost has far stronger real-world phishing recall
(99.3-100% vs RF's 73.5-93% on 5 real phishing test URLs) and better
calibration on the residual borderline-legit cases
(`twitter.com/anthropicai`: XGBoost 71.4% vs RF's 95.4%, both wrong but
XGBoost far less confidently so).

Confusion matrix `[[TN, FP], [FN, TP]]`: [[12126, 874], [1266, 11734]]

Top features for the winning model:

- `is_https`: 0.3018
- `hostname_length`: 0.1090
- `path_length`: 0.0884
- `is_url_shortener`: 0.0879
- `has_at_symbol`: 0.0814
- `num_dots`: 0.0568
- `num_subdomains`: 0.0537
- `num_hyphens`: 0.0371
