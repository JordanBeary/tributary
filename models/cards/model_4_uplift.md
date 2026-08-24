# Model card — Model 4: Marketing uplift

*Phase 5, design Section 8. Trained 2026-08-24 on the C19 world. Provenance: A.*

**Business question.** Who should we message at all?

**Model.** Cross-fitted T-learner on the randomized nurture experiment at
contact grain (`fct_marketing_contacts`, 859k contacts, 85/15 treated/holdout):
one logistic regression per arm on one-hot covariates, uplift = P(apply |
treated) - P(apply | control), every contact scored out-of-fold (2 folds
stratified by arm).

**Power-driven design choices (the honest core of this card).** The injected
effect is +0.115pp pooled, concentrated ~4.5x in one engagement segment
(~0.52pp) — below the per-segment sampling noise of a flexible learner's
control model (~1.1pp per 50% fold). Three choices follow, each verified
against the failure it prevents:

- **Linear base learner.** A LightGBM T-learner produced level-correct but
  rank-noisy uplift. The calibration artifact itself measured heterogeneity
  with a logistic-per-arm T-learner; matching it is both principled and
  power-appropriate.
- **Covariates = the action space** (engagement segment, acquisition
  channel). State is not actionable for send-targeting and its ~50 small
  control cells feed pure arm-difference noise into the uplift. Acquisition
  month is excluded as *imbalanced by construction* (control mean month 20.2
  vs treated 19.1 — the engine's inverse construction correlates assignment
  with converter/prospect composition over time); including it biased mean
  uplift to -3.1pp via cross-arm extrapolation.
- **Cross-fitting** instead of a train/test split, so the small control arm
  is never halved for evaluation.

**Evaluation (out-of-fold, n=859k).**

| Metric | Value |
| --- | --- |
| AUUC above random | **+1.9e-4** — 68% of the oracle ceiling (+2.7e-4); response-model targeting: **-5.2e-4** |
| Mean predicted uplift | **+0.107pp** (injected +0.115pp) |
| Concentrated segment ranked first | **yes** (predicted +0.46pp vs injected +0.52pp) |
| Segment rank agreement (Spearman) | 0.90 |

A methods note that mattered: predicted uplift takes ~35 distinct values
(segment x channel cells), and mart row order correlates with converter
status by the engine's construction — stable sort tie-breaking fabricated a
35x-inflated oracle curve until ties were broken by a seeded shuffle
(`uplift_curve`).

Response-model targeting (rank by predicted application rate) is *worse than
random* here — high-intent contacts apply anyway — which is the standard
argument for uplift modeling, realized in the data.

**Honest notes.**

- The pooled experiment is underpowered (D10; CI on the ATE spans zero), so
  ranking metrics are the evaluation, per the Phase 5 handoff.
- The gain curve is noisy at small targeting fractions; the reliable read is
  the segment ordering, which is also the granularity a send-policy acts on.

**Reproduce.** `.venv/bin/python models/train_uplift.py` →
`models/out/m4_metrics.json`, `models/out/m4_uplift.html`.
