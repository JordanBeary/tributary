
# Decision Log (ADR)

Covers both tracks. Series: **A** (architecture and workflow), **B** (naming and configuration), **C** (calibration assumptions), **D** (post-reframing decisions), **Q** (open questions). A/B/C entries were migrated 2026-08-03 from `project_guide.md` Section 5 with their original ids preserved; they predate the id/citation discipline and are marked `[backfill]`.

When a decision supersedes another, both entries say so.

---

## A-series — Architecture and workflow `[backfill, Phase 0]`

| # | Decision | Rationale |
| --- | --- | --- |
| A1 | **Simulator reads only fitted parameter artifacts** (`simulation/params/*.json`), never the raw public datasets | Keeps the simulator runnable without ~35 GB of downloads; makes calibration a one-time, versioned, reviewable step. The profiling notebooks are the only code that touches raw data. |
| A2 | Stage contracts (inputs/outputs/formats per stage) frozen in `simulation/stages.py` docstrings before implementation | Lets silo loaders, dbt sources, and the ER pipeline be built in parallel against stable interfaces. |
| A3 | Free-tier hybrid architecture (design Section 4.1) over the all-AWS variant (Section 4.2) | The design recommends it; nothing the author said suggested wanting the pure-AWS story. Revisit only if target roles are AWS-specific. |
| A4 | `us-east-1` for AWS; `US` multi-region for BigQuery; Neon in us-east-2 | Cheapest/default regions; cross-region latency is irrelevant at this scale. |
| A5 | Python 3.12 via uv-managed standalone interpreter; project venv at `.venv/` | Machine's system Pythons (3.7/3.8) predate every dependency. See `CLAUDE.md` machine quirks. |
| A6 | Incremental commit-and-push to `main` (no PR flow) | Solo project; review theater adds friction without value. Can switch to branches to demo PR discipline (see Q4). |

## B-series — Naming and configuration `[backfill, Phase 0]`

| # | Decision | Value | Status |
| --- | --- | --- | --- |
| B1 | S3 bucket name | `clx-auction-lake-jb` | **Superseded by D3** (fictional-name reversal, INT-001) |
| B2 | BigQuery dataset | `clx_marketing` | **Superseded by D3** |
| B3 | Budget alert email | The author's alert address (see AWS Budgets console) | Active |
| B4 | Budget amount/thresholds | $10/month, alerts at 50/80/100% actual spend, both clouds | Active |
| B5 | IAM daily-work user | `tributary`: S3 Get/Put/Delete/List on the one bucket only | Active (policy re-scoped to the D3 bucket) |

## C-series — Calibration assumptions `[backfill, Phase 0]`

Proposals to be validated or revised in the Phase 1 profiling notebooks.

