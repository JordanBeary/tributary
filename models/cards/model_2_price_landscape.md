# Model card — Model 2: Winning-price landscape

*Phase 5, design Section 8. Trained 2026-08-24 on the C19 world. Provenance: A.*

**Business question.** What would buyers pay? (The foundation for pricing:
50.8% of leads never show a price — under C19, recency-suppressed demand makes
the censoring structure first-class.)

**Model.** The design's survival framing of censored regression. The waterfall
is a discrete-time hazard process over the tier ladder, so the landscape is
two LightGBM heads composed:

- **hazard** h_t(x) = P(clears tier t | reached tier t) — binary model on
  6.29M stacked (lead, offered-tier) training rows;
- **price** E[log clearing | cleared at tier t] — regression on sold leads.

P(sells at t) = h_t · prod(1-h_s, s<t); expected lead value sums tier
probabilities times tier prices; P(unsold) is the survival product. Training
uses only what a real marketplace observes: cascade depth and prices on sales.

**Evaluation (test months, n=401k).**

| Metric | Model | Baseline |
| --- | --- | --- |
| Expected-value rank corr with realized revenue | **0.859** | 0.269 (group EV table) |
| Revenue captured by top EV decile | **33.3%** | 14.7% (group EV table) |
| EV RMSE ($, unsold = 0) | **97.6** | 134.4 (group EV table) |
| Sold-price MAE ($) | **50.06** | 63.07 (tier-mean) |
| P(unsold) reliability | tight along the diagonal | — |

**Specification test — why the textbook Tobit fails here.** A Type-I Tobit
(left-censored Gaussian at the deepest reserve; custom LightGBM objective in
`models/tobit.py`, sigma profiled) was fitted on the same split. It stretches
to sigma = 1.43 in logs and its latent collapses to a median $0.18 for unsold
leads — against a median $32 top bid actually logged for those same leads
(sub-reserve bids ride the ping/post lake and were never used in training).
Censoring in this world is participation-driven, not low-valuation-driven,
and a single-sigma latent Gaussian cannot express that. The Tobit's implied
P(unsold) calibrates surprisingly well; its price level does not. Kept in the
report and in `models/out/boosters/m2_tobit.txt` as the documented
specification test.

**Honest notes.**

- The hazard head shares signal with model 1 (P(sold) = 1 - survival); the
  two models answer different questions (calibrated decisioning vs dollar
  landscape) and their agreement is a consistency check.
- Sold-price bias is -$14 (model predicts conditional medians on a
  right-skewed price distribution); the tier-mean baseline is unbiased by
  construction but 26% worse in MAE.

**Reproduce.** `.venv/bin/python models/train_price_landscape.py` →
`models/out/m2_metrics.json`, `models/out/m2_price_landscape.html`.
