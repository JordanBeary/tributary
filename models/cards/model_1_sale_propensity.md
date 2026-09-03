# Model card — Model 1: Sale propensity

*Phase 5, design Section 8. Trained 2026-08-24 on the C19 world. Provenance: A.*

**The decision this serves — stated honestly.** Nothing in this marketplace
turns on knowing in advance whether a lead will sell: every lead is
auctioned, there is no triage gate, and the waterfall returns the true
answer minutes later for free. A prediction superseded by cheap ground
truth is not a decision input, and the 0.994 AUC below is the tell rather
than the achievement — a model that accurate on a question that cheap
indicates the question carries no decision.

What this model is legitimately for, in order of weight:

1. **The project's calibration and leakage exhibit.** This is where the
   auction-time feature contract is defined and enforced — including the
   exclusion of `consumer_applications_total`, which counts a consumer's
   *future* applications and would have inflated every model on the site.
   Calibrated probabilities (ECE 0.0017 against 0.0168 for the group-rate
   table) are what make an expected value a dollar figure. That discipline
   transfers to any real system; the AUC does not.
2. **The probability component of a lead's value before money is spent.**
   The real upstream decision is acquisition — what to pay for a contact of
   a given channel and credit profile, where per-contact margins run from
   -$9 (display) to +$288 (organic). That needs P(sells) x E[price | sale].
   Model 2 computes it directly and better, so this use is largely
   redundant.
3. **A consistency check on model 2**, whose hazard head implies the same
   P(sold) by a different route.

The decision that *would* make this model load-bearing — accepting or
declining inbound third-party leads at an offered price in milliseconds,
before any auction runs — does not exist in this simulated world. Adding it
would be a design change, not a modeling one, and it has not been
retrofitted here.

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

**Decision this informs.** Pre-auction lead decisioning: a calibrated
P(sold) x P(tier | sold) is the expected-value input for routing a lead to
the buyers most likely to clear it, for setting seller-side expectations on
a batch, and for the prior a routing bandit (design model 5) would start
from. Calibration, not discrimination, is what makes the probabilities
usable in a decision: an ECE of 0.0017 means a predicted 30% sells 30% of
the time.

**What we would do next.** (1) Use the model 2 hazard head as the
consistency check (P(sold) = 1 - survival) and publish the agreement.
(2) Report calibration within recency bucket and FICO band, the two
dimensions a routing policy would act on. (3) Treat the AUC as
non-transferable and re-validate on any real log before it informs a
decision.

**Reproduce.** `.venv/bin/python models/train_sale_propensity.py` →
`models/out/m1_metrics.json`, `models/out/m1_sale_propensity.html`, boosters
in `models/out/boosters/` (git-ignored; reproducible from the warehouse).
