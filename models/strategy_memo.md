# Optimization strategy memo

Status: **final, 2026-09-02.** The Phase 5 models it draws on were accepted (D11) and the Phase 6 validation method was ratified (D18), so the engine re-run below is the Phase 6 exit measurement — the design's "simulated EPL lift quantified with uncertainty bands" — rather than a provisional figure. Every number traces to `models/out/m*_metrics.json`, `models/out/m3_validation.json`, `models/out/experiment_power.json`, `analysis/dashboards/data/derived_figures.json`, or `er/scorecard.json`.
Audience: the simulated marketplace's executive team. Provenance: A (design Section 8 deliverable; Phase 6).

## 1. Recommendation in five lines

1. **Reshape the reserve schedule; do not move its level.** Raise the tier-1 floor from $187.11 to $224.53 (x1.20) and cut tiers 2-6 to $64.75 / $20.58 / $6.78 / $2.24 / $1.10 (x0.70 / 0.45 / 0.30 / 0.20 / 0.20). Expected revenue per lead +2.02% in counterfactual replay (95% CI +1.96% to +2.08%), about **$4.2M a year** at the logged 2.4M leads; the engine re-run puts it at +2.98% (five-seed range +2.88% to +3.15%). Ship it staged, behind lead-level randomized multipliers, because the gain disappears if buyers give back about a fifth of the tier-1 increase.
2. **Message engagement segment 5 only.** The nurture effect is concentrated there; the other four segments' uplift is indistinguishable from zero. Revenue upside about $250k a year; about 1.77M messages a year avoided.
3. **Hold display spend pending a maturity-adjusted read; do not reallocate on average ROAS alone.** Display is below break-even (0.94x, a $0.67M net loss on $11.6M), but cohort ROAS is right-censored and there is no spend variation to estimate a marginal return.
4. **Treat the $12.0M of same-buyer duplicate revenue as a policy question, not a loss to recover.** Buyers already discount recents to 0.52-0.75x of fresh prices; what remains is the marketplace's to price or suppress, and each option needs a buyer-response experiment.
5. **Run the floor test first.** Its expected value is two orders of magnitude larger than the send-policy test's.

## 2. The business in numbers

- $209.2M of auction revenue on 2,399,526 applications; sell-through 49.1%; $87.18 per application.
- **Tier 1 is 83% of revenue.** It sells 28.4% of the leads offered at a mean $254.87 against a $187.11 floor, and its median clearing price equals the floor in every FICO band: more than half of tier-1 sales are floor-pinned, so the floor is the price for most of the base. Tiers 3-6 together are 3.8% of revenue.
- **Repeat applicants dominate volume.** 2.40M lead ids are 635,579 people; 68.8% of applications are repeats; the 20.2% of consumers with five or more applications produce 53.4% of revenue; the repeat share of monthly applications climbs from 23% in month 1 to 86% in month 12.
- **Paid acquisition returns 1.94x on $53.8M**, from 0.94x (display) to 3.06x (affiliate); cost per sold lead $57 (affiliate) to $183 (display).
- These numbers exist because 95.3% of auction events are joinable to a resolved consumer (0% before identity resolution; link F1 0.879, dedupe F1 0.873 against hidden ground truth). Every figure below inherits that linkage's error, which attenuates effects rather than fabricating them.

## 3. Floor policy

**Why the level is right and the shape is wrong.** A global sweep that scales every tier's floor together peaks exactly at the deployed level (x1.0: $87.18 per lead; x0.8: $85.54; x1.2: $86.35; x2.0: $75.74). Uniform tightening or loosening loses money. Per-tier search finds the gain in reshaping: a stiffer tier-1 reserve, where more than half of sales already clear at the floor, and much cheaper deep tiers, where the current reserves destroy small sales they do not protect. Sell-through rises from 49.1% to 75.8% in replay.

**How the estimate was made, and its two uncertainties.**

