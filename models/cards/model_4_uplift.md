# Model card — Model 4: Marketing uplift

*Phase 5, design Section 8. Trained 2026-08-24 on the C19 world. Provenance: A.*

**The decision this serves.** The nurture program messages 85% of acquired
contacts — about 2.19M messages a year — and measures itself in opens and
clicks, the only outcome its own silo can see and not a business outcome at
all. The decision is which contacts to enrol. Today the answer is
"everyone", which spends about 1.77M messages a year on 588,545 contacts
whose incremental effect is indistinguishable from zero.

**Why a model, honestly.** At the granularity the program can act on (five
engagement segments by seven channels), a grouped arm-difference table gets
close to the same ranking; this model's marginal contribution over that
table is regularization across sparse cells and out-of-fold scoring, and
that should not be oversold. What is genuinely a modeling result rather
than a query result is the comparison below: ranking by predicted uplift
earns positive area above random, while ranking by predicted *response* —
the near-universal default of targeting likely converters — scores worse
than random, because in a pool with an 84.5% base application rate the
high-intent contacts apply whether or not they are messaged. That finding
is what changes the policy.

**The rule someone acts on.** Enrol engagement segment 5; suspend segments
1-4; hold the suspended segments for a quarter and watch their application
rate. Owner: the marketing program owner. The value is small on revenue
(about 866 incremental applicants a year, roughly $249,519) and real on
focus and cost (about 1.77M messages avoided; the per-message cost lives in
no silo, so the saving is stated as a count for marketing to price).

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

**Decision this informs.** The send policy: whom the nurture program
should message at all. The model ranks the concentrated segment first and
shows response-model targeting is worse than random, so the actionable
policy is "message engagement segment 5, stop messaging segments 1-4". Its
value is small on the revenue side and real on the cost side: at the
injected +0.52pp, segment-5-only messaging yields about 870 incremental
applicants a year (roughly $250k of auction revenue) while avoiding about
1.77M messages to contacts whose uplift is indistinguishable from zero
(`models/out/experiment_power.json`; per-message cost is not in any silo).

**What we would do next.** (1) A follow-up test sized for the segment-5
effect rather than the pooled one: about 266k segment-5 contacts at the
current 85/15 split, or 134k at 50/50, against 166k available today
(`docs/experiment_readout.md`). (2) Obtain the per-message send cost so the
avoided sends are priced. (3) Keep the covariate set equal to the action
space; add a dimension only when the program can target on it.

**Reproduce.** `.venv/bin/python models/train_uplift.py` →
`models/out/m4_metrics.json`, `models/out/m4_uplift.html`.
