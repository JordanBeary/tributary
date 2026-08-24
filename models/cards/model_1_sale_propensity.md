# Model card — Model 1: Sale propensity

*Phase 5, design Section 8. Trained 2026-08-24 on the C19 world. Provenance: A.*

**Business question.** Which leads will sell, and at which tier?

**Model.** LightGBM binary classifier for P(sold), isotonic-calibrated, plus a
multiclass head for P(tier | sold); their product prices the full question.
Trained on `fct_leads` (the unified warehouse — these features exist nowhere
in any single silo).

**Data and split.** 2.40M auctioned leads over 12 months; temporal split:
train = first 8 months (1.60M), validation = months 9–10 (401k; early stopping
and calibration), test = months 11–12 (401k, untouched until evaluation).

**Features.** The auction-time contract in `models/common.py`: application
payload (loan amount, purpose, FICO band, state, income, employment length),
submission timing, marketing acquisition attributes and pre-submission message
activity (via ER), and the consumer-entity history (application sequence,
days since prior application with the C19 recency buckets, days since prior
sales). Leakage exclusions are explicit in `LEAKAGE_COLUMNS`; notably
`consumer_applications_total` counts future applications and is excluded.

**Evaluation (test months).**

| Metric | Model | Group-rate baseline (recency x FICO) | Global rate |
| --- | --- | --- | --- |
| ROC-AUC | **0.994** | 0.633 | 0.500 |
| PR-AUC | **0.995** | 0.579 | 0.490 |
| Brier | **0.027** | 0.235 | 0.250 |
| ECE (10 bins) | **0.0017** | 0.0168 | 0.0164 |

Tier head (sold test leads, n=196,720): log-loss **1.096** vs 1.220 for the
group tier-mix baseline; accuracy 58.3% vs 57.7% (tier 1 is 58% of sales, so
accuracy saturates; the distributional metric is the honest one).

**Honest notes.**

- Discrimination this high is a property of the synthetic world: given the
  payload and the recency bucket, the C19 demand model is low-noise, so the
  sold outcome is close to separable. The transferable evidence is the
  calibration discipline and the leakage contract, not the AUC.
- Isotonic calibration on a temporally-adjacent validation window held up on
  the test months (ECE 0.0017); the raw scores were already near-calibrated
  (ECE 0.0031).

**Reproduce.** `.venv/bin/python models/train_sale_propensity.py` →
`models/out/m1_metrics.json`, `models/out/m1_sale_propensity.html`, boosters
in `models/out/boosters/` (git-ignored; reproducible from the warehouse).