- *Counterfactual replay.* The lake logs every bid including sub-reserve bids, so each logged waterfall is replayed under the candidate schedule; replay at the deployed schedule reproduces the logged outcome for 100.0% of leads. Where a raised floor pushes a lead to tiers it never reached, demand is hot-deck imputed from leads that did, a downward-biased draw, so the replay is conservative. Sampling uncertainty (500-draw lead bootstrap): +1.96% to +2.08%. Imputation-seed spread: 0.01pp.
- *Engine re-run (the Phase 6 exit measurement, method ratified as D18).* Five fresh worlds (seeds 42-46, scale 0.2, about 478k leads each), the waterfall run under both schedules with common random numbers, no imputation. Realized lift **+2.98%** (standard deviation across seeds 0.10pp; range +2.88% to +3.15%), sell-through 49.2% to 76.5%. The replay understated the gain, in the direction its bias predicted.
- *Bid shading, the uncertainty that matters.* Bids are invariant to reserves in this engine; real buyers may give back part of a floor increase. If buyers at tier 1 lower their valuations by a share *s* of the 20% increase, the lift is +2.23% at *s* = 0.05, +1.43% at 0.10, **zero at about 0.19**, and -12.6% if they absorb it entirely. The recommendation is therefore conditional on measuring *s*, which the rollout below does.

**The price-scale caveat (C1, closed 2026-09-02).** The simulated price scale was anchored at a $120 tier-1 mean; the calibrated world clears tier 1 at $255 and this memo recommends a $224.53 floor, further from the anchor. The item was closed on the first of those readings: the scale's job is to carry realistic shapes and censoring structure, not to match any real market, and the relative claims in this memo (the level is right and the shape is wrong; break-even shading of about 19%; the ROAS ordering) do not depend on the price level. The drift is stated plainly here rather than hidden, so a reader can discount the dollar figures accordingly.

## 4. Risk register

| Risk | Mechanism | Signal to watch | Mitigation |
| --- | --- | --- | --- |
| Buyer bid shading | Tier-1 buyers give back part of the floor increase | Realized lift in the randomized arm falls below +1.4% (the *s* = 0.10 level) | Stage 1 at x1.10; measure *s*; stop if break-even is approached |
| Deep-tier volume shock | Sell-through 49% to 76%: deep-tier sales more than double at $1-7 prices | Buyer-side dedupe load, return rates, ops tickets | Stage deep tiers at x0.5 before x0.2; the revenue curve is nearly flat below x0.5, so little is lost by waiting |
| Tier-1 buyer attrition | Fixed five-buyer panels; revenue HHI about 3,120 | Participation rate per buyer at tier 1 | Guardrail on tier-1 sell-through (28.4% today) and per-buyer bid rate |
| Optimum drifts with the repeat mix | Repeat share rises through the year; recents are suppressed by buyers | Monthly recency mix; lift by recency bucket | Re-run the search quarterly; segment-level (tier x FICO x recency) schedule next |
| Linkage error | Consumer-entity features carry F1-0.88 linkage noise | Attenuated, not inflated, effects | Report operating-point sensitivity with every per-consumer figure |
| Model transfer | Model 1's near-separable AUC is a property of the world | — | Only the calibration and leakage discipline are claimed as transferable |

## 5. Rollout and gating

1. **Randomize from day one.** Assign each lead a floor-multiplier arm (deployed; stage-1 schedule) at random within a band. This measures the lift directly, estimates *s*, and creates the logged propensities that make off-policy evaluation of later schedules possible (the log today is deterministic, so no off-policy estimate is available).
2. **Stage 1 (two to four weeks):** tier 1 x1.10, tiers 2-6 x0.70 / 0.50 / 0.50 / 0.50 / 0.50. Guardrails: tier-1 sell-through, per-buyer participation, deep-tier return rate. Decision rule: proceed if the measured lift is at or above +1.4% (consistent with *s* at or below 0.10).
3. **Stage 2:** the recommended schedule (tier 1 x1.20, deep tiers to x0.20). Same guardrails; re-estimate *s* at the higher floor.
4. **Quarterly:** re-run the search on the latest quarter; move to a segment-level schedule once the model 2 landscape is validated in production.

## 6. Send policy

