# Model card — Model 2: Winning-price landscape

*Phase 5, design Section 8. Trained 2026-08-24 on the C19 world. Provenance: A.*

**The decision this serves.** Half the inventory has no price: 50.9% of
leads never sell, and the ones that do reveal a price only at the tier that
cleared. Every decision made *before* an outcome exists needs a value for a
lead whose value was never revealed — what to pay to acquire a contact of a
given channel and credit profile, whether unsold inventory is worth a
second route, and what a segment is worth when a reserve schedule stops
being one number per tier. The alternative in use today is the pipeline
table a team ships first (baseline B0 below: sell rate x mean sold price by
recency bucket and FICO band), which conditions on selling and so answers a
systematically different question from the one being asked.

**The rule someone acts on.** Expected value per lead in dollars, compared
against a channel's cost per contact by the acquisition owner; compared
against zero (not assumed to be zero) when deciding what to do with unsold
leads; and as the per-segment starting point for the segment-level reserve
schedule that model 3's per-tier search does not yet produce.

**What is not claimed.** This card previously called the model "the
foundation for pricing". In a second-price auction with fixed reserves the
marketplace does not price leads — the auction does — and the one pricing
decision it owns (the floors) was answered by model 3 from logged bids, not
from this landscape. No dollar value is claimed for model 2 here: its three
uses are real, and none has yet been carried through to a decision in this
project. The measurable claim is the margin over the table a team would
otherwise use.

**Business question.** What would a lead fetch, including the 50.9% that
never show a price at all? Under C19, recency-suppressed demand makes the
censoring structure first-class rather than a nuisance.

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

**Decision this informs.** Lead valuation in dollars: what a buyer would
pay, and the probability the lead never sells. This is the pricing
foundation for buyer-facing lead pricing and for reserves set per segment
rather than per tier -- the survival landscape gives an expected value for
every FICO band x recency cell, which model 3's per-tier search does not
use yet. The specification test is itself a decision: a team that shipped
the textbook Tobit here would price unsold leads two orders of magnitude
too low.

**What we would do next.** (1) Extend model 3's search from six tier
multipliers to tier x FICO-band schedules, using the landscape's segment
expected values as the starting point. (2) Publish the landscape's
expected value by segment as a buyer-facing price guide. (3) Re-fit on a
real log with the same two-head structure; the participation-driven
censoring diagnosis is the part most likely to transfer.

**Reproduce.** `.venv/bin/python models/train_price_landscape.py` →
`models/out/m2_metrics.json`, `models/out/m2_price_landscape.html`.
