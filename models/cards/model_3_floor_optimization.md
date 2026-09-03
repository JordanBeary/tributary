# Model card — Model 3: Reserve/floor optimization

*Phase 5, design Section 8. Built 2026-08-24 on the C19 world. Provenance: A.*

**The decision this serves.** Six numbers in the auction configuration —
the reserve price at each tier — set for every one of 2.4M leads a year
whether it sells and at what price. Tier 1 carries 83% of revenue and its
median clearing price equals its floor in every FICO band, so for most of
the revenue base the floor *is* the price, not a backstop. Today those
numbers were calibrated once and left alone; sell-through by tier is
visible on a dashboard, but whether a different schedule would earn more is
not, because the comparison was never run.

**Why a counterfactual and not a report.** The intuition a business rule
would encode is wrong in both directions: a uniform 10% floor increase
*reduces* revenue per lead ($87.18 to $86.90), a 20% increase costs more,
and the global sweep peaks exactly at today's level. All of the gain is in
reshaping across tiers — tier 1 up, deep tiers cut to a fifth — which no
rule of thumb produces and no dashboard reveals, and which cannot be A/B
tested tier by tier because each tier changes what cascades into the next.

**The rule someone acts on.** The six recommended floors, staged (tier 1 to
x1.10 and deep tiers to x0.50 first), with lead-level randomized
multipliers from day one so the lift is measured rather than assumed.
Guardrails: tier-1 sell-through (28.4% today) and per-buyer participation.
Stop rule: the schedule stops paying if buyers give back more than about
19% of the tier-1 increase in shaded bids, which the randomized arm
measures directly. Owner: the yield and pricing function, with operations
consulted on roughly a doubling of deep-tier volume.

**Business question.** What reserve schedule maximizes expected revenue per
lead (EPL)?

**Method.** Counterfactual replay of 2.40M logged waterfalls. The lake logs
every bid — sub-reserve included — and buyers bid valuations independent of
the reserve, so any candidate schedule replays exactly wherever the logged
cascade reached: a lead sells at the first tier whose candidate floor its
logged top bid clears, at max(second bid, floor). Replay at the deployed
schedule reproduces the logged outcome for **100.0%** of leads (the fidelity
gate).

The one unobserved region: a lead that sold at tier t never revealed tiers
t+1..6, so raised floors need imputed deeper-tier demand — hot-deck sampled
from logged bid pairs at that tier within the same FICO band x recency bucket
(selection-biased downward: leads that reached deep tiers failed shallow
ones; raised-floor revenue estimates are therefore conservative). Lowered
floors need no imputation.

**Search.** Global-multiplier sweep for the response curve; coordinate
descent on per-tier multipliers (two passes, grid 0.2–1.6, bounded below at
20% of deployed — near-zero reserves make single-bidder sales clear near
zero under second-price rules).

**Result.**

| Tier | Deployed floor | Multiplier | Recommended |
| --- | --- | --- | --- |
| 1 | $187.11 | x1.20 | $224.53 |
| 2 | $92.50 | x0.70 | $64.75 |
| 3 | $45.73 | x0.45 | $20.58 |
| 4 | $22.61 | x0.30 | $6.78 |
| 5 | $11.18 | x0.20 | $2.24 |
| 6 | $5.52 | x0.20 | $1.10 |

Expected lift **+2.02%** revenue per lead ($87.18 → $88.94; 95% lead-bootstrap
CI +1.96%..+2.08%; imputation-seed spread ±0.01pp). Sell-through rises 49.1%
→ 75.8% (deep-tier reserves currently destroy many small sales they don't
protect). Notably the *global* sweep peaks at exactly x1.0 — the deployed
level is right; the gain is all reshaping: a stiffer tier-1 reserve plus
much cheaper deep tiers.

**Validation by re-running the engine (Phase 6 exit; method record D18,
ratified 2026-09-02).** The replay's one imputed region is removed entirely
by regenerating five worlds (seeds 42-46, scale 0.2, about 478k leads each)
and running the waterfall itself under both schedules with common random
numbers. Realized lift **+2.98%** (five-seed range +2.88% to +3.15%,
standard deviation 0.10pp) against the replay's +2.02% — higher, in the
direction the downward-biased hot-deck imputation predicts. Sell-through
49.2% to 76.5%. Bid-shading stress test (buyers give back a share *s* of
the tier-1 floor increase): +2.23% at *s* = 0.05, +1.43% at 0.10, zero at
about **0.19**, -12.6% if the increase is absorbed entirely. That
break-even is the number the staged rollout is built around.
`models/validate_floors.py` -> `models/out/m3_validation.json`,
`models/out/m3_validation.html`.

**Honest notes.**

- Bids-invariant-to-floors is true in this engine by construction; in a real
  marketplace buyers shade bids against reserves, so this replay would be an
  upper bound on knowable counterfactuals and the recommendation would gate
  through an A/B test (the design's model 6 / Phase 6 territory).
- Deep-tier multipliers sit at the 0.2 bound; the revenue curve is nearly
  flat below it, so the bound costs little and keeps prices operationally
  sane.
- Bids-invariant-to-floors holds in the engine and in the validation above,
  so the shading stress test bounds rather than measures what real buyers
  would do; the rollout's randomized arm is what measures it.

**Decision this informs.** The reserve schedule -- the marketplace's
primary revenue lever, since tier 1 carries 83% of revenue and more than
half of its sales clear at the floor. The recommendation is to keep the
overall level and reshape: tier 1 to 1.2x, deep tiers to the 0.2x bound,
staged (tier 1 to 1.1x and deep tiers to 0.5x first) behind lead-level
randomized multipliers so the effect is measured, not inferred. Expected
value at the logged volume is about $4.2M per year (+$1.76 on $87.18 per
lead x 2.4M leads; `analysis/dashboards/data/derived_figures.json`).

**What we would do next.** (1) Segment-level reserves (tier x FICO band)
using the model 2 landscape, where the replay thins out inside small strata
and the fitted landscape starts to earn its place. (2) The staged rollout
with lead-level randomized multipliers, which measures the realized lift
and the shading share *s* directly, and produces the logged propensities
off-policy evaluation would need. The C1 price-scale item is closed
(2026-09-02): the recommended tier-1 floor sits above the design's original
$120 anchor, the memo states the drift plainly, and the relative claims
(level right, shape wrong; break-even shading 0.19) do not depend on the
level.

**Reproduce.** `.venv/bin/python models/optimize_floors.py` →
`models/out/m3_metrics.json`, `models/out/m3_floor_optimization.html`.
