# Model card — Model 3: Reserve/floor optimization

*Phase 5, design Section 8. Built 2026-08-24 on the C19 world. Provenance: A.*

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

**Honest notes.**

- Bids-invariant-to-floors is true in this engine by construction; in a real
  marketplace buyers shade bids against reserves, so this replay would be an
  upper bound on knowable counterfactuals and the recommendation would gate
  through an A/B test (the design's model 6 / Phase 6 territory).
- Deep-tier multipliers sit at the 0.2 bound; the revenue curve is nearly
  flat below it, so the bound costs little and keeps prices operationally
  sane.
- Engine-loop validation (re-simulating at the recommended schedule) is the
  Phase 6 exit, deliberately not claimed here.

**Reproduce.** `.venv/bin/python models/optimize_floors.py` →
`models/out/m3_metrics.json`, `models/out/m3_floor_optimization.html`.