| # | Assumption | Value | Status |
| --- | --- | --- | --- |
| C1 | Tier price scale: iPinYou provides price *shapes*; absolute lead prices are invented | tier-6 floor ~ $2 ... tier-1 clearing ~ $120 | Declared design assumption — sanity-check against public lead-gen pricing anecdotes before publishing. **Watch item (2026-08-10, C16):** full-scale mean clearing price on sold leads is $198 — the C11 elasticity's right tail pulls the mean above the anchor |
| C2 | Overall sell-through target | ~60%, monotone declining by tier; censored (unsold) fraction 35–45% | Tunable dial |
| C3 | Applications per consumer | P(1)=0.75, P(2)=0.18, P(3)=0.07 → ~1.6 leads/consumer | **Superseded by C14** — the stated mix has mean 1.32 and never met its own 1.6× target |
| C4 | Marginal-fit QA gates | KS < 0.05 numeric; ±1pp categorical; copula max corr error < 0.1 | Agent-proposed thresholds; tighten/loosen with evidence |
| C5 | Message funnel | send→open 35%, open→click 8%; Poisson(λ≈3) messages/contact, cap 10 | Industry-plausible inventions — Criteo has no email funnel |
| C6 | Uplift | ~85/15 treated/control; +0.1–0.3pp absolute; top-decile ≈ 3–5× average uplift | **Measured 2026-08-04** (`03_criteo`): ratio 0.850 and ATE +0.115pp confirm the declared values, but the top-decile/average ratio is **7.04** — heterogeneity is far more concentrated than the declared 3–5× (the top quintile carries ~4.5× the average; the bottom four are near zero). The simulator uses the measured quintile multipliers from `uplift_params.json`. |
| C7 | Duplicate corruption mix | nickname 40% / email typo 30% / new phone 20% / all three 10% | Invented; tune until ER F1 lands in 0.85–0.95 (design's own target band) |
| C8 | LendingClub rejected file used only for tail-widening + acceptance model | — | Its schema is far narrower than the accepted file |

### C-series additions (Phase 1)

| # | Assumption | Value | Status |
| --- | --- | --- | --- |
| C9 | iPinYou CTR-price elasticity: **valid estimate, non-transferable** to the lead marketplace (expanded record below) | Empirical −0.149 recorded in the artifact as a correct in-domain estimate; simulator uses a **declared elasticity of +1.0** log-price units per unit `q` — a full parameter override, sign and level | **Ratified 2026-08-07** with human reframing (INT-013); end-to-end QA gate added |
| C10 | Winning-price distribution model: iPinYou's advertiser-standardized log prices deviate from lognormal by up to 24% pooled / 40% per advertiser at deciles 1–9 — the spec's original "lognormal + ±10% Q-Q gate" pair is unsatisfiable with its own model | Valuation noise drawn from the **empirical standardized log-price shape** (1000-point inverse-CDF table in the artifact, house style per A1/01); per-advertiser (mu, sigma) retained for location/scale; lognormal-adequacy measurements kept as a documented finding | **Ratified 2026-08-12**, accepted as proposed (all downstream calibration — C11, C12, the waterfall engine and its gates — was built on the empirical shape) |

#### C9 — expanded record: iPinYou CTR-price elasticity, valid estimate, non-transferable

*Ratified 2026-08-07. Human-drafted in a review session (as `D-007`, merged here with ids mapped); category: declared-assumption override; initiated by human decision, agent-assisted analysis. Cross-ref: INT-013 (the framing of this finding was itself corrected).*

***Status (2026-08-07, same day): parameter values superseded by C11.*** *The +1.0 declared elasticity failed this record's own end-to-end gate on first verification. This record is preserved unedited below — the falsification is part of the project's story (INT-014): the override-then-verify pattern worked exactly as designed, against its own author.*

**Finding.** The calibration spec (Section 2, valuation-quality coupling) sources the elasticity of buyer valuation w.r.t. lead quality `q` from a regression of log winning price on CTR decile in iPinYou. The fitted slope is **−0.149**. This estimate is *correct in-domain*: in display RTB, high-CTR inventory skews toward cheap remnant/performance placements while premium brand inventory carries high CPMs with unremarkable CTR, so price and the CTR proxy genuinely anticorrelate in that market.

**Why it does not transfer.** The regression answers "how does price relate to a CTR-based quality proxy in display RTB?"; the simulator needs "how does buyer valuation relate to lead quality in a loan-lead marketplace?" The price-quality mechanism differs structurally between the two markets (remnant-inventory dynamics vs. underwriting economics), flipping the sign. The target market requires positive coupling: the waterfall's tier ordering, the adverse-selection cascade, and the downstream ML workstream (censored price model, floor optimization, sale propensity) all presuppose it. Importing the fitted slope would produce an inverted economy in which routing the best leads to the cheapest tier maximizes revenue.

**Resolution.** Per the spec's rule that every parameter is either a fitted distribution or a declared assumption:

- The empirical −0.149 is executed and **recorded in `simulation/params/auction_landscape.json`** as a correct in-domain estimate — not suppressed, not labeled anomalous.
- The simulator **uses a declared elasticity of +1.0** log-price units per unit `q` (q: 0 to 1 multiplies expected valuation by e, roughly 2.7x). This is a full parameter override — sign and level — documented as a design assumption, same pattern as the price-level rescaling in Section 2 (iPinYou contributes distributional shape; declared assumptions supply level/sign where the source market structurally diverges from the target).

**Follow-on QA gate.** Section 2 gates did not previously validate this parameter end-to-end. Added: Spearman correlation between `q` and realized clearing price on sold leads must exceed 0.3 in simulated output, so the declared elasticity is verified rather than trusted.

**Artifacts touched.** `docs/calibration_spec.md` Section 2 (row rewritten, gate added, v0.5); `analysis/profiling/02_ipinyou.ipynb` (records both values with this rationale; gate implemented).

**Follow-up note (2026-08-07).** The gate did its job immediately: on first verification the current calibration **fails it** (Spearman ~0.00). Diagnosis: with EL=+1.0 and the fitted q distribution (mean 0.787, sd 0.164), quality's effect on clearing decisions is ~0.18 standard deviations of the valuation noise — tier assignment is decided by participation luck, mean q per tier is flat, and floor-pinned prices therefore carry no q signal. Neither raising elasticity alone (EL=5 → 0.265) nor q-dependent participation alone (0.09) passes. Resolved by **C11**.

### C11 — Quality-price transmission repaired: rank-q, elasticity 3.0, within-vertical sigma

*2026-08-07. Category: declared-assumption revision + q-scale repair. Initiated by the C9 gate falsification (INT-013/INT-014); component selection by human decision, verification by agent harness. Supersedes C9's parameter values; C9's transferability rationale stands.*

**Finding (from the falsification diagnosis).** Three compounding causes kept lead quality out of realized prices: (1) the Section 1 quality score was nominally in [0,1] but practically squashed into 0.6–1.0 (mean 0.787, sd 0.164) — the logistic rescaling wasted the range; (2) the declared elasticity (+1.0) was too small relative to valuation noise (signal ratio ~0.18); (3) the pooled sigma (0.912) conflates between-vertical dispersion with within-auction dispersion, overstating the noise each tier's buyers exhibit.

**Decision — the triple:**

1. **`q` is redefined as the within-cohort percentile rank** of the Section 1 quality score (ordering preserved exactly; sd 0.164 → 0.289; a repair, not a tuning trick — elasticity semantics become log-price units per percentile of quality).
2. **Declared elasticity = 3.0** on rank-q. Plausibility: the p10–p90 quality spread implies e^(3×0.8) ≈ 11x in valuation, comfortably inside the design's ~60x tier-6-floor-to-tier-1-clearing price geography.
3. **Per-tier valuation noise uses the within-vertical sigma** — the median of per-advertiser sigmas, **0.860** (range 0.83–1.11) — with the pooled 0.912 recorded alongside it in the artifact for auditability.

**Verification (harness, all Section 2 gates jointly, floors re-bisected to the 60% target).** Censored 0.401; per-tier sell rates monotone (0.329 → 0.030); noise-shape round-trip max deviation 0.016; **Spearman(q, price) on sold = 0.348** (> 0.3). Diagnostics (reported, not gated): mean-q-by-tier now descends **0.72 → 0.54** — the adverse-selection cascade exists where it previously did not; floor-pinned sale share **0.768**, below the 85% flag but retained as a Model-2 watch item.

**Prediction outcome, recorded honestly.** The human's harness-anchored prediction was that the sigma reduction would be load-bearing (ratio ≥ 1.1 needed, sigma ≤ 0.75). It was not: rank-q + EL=3 passes at the pooled sigma (0.348), because the rank transform restored *tier sorting* — a mechanism the EL=5-on-squashed-q anchor could not exhibit. The within-vertical sigma is adopted on its independent principled ground (and it improves pinning and shape fidelity), at its fitted value 0.860 rather than a forced 0.75.

**Gate restatement owned by this decision.** The C10 shape gate now applies to the valuation **noise component** (the empirical shape table round-trip); with strong quality coupling the *marginal* valuation distribution legitimately widens, and quality transmission is tested by its own gate. Separation of concerns: C10 verifies the noise model, C9/C11 verifies the coupling.

**Artifacts touched.** `docs/calibration_spec.md` v0.6 (Section 1 q-scale note, Section 2 sigma and elasticity rows, gates restated, diagnostics added); `analysis/profiling/02_ipinyou.ipynb` rebuilt and re-executed; `simulation/params/auction_landscape.json` regenerated with both sigmas, the q-scale definition, and elasticity 3.0.

### C12 — Cherry-picking participation: quality-dependent bid odds (kappa = 2.0)

*2026-08-07. Category: realism mechanism, layered after the C11 repair per the human's standing direction ("it can't carry the gate but it's the mechanism real marketplaces actually exhibit"). Agent-selected strength from a gate-verified dose-response grid; floors recalibrated with the mechanism active.*

**Mechanism.** Real buyers see quality signals and choose what to bid on. Each seated buyer's participation odds shift with lead quality: logit(p_seat) + kappa (q − 0.5). At kappa = 2.0 the odds swing is e^(±1) ≈ 2.7x across the quality range — substantial selection without the aggressive end of the grid.

**Dose-response (harness, floors re-bisected per kappa, all gates passing at every point):**

| kappa | Spearman(q, price) | floor-pinned share | mean bids on sold | mean-q tier 1 → 6 |
| --- | --- | --- | --- | --- |
| 0.0 | 0.348 | 0.768 | 1.69 | 0.72 → 0.54 |
| 1.0 | 0.440 | 0.733 | 1.75 | 0.73 → 0.52 |
| **2.0** | **0.513** | **0.696** | **1.83** | **0.74 → 0.50** |
| 3.0 | 0.568 | 0.661 | 1.90 | 0.74 → 0.49 |

**Selection rationale.** kappa = 2.0 takes the middle of the verified range: it materially eases the Model-2 floor-pinning watch item (0.768 → 0.696) and steepens the adverse-selection cascade, while keeping the participation story defensible (a 2.7x odds swing, not an order of magnitude). The floor calibration barely moves (multiplier 1.75 → 1.73), confirming the mechanism reshapes *who* sells rather than *how much* sells.

**Engineering consequence.** The mechanism ships in the artifact (`participation.cherry_picking`) and is consumed by the production engine (`simulation/auction.py`); `run_waterfall` in `simulation/stages.py` is now implemented against it, and `tests/test_waterfall.py` asserts the Section 2 gates are reproduced from the artifact alone — the notebook's stated exit condition for the simulator.

### C13 — Consumer engine interpretation choices (record grain, Faker sampling, derived FICO band)

*2026-08-07. Category: engine semantics for `generate_consumers`, resolved while implementing the frozen stage contract. Proposed by the agent; **ratified same day (P-007)** — (a) and (c) as proposed, (b) with a terminology amendment. Alternatives were real in each case; the artifact and gates were the tiebreakers.*

**(a) `n_consumers` counts records, duplicates included.** The stage emits exactly `cfg.n_consumers` rows, of which ~`duplicate_rate` are duplicate records of another row's person (`consumer_key` shared, credit profile copied verbatim, identity corrupted per C7). Alternative rejected: n base persons plus 8% extra rows, which would inflate every downstream volume past the design's Section 3.3 table (1.5M records × 1.6 apps = 2.4M leads holds exactly under the chosen reading). Duplicate sources are drawn with replacement, so some persons carry 3+ records — duplicate flooding is not pairwise-only. *Ratified with domain confirmation (P-007): person-to-lead ratios are 1:many in real small-loan marketplaces because borrowers return for more.*

**(b) Synthetic identity data: library as vocabulary, stage RNG as sampler.** Identity fields draw from frequency-weighted en_US name/street/city/domain vocabularies (and per-state zip ranges) through vectorized numpy sampling on the stage's seeded stream rather than per-row library calls. Rationale: single-seed determinism stays in the one RNG-stream family the pipeline already uses ([seed, stage]), and full scale runs in ~11 s instead of minutes. Frequency-weighted names are load-bearing for ER difficulty: common names collide across distinct persons, as in real CRM data. *Ratification amendment (P-007): the narrative term for these attributes is **synthetic identity data** — the `faker` package remains the vocabulary source in the implementation, but documents and site copy describe the data, not the library.*

**(c) `fico_band` derived from `fico_mid`,** not drawn independently as in the notebook's QA sampler. Every row is internally coherent (band always contains the score), which downstream silos and models can rely on; the derived band mix stays within the ±1pp categorical gate with an order of magnitude to spare (max deviation 0.08pp at 500k draws). The notebook's independent draw was fine for gate-checking marginals but would have produced rows where band contradicts score.

**Engineering consequence.** The engine ships as `simulation/consumers.py` (artifact-only, per A1: consumes `lendingclub_marginals.json` and Faker vocabularies, never raw data); `generate_consumers` in `simulation/stages.py` is implemented against it, and `tests/test_consumers.py` reproduces the Section 1 QA gates from the artifact alone plus the duplicate-structure invariants the ER pipeline will be scored against. A per-record `consumer_record_id` (independent of `consumer_key`) keys leads to a specific identity record without leaking the hidden person key.

### C14 — Applications-per-consumer mix corrected to meet its own target

*2026-08-07. Category: arithmetic error in a backfilled assumption, found while implementing `generate_leads` against it. Supersedes C3's mix values; C3's target stands.*

**The error.** C3 declares P(1)=0.75, P(2)=0.18, P(3)=0.07 "tuned so total leads ≈ 1.6× consumers" — but that mix has expectation 0.75 + 0.36 + 0.21 = **1.32**, which at full scale yields ~1.98M leads against the design Section 3.3 target of 2.4M. The mix never satisfied its own stated goal; the feasibility arithmetic was one line and was never run (the INT-014 lesson, caught on paper this time).

**The correction.** P(1)=0.55, P(2)=0.30, P(3)=0.15 → mean exactly 1.60, so 1.5M records × 1.60 = 2.4M leads. The heavier reapplication tail is independently supported by the human's domain confirmation (P-007): person-to-lead is 1:many in real small-loan marketplaces because borrowers return for more. The 1–3 range from the frozen stage contract is unchanged.

### C15 — Marketing experiment structure: inverse construction, contact pool, ITT semantics

*2026-08-10. Category: engine semantics for `generate_marketing`, resolved while implementing the stage against already-fixed application outcomes. Proposed by the agent; **ratified 2026-08-12**, accepted as proposed (the C16 channel layer, human-directed, was built on this structure).*

**The structural problem.** The pipeline generates applications (leads) before marketing, so the stage cannot forward-simulate "treatment raises application probability" — outcomes already exist. And since every consumer record carries at least one lead, a pool of consumer contacts alone has conversion rate 1.0: no non-converters, no measurable uplift.

**(a) The nurture pool is built at the marketing stage and includes never-applier prospects.** Contact grain is unique email. Consumer records contribute their emails; fresh synthetic identities sized by `cfg.marketing_only_rate` (10% of contacts) contribute the non-converters the experiment requires. These prospects double as the design Section 2.3 "marketing contacts who never converted" orphan pathology — the dial is consumed here rather than at fracture, because the experiment needs them causally, not just cosmetically.

**(b) The causal effect is injected by exact inverse construction.** Within each engagement segment (quintiles, uniform), the number of converters assigned to treatment is solved so that treated-minus-holdout conversion equals the injected per-segment uplift: with T treated and C holdout among N contacts of whom A converted, T_a = round(T(A + tau·C)/N) treated converters gives conv_T − conv_C = tau exactly. A naive analyst recovers the artifact's ATE because it is arithmetically present. Feasibility (INT-014 discipline, run on paper this time): tau ≤ ATE × 4.52 ≈ 0.52pp shifts T_a by under 1% of either arm at any scale ≥ 0.01; rounding error is 0.5/min(arm) ≈ 0.01pp at test scale, an order of magnitude under the asserted tolerances. Full-scale verification: naive estimate +0.001153 vs injected +0.001152.

**(c) Intention-to-treat semantics.** Holdout contacts receive no messages (that is what a holdout is); ~5% of treated contacts draw zero messages from Poisson(3) and remain silently enrolled. The uplift attaches to assignment, not exposure — the standard ITT frame, and the one the Phase 4/5 analyses should use.

**(d) Second stage output.** The frozen contract named only `messages.parquet`, but the holdout flag must be visible somewhere for any analysis to exist — a real ESP would hold an audience export. The stage therefore writes `marketing_contacts.parquet` (email, holdout flag, engagement segment, marketing-only flag) alongside `messages.parquet`. No downstream consumer existed yet; the silo loaders (Phase 2) build against the amended contract.

**(e) Baseline conversion is structural, not Criteo's.** The artifact records Criteo's control conversion (0.19%), but this pool's baseline is ~90% by construction (converters dominate because only 10% of contacts are prospects). The Criteo calibration governs the *size* (ATE +0.115pp) and *spread* (segment multipliers, C6) of the effect — the baseline level is non-transferable, same epistemics as C9. Funnel heterogeneity uses mean-preserving segment factors 0.6–1.4 on the C5 rates (declared).

**Engineering consequence.** Engine in `simulation/marketing.py` (artifact-only per A1); `generate_marketing` implemented against it; `tests/test_marketing.py` asserts the Section 3 gate sharply (realized uplift within rounding of the ATE, overall and per segment) plus ITT, pre-submission timing, funnel, and orphan-share invariants. Full scale: 1.59M contacts, 4.05M messages (design target ~4M) in ~37 s.

### C16 — Acquisition channels: declared full-funnel economics (human-directed, P-008)

*2026-08-10. Category: marketing-silo realism extension, directed by the human (P-008): surface where the never-applier prospects come from via a natural channel mix with realistic per-channel conversion, KPIs, ROAS, and profitability — "PPC likely has low intent and conversion - organic has higher intent and conversion."*

**Structure.** Every contact enters the pool through one of seven acquisition channels; intent drives the whole funnel. The declared table (`ACQ_CHANNELS` in `simulation/marketing.py`):

| Channel | Mix | Contact→app target | Seg tier | q tilt | Click→contact | Unit cost |
| --- | --- | --- | --- | --- | --- | --- |
| direct | 8% | 0.97 | high | +0.30 | 0.35 | — |
| organic_search | 24% | 0.95 | high | +0.40 | 0.12 | — |
| referral | 8% | 0.93 | mid | +0.20 | 0.10 | — |
| paid_search | 26% | 0.90 | mid | 0.00 | 0.08 | $10.00 CPC |
| affiliate | 12% | 0.85 | low | −0.20 | — | $60.00 CPL |
| paid_social | 14% | 0.82 | low | −0.30 | 0.025 | $1.60 CPC |
| display | 8% | 0.72 | low | −0.40 | 0.005 | $0.80 CPC |

Conversion targets are rescaled by one factor so the pool-weighted rate matches the structural rate implied by the marketing-only dial (the *ladder* carries the realism; the level is structural, C15e). Converter/prospect channel mixes follow by Bayes — prospects concentrate in low-intent paid channels, which is exactly "where the never-appliers come from." Three correlation surfaces make the channels real end to end: engagement-segment tilt (high-intent channels open/click more, and respond more to nurture via the segment-uplift multipliers), lead-quality tilt among converters (organic delivers better leads, so revenue per contact varies by channel), and the declared unit economics feeding a monthly spend ledger (`channel_spend.parquet`: month × channel — contacts, visits, impressions, spend; visits back-derived so traffic always covers contacts).

**Realized full-scale economics** (seed 42, revenue joined through to auction clearing prices):

| Channel | Contacts | Spend | Revenue | CAC | ROAS |
| --- | --- | --- | --- | --- | --- |
| display | 127k | $20.9M | $16.3M | $164 | **0.78x** |
| paid_search | 414k | $48.8M | $74.7M | $118 | 1.53x |
| paid_social | 223k | $14.2M | $33.5M | $64 | 2.36x |
| affiliate | 190k | $11.4M | $30.8M | $60 | 2.69x |
| organic_search / referral / direct | 633k | $0 | $131M | $0 | owned |

The spread is the point: an unprofitable channel (display), a thin one (paid search at loan-keyword CPCs), healthy paid channels, and free owned traffic — the Phase 4 unified-ROAS dashboard has a real finding to surface, and it is only computable *after* silo unification (spend lives in marketing, revenue in the auction silo, joined through ER).

**En-route observation (C1 watch item).** Calibrating CPCs required measuring revenue: full-scale mean clearing price on sold leads is **$198**, above C1's "tier-1 clearing ≈ $120" anchor — the C11 elasticity's right tail pulls the mean. Logged on C1's status; revisit against public lead-pricing anecdotes before publishing, per C1's own caveat.

### C17 — Fracture semantics: payload, migration orphans, funded flag, hash isolation

*2026-08-10. Category: engine semantics for `fracture_into_silos`, resolved while implementing the Section 2.3 pathologies. Proposed by the agent; **ratified 2026-08-12 (P-009)**. Closes the five-stage engine.*

**(a) Auction bid_request rows carry the offer payload** (state, loan amount, purpose, FICO band). Real lead auctions transmit the lead to buyers, and the feasibility argument is structural: by design no key survives between the auction silo and the CRM, so without the payload the two silos would be unlinkable *in principle* and the north-star question (marketing ROI through auction revenue) unanswerable. With it, auction↔CRM linkage is fuzzy-but-feasible (state + amount + submission-time proximity), which is the intended difficulty. *Ratification added a second rationale (P-009): from an OLAP perspective, wide event-grain fact rows carrying consumer attributes row-wise are the analytically preferred shape — a preference that also informs the Phase 4 mart design.*

**(b) CRM ships as `leads.csv` + `schema.sql`** (DDL + copy instructions) rather than literal INSERT statements — 2.4M INSERTs would be a ~1 GB SQL file with no realism gain. The design's "CSV + SQL inserts" is read as data + loader.

**(c) Migration orphans come from the early window.** The ~5% orphan budget is drawn entirely from the first three months (~20% of that period's rows) — a migration that lost a slice of legacy records, not row-lottery noise — and the surviving CRM renumbers `lead_id` densely in submission order, so the id sequence gives no hint of the gap. Their auction events remain, orphaned.

**(d) `funded` = the artifact's conversions/clicks rate** (847/6329 ≈ 13.4%) drawn among sold leads, per the spec's "CVR-scaled funded flag" row — artifact-driven, not declared. CRM status is current-state ({funded, sold, closed_lost}) with a single overwritten `updated_at` (funded reports back 7–45 days after sale) — the entity-grain mutability pathology.

**(e) Both email hashes ship, raw email ships nowhere.** CRM carries sha256, marketing carries md5 — different algorithms, so the silos cannot be joined cryptographically; if either silo shipped raw email the CRM↔marketing join would be a trivial hash computation and ER would collapse to F1 ≈ 1.0. The fuzzy signal rides on names, phones, and zips instead — marketing contacts now retain phone/state/zip (plausible: signup forms + SMS reachability), because name-only matching at 1.4M contacts would be infeasible in the other direction. This name/phone/zip ladder plus the C7 corruptions is the ER difficulty dial.

**(f) Observed: DST makes naive CRM timestamps non-monotonic.** `lead_id` follows UTC submission order, but Pacific wall-clock inverts inside the November fall-back hour — the timezone pathology biting exactly as intended; asserted as a feature in `tests/test_fracture.py`.

**Watch items (Phase 2).** Full-scale CRM CSV is **561 MB against the design's ~0.4 GB Neon free-tier target** — the silo loader will need trimming (column subset or scale dial), per the design's own "free-tier limits take precedence" rule. Fracture peaks at ~22 GB RSS at scale 1.0 (whole-frame event transforms); acceptable on the dev machine, chunk by partition if it ever isn't. Marketing JSONL is 1.2 GB — comfortably inside BigQuery's free tier.

**Engineering consequence.** Engine in `simulation/fracture.py`; the full five-stage pipeline now runs from one seeded command — 1.8 s at scale 0.01, 2m28s at scale 1.0 — and `tests/test_fracture.py` asserts every pathology from the outside (key isolation, crosswalk completeness, orphan mechanics, CRM semantics and timezone round-trips, semantic drift, crosswalk confinement to `data/private/`). Phase 1's local exit criteria (design Section 9: reproducible 1%/100% runs from one command; distribution QA passing) are met.

### Interpretations of ambiguous design points `[backfill, Phase 0]`

- **"Conversion" semantics** are implemented as three genuinely different column definitions in the three silos (sold lead / funded loan / email click) — the semantic-drift pathology must be real enough to bite during unification, not just documented.
- **CRM mutability** (design Section 2.3 "mutable/overwritten"): the CRM export represents *current state* with overwritten fields, meaning the auction log and CRM can legitimately disagree — intended, not a bug.
- **Design doc's cost/pricing figures** (Section 5) are planning estimates from mid-2026; re-verify against provider pricing pages before publishing the cost write-up.
- **Volumes** (9M events, etc.) are targets at `--scale 1.0`, not exact requirements; free-tier limits take precedence over row counts.

## D-series — Post-reframing decisions

### D1 — Repository visibility: public, with git history rewrite

- **Date:** 2026-08-03 · **Decider:** human · **Resolves:** Q2; plan Section 8 item 2
- **Context:** The repo was public with the AWS account id and personal emails in committed history (INT-002). Options: (a) private until first publishable milestone (the plan's recommendation), (b) stay public and rewrite history to scrub the identifiers, (c) stay public as-is.
- **Decision:** (b) — stay public; rewrite history with replace-text filters and force-push. The git author email remains in commit metadata as the author's public git identity, by acceptance.
- **Consequence:** All commit hashes prior to the migration changed once. The redaction rule (`meta/conventions.md` Section 2) prevents recurrence.

### D2 — GCP project id: replaced

- **Date:** 2026-08-03 · **Decider:** human · **Resolves:** plan Section 8 item 1 (project-id sub-decision)
- **Context:** The project id carried the fictional name and is immutable. Options: replace the project (new project, billing re-link, budget, re-auth; nothing to migrate while empty) or accept-and-document.
- **Decision:** Replace now, while the dataset was empty. New project `tributary-jb`; billing linked; the existing account-wide $10 budget (50/80/100% thresholds) covers it without a new budget object; ADC quota project updated; old project deleted (30-day undelete window from 2026-08-03).

### D3 — Cloud resource names (supersedes B1, B2)

- **Date:** 2026-08-03 · **Decider:** human · **Resolves:** plan Section 8 item 1
- **Context:** Bucket and dataset carried the fictional name; both were empty, so recreation was cheap (the window the plan identified). Naming options: plan's suggestion (short dataset name, project provides context) versus prefixing everything.
- **Decision:** Plan's suggestion — S3 bucket `tributary-auction-lake-jb`, BigQuery dataset `marketing` (in project `tributary-jb`, per D2). Old bucket and dataset deleted after verification; IAM policy for the `tributary` user re-scoped to the new bucket (B5).

### D4 — iPinYou acquisition: Kaggle mirror, sampled days (resolves Q5)

- **Date:** 2026-08-03 · **Decider:** human (source) + agent (sampling detail) · **Resolves:** Q5
- **Context:** The academic mirror (data.computational-advertising.org) was unreachable; the human located the canonical `ipinyou.contest.dataset` tree mirrored on Kaggle (`lastsummer/ipinyou`, ~6.3 GB compressed). The calibration spec needs distribution shapes, not the full ~35 GB uncompressed corpus.
- **Decision:** Download from the Kaggle mirror, sampled per day: season 2 (`training2nd`) gets a weekend day plus two weekdays (20130608, 20130610, 20130612); season 3 (`training3rd`) gets its weekend plus three weekdays (20131019–20131023, whose per-day files are much smaller). All four record types (bid/imp/clk/conv) per sampled day, plus README/checksums/lookup tables. ~1.5 GB compressed total. Encoded in `scripts/download_datasets.sh` so the sample is reproducible.
- **Consequence:** If a profiling QA gate later shows the sample is unrepresentative (e.g., day-of-week price effects), widen the day list in the script — the fitting notebooks re-run unchanged.

### D5 — Silo deployment mechanics (Phase 2 load choices)

- **Date:** 2026-08-13 · **Decider:** agent (proposed); **ratified by the human 2026-08-14**
- **Context:** Loading the fracture outputs into the three clouds surfaced choices the design leaves open. All are load-layer decisions: `simulation/` outputs and their tests are untouched.
- **Decision:**
  - **(a) BigQuery timestamps load as `DATETIME`, not `TIMESTAMP`.** The marketing export carries naive US/Eastern wall-clock times (C17 timezone pathology). `TIMESTAMP` would stamp a UTC assumption onto them and silently "fix" the defect Phase 3 is supposed to confront; `DATETIME` stores the naive values as exported.
  - **(b) `channel_spend.visits`/`impressions` load as `FLOAT64`.** The export writes these counts as float-or-null (nullable-column artifact); BigQuery refuses `98105.0` into `INT64`. The export is loaded as-is rather than laundered; casting is staging's job (Phase 3).
  - **(c) `messages` ends deployed as `PARTITION BY DATE(sent_at)` `CLUSTER BY channel`,** rewritten post-load via create-new/drop/rename (BigQuery cannot `CREATE OR REPLACE` across partitioning specs). The unpartitioned-then-optimize sequence was deliberate: it produced the before/after bytes-scanned receipt (124,325,982 -> 11,430,092 bytes on the benchmark query, 10.9x; `silos/marketing_bq/benchmark_receipt.json`).
  - **(d) S3 receives the Hive tree as generated** (366 `event_date=` partitions, 1,098 objects, one idempotent `aws s3 sync`), verified byte-exact (1,226,209,268 bytes local and remote). The loader refuses to run if any crosswalk artifact is under its source tree.
  - **(e) A local-network quirk is fixed in the environment, not the loader.** This network deterministically kills single-request S3 PUTs of certain payloads (seven specific parquet files failed identically across runs while random same-size bytes passed; content-keyed, mechanism unidentified). Workaround: `~/.aws/config` `tributary` profile forces 1 MB multipart chunks + adaptive retries (max 10). Recorded in CLAUDE.md machine quirks; the loader stays portable.
- **Consequence:** Phase 3 staging models cast `channel_spend` counts to integers and handle `DATETIME` -> UTC normalization explicitly — which is the pathology doing its job. The benchmark receipt feeds the FinOps write-up and the Section 5.3 extrapolation.

### D6 — CRM free-tier fit: measurement done, trim decision requested

- **Date:** 2026-08-13 · **Decider:** human (requested; options below) · **Resolves:** C17 Phase 2 watch item
- **Measurement (the C17 ask):** scale-0.01 probe on Neon (22,716 rows COPYed into a throwaway table, measured, dropped): 270.8 B/row heap+PK-index. Extrapolated to the full 2,279,540 rows: **~0.62 GB against the ~0.5 GB free tier** (~24% over, before any secondary index). Column weight: `email_sha256` as hex `CHAR(64)` is the fattest column (27.4% of data bytes); `street_address`+`city` total 13.3%; names 5.9%; phone 5.5%. The handoff's guess (street/city fattest) is falsified: dropping them alone projects ~0.55 GB — still over.
- **Options:**
  - **(a) Trim + recode at load (recommended):** drop `street_address`/`city` (not in the C17e ER ladder of names/phones/zips) and store `email_sha256` as 32-byte `BYTEA` (loader hex-decodes in-stream; the generated CSV is untouched; staging can re-encode losslessly). Feasibility arithmetic: 0.617 − ~0.066 (street/city) − ~0.068 (hash recode) ≈ **0.48 GB projected, ~96% of quota** — viable but thin; Neon counts history/WAL toward storage, so set history retention to minimum and re-measure immediately after load. Fallback if it lands over: option (c).
  - **(b) Regenerate everything at a lower `--scale` (0.6–0.75):** ~0.37–0.47 GB CRM with real headroom at 0.6, cross-silo integrity preserved by construction — but every silo shrinks (auction ~15M events), S3/BQ must be re-uploaded and re-verified, all Phase 2 receipts recomputed, and lead volume falls well below the design's 2.4M target. Note: slicing *only* the CRM rows (the handoff's variant) is not offered — it would silently inflate the calibrated ~5% orphan rate into ~25%, changing a C17c pathology, which Phase 2 must not do.
  - **(c) First paid Neon tier:** zero data compromise, but a recurring charge against the ~$5/month cost story — the "cost discipline as content" objective takes the visible hit. *Pricing confirmed in console by the human, 2026-08-14: the lowest upgrade (Launch, usage-based) shows typical spend $15/month at "intermittent load, 1 GB storage" ($0.106/CU-hr compute + $0.35/GB-month storage) — roughly 3x the entire project's monthly budget, so this option is a last resort.*
- **Consequence of deciding:** the loader (`silos/crm_postgres/load.py`) is written and idempotent; whichever option is ratified loads the same day. Phase 2's exit criterion ("each silo queryable") stays open until then.
- **Decision (human, 2026-08-14): option (a)** — trim `street_address`/`city` and recode `email_sha256` to `BYTEA` at load, with minimum history retention and an immediate post-load re-measure; (c) is the fallback if the measured size still exceeds the tier. The generated CSV and `schema.sql` stay untouched; the deployed DDL lives in the loader and the divergence is documented in the silo audit memo.
- **Post-load measurement (2026-08-14):** all 2,279,540 rows loaded; **0.462 GB relation (0.411 heap + 0.051 PK index), 0.470 GB database logical size — under the ~0.5 GB tier with ~6% headroom**. Hash round-trip verified exact (stored 32-byte values re-encode to the CSV hex verbatim). The fallback was not needed. Watch item: headroom is thin — history retention stays at minimum, and any future schema addition re-measures first.

### D7 — Warehouse staging wiring: silo access patterns and staging conventions

*2026-08-20. Category: Phase 3 architecture, resolved while standing up the dbt staging layer. Proposed by the agent; **ratified 2026-08-20, accepted as recorded**.*

**(a) Marketing silo reads from local Parquet exports** (`warehouse/export_marketing.py`, BigQuery Storage read into git-ignored `data/silo_exports/marketing/`), refreshed only when the silo itself is reloaded. Design 4.1 names this pattern ("DuckDB reads local exports from BigQuery"); the rejected alternatives were the DuckDB BigQuery community extension (an unvetted dependency in the critical path) and per-run live queries (dbt-duckdb has no BigQuery transport, and re-scanning a static silo every run buys nothing). Adds `google-cloud-bigquery-storage` to `[dev]`.

**(b) CRM attaches live, read-only** (DuckDB postgres extension against Neon) — the design's stated pattern, kept because staging models materialize as tables, so the 2.28M-row wire pull happens once per `dbt build`, not per downstream query. The S3 auction lake likewise streams straight from the bucket via the least-privilege profile's credential chain.

**(c) Staging timestamp convention: everything lands naive-UTC in `*_utc` columns.** The auction silo logs UTC natively; CRM (US/Pacific) and marketing (US/Eastern) naive wall-clock are localized via ICU. The CRM DST fall-back hour is ambiguous *by construction* (C17f): ICU resolves it to one offset, a bounded one-hour error on roughly one wall-clock hour of rows per year, documented in the model rather than "corrected" — the pathology stays visible in the silo, staging just makes downstream joins sane.

**(d) Tests encode the intended pathologies, not textbook cleanliness**: `lead_id` unique but consumers deliberately not; `message_id` unique and messages→contacts referentially intact (verified against the generated data before writing the tests); event types closed to the four observed; no test dedupes or repairs what the fracture stage deliberately broke.

**Engineering consequence.** `warehouse/` is now a working dbt project (profile in-repo, `.env`-driven secrets, DuckDB file as a disposable build artifact). First full build: 5 staging models + 17 data tests green in 9m10s -- the auction pull dominates (547s for 25.0M events, 1.3 GB over httpfs), the CRM wire pull takes 102s (2.28M rows), and the marketing models run in seconds against local exports. Verification: staged row counts match all three silos exactly (25,024,926 / 2,279,540 / 1,586,849 + 4,045,057 + 84), and the CRM timezone unwind round-trips the fracture's own UTC-to-Pacific transform -- staged min/max land exactly on the pipeline's [2025-07-01 00:00 UTC, 2026-07-01) window. One fix en route: monthly display impressions (4.77B) overflow INT32; counts are BIGINT.

## Q-series — Open questions (parked, non-blocking)

| # | Question | Status |
| --- | --- | --- |
| Q1 | Domain name choice + registrar (Phase 7 hard requirement, nice-to-have earlier) | Open |
| Q2 | Repo visibility | **Resolved by D1** |
| Q3 | All-AWS variant (A3) | Closed unless target roles shift |
| Q4 | Demo a PR-based workflow for portfolio optics (A6) | Open |
| Q5 | iPinYou sampling strategy — full seasons 2–3 (~35 GB) vs. a 3–5 day sample per season | **Resolved by D4** (Kaggle mirror, day sample) |
