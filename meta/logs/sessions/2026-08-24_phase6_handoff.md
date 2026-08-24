# Phase 5 → Phase 6 Handoff

Written 2026-08-24 at the end of the Phase 5 build session. Session-start context for Phase 6 (optimization and strategy memo). Durable state lives in the canonical docs (CLAUDE.md read-first list); this note is the delta a fresh session needs.
Provenance: A

## Decisions requested (INT-015 form)

**D11 — Phase 5 models 1–4** (`meta/logs/decisions.md`, full record there).

1. *What was decided and why:* four models trained on the D10 marts under one auction-time feature contract and one temporal split (train months 1–8 / valid 9–10 / test 11–12). Model 1: calibrated LightGBM sale propensity + conditional tier head (test AUC 0.994 vs 0.633 baseline, ECE 0.0017). Model 2: the design's survival framing — tier-ladder hazard x price-given-sale — with the textbook Tobit fitted and kept as a documented specification test (it fails informatively: censoring here is participation-driven, so its latent collapses to $0.18 median against $32 of logged sub-reserve demand). EV-revenue rank corr 0.859 vs 0.269 baseline. Model 3: exact counterfactual replay of logged bids (100.0% fidelity at the deployed schedule) + hot-deck imputation for raised floors; recommends tier-1 x1.2 and deep tiers cut to a declared 20% bound, +2.02% revenue/lead (CI +1.96..+2.08%), with the striking side-finding that a *global* floor sweep peaks exactly at the deployed level. Model 4: cross-fitted T-learner, logistic per arm, covariates = the action space (segment + channel); recovers the injected concentration (top segment +0.46pp vs +0.52pp injected; AUUC 68% of the oracle ceiling; response-model targeting is worse than random). Evaluation ships as scripts + static reports, amending the design's "evaluation notebooks" wording (design v1.7).
2. *The consequences to weigh:* (a) model 4's covariate set excludes state and acquisition month for stated power/imbalance reasons — a reviewer could read that as tuning toward the injected answer; the card argues the exclusions from design principles (action space; imbalance-by-construction) and records the failure modes each prevents. (b) Model 3's deep-tier recommendation more than doubles deep-tier sales volume (sell-through 49% → 76%) — operationally loud; the 20% lower bound is a declared constraint, adjustable in one place (`TIER_GRID`). (c) The Tobit stays in the repo as a deliberately-failed specification, which is a narrative choice about what the portfolio shows.
3. *The ask:* accept / amend / reject. Cheap amendments: split boundaries (`models/common.py`), the m3 grid bound, m4 covariates, any card wording. Rejecting the survival framing for a pure Tobit would fail the beats-baselines exit on current evidence.
4. *Consequences of accepting:* Phase 5 closes (all four models beat baselines; calibration + uplift curves documented in `models/out/`; logs current; graph validates; 58 tests green). Phase 6 starts from the D11 artifacts.
5. *Recommendation:* accept. Every methodological choice is verified against the failure it prevents, and the two honest failures (Tobit specification, tie-breaking artifact) are documented as findings, which is the stronger portfolio story.

**D10 — Phase 4 marts and dashboards** remains pending from the previous session; the full INT-015 ask is in the Phase 5 handoff (`2026-08-20_phase5_handoff.md`) and is unchanged by this session. Phase 4 closes on it.

## Where Phase 5 ended

- `models/`: `common.py` (feature contract + temporal split), `tobit.py`, four training scripts, `cards/` (four one-page model cards), `out/` (metrics JSON + four static evaluation pages in the dashboard look; boosters git-ignored). `tests/test_models.py` (10 gates: Tobit gradients vs numerical differentiation, replay mechanics, uplift-curve tie-breaking, leakage disjointness, C19 bucket agreement).
- Rebuild all four: the four commands in `models/README.md` (~25 min total, warehouse-local, no cloud).
- En-route: LightGBM needed a user-local arm64 OpenMP runtime (INT-016, machine state only); uplift-curve stable-sort tie-breaking fabricated an inflated oracle Qini until seeded shuffling (D11f, fixed and tested).

## What Phase 6 is

Design Section 8 (models 5–6, both droppable) and Section 9 Phase 6 row: floor-price simulation, bandit experiment, and the 3-page optimization strategy memo. Exit: simulated EPL lift quantified with uncertainty bands. The natural spine: validate model 3's recommended schedule by re-running the engine at those floors (one seeded command; compare realized EPL against the replay's +2.02%), then the memo; the Thompson-sampling bandit (model 5) rides the same simulator loop if kept.

## Watch items carried forward

1. **C1 price-scale watch item stands** (tier-1 mean ~$255 vs the $120 anchor; eased by C19, not resolved). Model 3 recommends *raising* the tier-1 floor, which moves further from the anchor — flag this in the Phase 6 memo; human decision before anything publishes.
2. **Model 3's bid-invariance assumption** is true in the engine by construction but would not survive contact with real buyers (bid shading against reserves); the memo should carry this as the rollout-gating argument (A/B first), which is also the design's model 6 hook.
3. **Uplift experiment power**: unchanged (D10); any Phase 6 revenue claims for nurture targeting should stay ranking-based, not level-based.
4. **The m2 hazard head and model 1 share signal** (P(sold) = 1 - survival product); their agreement is an available consistency check if Phase 6 needs one.

## Standing process rules most likely to bite

INT-015 (decision requests in full form), INT-010 (no AI-attribution trailers; `Provenance:` only), C13b/P-007 (synthetic data, never the library name), the redaction rule, and the session protocol (state phase and governing sections at start; candidate records at end; graph diff in the same commit as structural change).