- **Evidence.** Intention-to-treat holdout, 729,856 treated / 128,797 holdout. Pooled application lift +0.109pp (95% CI -0.105pp to +0.324pp) against an injected +0.115pp: underpowered for the level (about 6.1M contacts needed for 80% power; minimum detectable effect 0.307pp). Two reads agree on the ranking: segment 5 first (naive +0.37pp; uplift model +0.46pp; injected +0.52pp), and ranking contacts by predicted application rate scores *below random*, because high-intent contacts apply anyway.
- **Policy.** Message segment 5; stop messaging segments 1-4. Value at the injected effect: about 866 incremental applicants a year, about $249,519 of auction revenue; about 1,766,645 messages a year avoided across 588,545 contacts. Per-message send cost is not in any silo; marketing supplies it and the avoided cost prices itself.
- **Follow-up test.** Sized for the segment-5 effect: 134,179 contacts at 50/50 (about ten months of segment-5 acquisition) or 266,126 at the current 85/15 (about nineteen months). The holdout is nearly free in this program, so 50/50 is recommended. Guardrail: segments 1-4 unmessaged for a quarter; resume if their application rate falls by more than that sample's detectable effect.

## 7. Channel spend

- **What is known.** Average ROAS by acquisition cohort: affiliate 3.06x (CAC $60 per contact), paid social 2.80x ($61), paid search 1.84x ($124; the largest line at $27.6M), display 0.94x ($157). Owned channels earn about $288 per contact; paid channels $148-$229.
- **Why it is not yet a budget decision.** (1) Cohort ROAS is right-censored: the youngest cohorts have had months, not a year, to re-apply (affiliate reads 3.58x for the first cohort and 0.33x for the last). (2) There is no spend variation, so the marginal return of the next dollar is unidentified; cutting display saves $11.6M and forgoes $10.9M only if the average equals the margin.
- **What would make it one.** A cohort revenue-maturation curve to project 12-month ROAS for young cohorts with an interval, and a geo or budget-split test on display and affiliate to estimate marginal ROAS. Decision rule to pre-register: cut display if its projected 12-month ROAS is below 1.0x with 80% confidence; shift to affiliate and paid social up to their capacity ceiling, which is unknown and must be stated as such.

## 8. Duplicate consumers

- **Exposure.** $12.0M (5.7% of revenue, 63,579 leads) paid by a buyer for a consumer it had bought within 30 days; $48.3M (23.1%, 345,531 leads) re-sold to any buyer within 30 days. Window sensitivity: $2.4M / $13.8M at 7 days; $33.2M / $97.2M at 90 days. These are the residual after buyers' own suppression and discounting (recents clear at 0.52-0.75x and win at 0.46-0.70x of fresh rates).
- **Options.** (a) Marketplace-side suppression of same-buyer repeats within 30 days: forgo up to $12.0M, protect buyer trust and the recent-price ratio. (b) A freshness guarantee priced into the tier-1 floor. (c) Recency-aware reserves: extend the floor search to recency buckets, which the replay machinery already stratifies on.
- **What decides it.** Buyer response to marketplace-side suppression is not in the data. Randomize suppression by buyer or by week and measure win rate and price on the buyer's fresh leads. Until then, this is an exposure number, not a loss.

## 9. What to test first, and in what order

1. Floor stage 1 with lead-level randomization (Section 5): largest expected value; also creates the log that future policy work needs.
2. Segment-5-only sends at 50/50 (Section 6): near-zero cost, about ten months to a read.
3. Display budget split (Section 7): decides the largest paid line after paid search.

## 10. Appendix

- Model cards: `models/cards/model_1_sale_propensity.md` through `model_4_uplift.md`; static reports `models/out/m1-m4_*.html`; validation `models/out/m3_validation.html`.
- The specification test: a Type-I Tobit fitted on the same split stretches to sigma 1.43 and prices unsold leads at a median $0.18 against $32.25 of logged sub-reserve demand; censoring here is participation-driven, so the survival landscape is used.
- Problem framing: `docs/problem_framing.md`; experiment read-out: `docs/experiment_readout.md`.
- Data lineage in one paragraph: three silos (S3 Parquet auction lake, Postgres CRM, BigQuery marketing exports) resolved to one consumer identity by probabilistic linkage where identity is fuzzy and deterministic linkage where an exact key exists, at stated operating points, scored against a hidden crosswalk; wide marts at event, lead, and contact grain; models trained on the marts only.
