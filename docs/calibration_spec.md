# Calibration Spec — Source Datasets → Simulator Parameters

Status: v0.7 · Written against design.md v1.1, Section 3 · Changes cite trigger ids per `../meta/plan.md` Section 7 (changelog in Section 6)
Provenance: A — agent-proposed quantitative assumptions (decision log C1–C8), to be validated in the Phase 1 profiling notebooks

This spec defines, parameter by parameter, how the three public datasets drive the simulator. Every simulator parameter must trace to either (a) a fitted distribution from a source dataset, or (b) an explicitly declared design assumption. Calibration notebooks in `analysis/profiling/` must reproduce every fit and emit the side-by-side QA plots referenced in the design doc's risk register.

## 0. Conventions

- **Fit artifacts** are JSON files written to `simulation/params/` (e.g. `lendingclub_marginals.json`), versioned in git — the simulator reads *only* these artifacts, never the raw datasets. This keeps the simulator runnable without the multi-GB downloads.
- **QA gates**: each fitted distribution gets a quantitative acceptance check (KS distance, quantile table, or rate comparison) in its profiling notebook. Gates listed per section below.
- Randomness: all sampling is driven by a single seed via `numpy.random.default_rng(seed)` threaded through `SimConfig`.
- **Data-mutation ledger** (v0.2, INT-011): every profiling notebook records each operation that alters data — row drops, sentinel-to-NaN coercion, winsorization clips (with bounds), recategorization, imputation — with row counts, disposition, and rationale. The ledger is displayed in the executed notebook and embedded in the emitted params JSON under `metadata.data_mutations`, so each artifact carries its own cleaning provenance. Sentinel values (e.g., accepted `dti = 999`, the rejected file's negative DTI) are excluded from marginals, never winsorized into them; winsorized rows remain, clipped to stored bounds.
- **Narrated EDA companion** (v0.4, INT-012): every source dataset gets a read-only `*_eda.ipynb` alongside its fitting notebook, written to teach a reader who has never seen the data: what the dataset is and how it was generated (mechanics, observability limits), sample rows, a data dictionary (column, type, distinct values, nulls, definition), descriptive statistics with their semantics, collinearity and categorical nesting structure, known data quirks, declared assumptions, and the business implications for this project. EDA notebooks emit no artifacts and mutate nothing; foundational facts they establish are cited by the fitting notebooks rather than re-derived.

## 1. LendingClub (accepted + rejected) → consumers & leads

**Drives:** consumer credit features, application features, and the lead quality score that conditions the auction.

| Simulator parameter | Source field(s) | Fitting method |
| --- | --- | --- |
| Loan amount marginal | `loan_amnt` | Empirical quantiles (1000-point inverse-CDF lookup) |
| Purpose mix | `purpose` | Categorical frequencies, top 8 + "other" |
| Employment length | `emp_length` | Categorical frequencies (ordinal buckets) |
| DTI marginal | `dti` | Empirical quantiles, winsorized at 1%/99% |
| FICO band | `fico_range_low/high` | 5 bands (<600, 600–659, 660–719, 720–779, 780+), frequencies |
| State mix | `addr_state` | Categorical frequencies |
| Annual income marginal | `annual_inc` | Log-space empirical quantiles, winsorized |
| Feature correlation structure | all numeric above | Gaussian copula: Spearman correlation matrix on accepted+rejected pooled sample, sampled via scipy multivariate normal + inverse-CDF marginals |
| Lead quality score `q` | accept/reject label | Logistic regression of acceptance on features above; the fitted linear score (rescaled to [0,1]) is the raw score. **The simulator consumes `q` as the within-cohort percentile rank of that score** (v0.6, C11: ordering preserved exactly; the linear rescaling squashed the score into 0.6–1.0, wasting the range). The accepted/rejected *shape* is the realism anchor — not reused as an outcome |
| Applications per consumer (1–3) | — (assumption) | Zipf-ish: P(1)=0.75, P(2)=0.18, P(3)=0.07 — tuned so total leads ≈ 1.6× consumers |

**QA gates:** KS distance < 0.05 on each numeric marginal (simulated vs. source sample); categorical mixes within ±1pp; correlation matrix max absolute error < 0.1; simulated `q` distribution visually matches the accept-score histogram.

**Note on rejected loans:** the rejected file has far fewer columns (amount, DTI, state, emp length, risk score). Fit the full copula on accepted; use rejected only to (a) widen the DTI/amount tails and (b) fit the acceptance model. Document the column mapping (`Amount Requested`→`loan_amnt`, `Debt-To-Income Ratio`→`dti`, etc.) in the profiling notebook.

## 2. iPinYou RTB (seasons 2–3) → waterfall auction

**Drives:** buyer valuation landscape, bid participation, win/censoring dynamics.

| Simulator parameter | Source signal | Fitting method |
| --- | --- | --- |
| Winning-price landscape | `paying_price` in impression logs | Per-advertiser (μ, σ) for location/scale, plus the **empirical standardized log-price shape** as a 1000-point inverse-CDF table (v0.3, C10: measured lognormal deviation is up to 24% pooled / 40% per advertiser at deciles 1–9, so valuation noise samples the empirical shape; the adequacy measurements are retained as a documented finding). Levels rescale to lead-market price points (tier-6 floor ≈ $2 … tier-1 clearing ≈ $120 — C1) |
| Valuation ~ quality coupling | `paying_price` vs. CTR-proxy features | Regress log price on predicted CTR decile and **record** the fitted slope as a correct in-domain estimate (−0.149: in display RTB, high-CTR inventory skews toward cheap remnant placements, so price and the CTR proxy genuinely anticorrelate). The estimate is **non-transferable** — the target market's price-quality mechanism is underwriting economics, not remnant-inventory dynamics — so the simulator uses a **declared elasticity of 3.0 log-price units per percentile of quality (rank-q)** — C9 established the override pattern with +1.0; its own end-to-end gate falsified that value on first verification, and C11's verified triple superseded it (v0.6; C9, C11, INT-013, INT-014). Empirical −0.149 preserved in the artifact throughout |
| Bidders per auction (2–5 per tier) | bid density across season files | Empirical distribution of competing bids per auction, truncated to 2–5 |
| Bid/no-bid participation rate | bid vs. impression volume ratios | Per-buyer participation probability ~ Beta fit to observed rates; each seat's odds shift with lead quality — logit(p) + 2.0·(q − 0.5) — the C12 cherry-picking layer (v0.7): buyers bid more often on better leads, with tier floors calibrated under the mechanism |
| Floor-price dynamics | `floor_price` field | Distribution of floor-to-clearing ratios → sets tier floor schedule so sell-through cascades realistically (target: ~60% overall sell-through, declining by tier) |
| Censoring structure | second-price win logs | Structural: only the winning tier's clearing price is observed; losing tiers emit bids without prices. Validate that simulated censoring fraction (~40% unsold) matches the design target |
| CTR/CVR base rates | click/conversion logs | Base rates for the marketing silo's click model and the post-sale funded-loan rate (CRM `funded` flag ≈ CVR-scaled) |

**QA gates** (restated v0.6 per C11 — separation of concerns: C10 verifies the noise model, C9/C11 verifies quality transmission): per tier, deciles 1–9 of the simulated valuation **noise component** within ±10% (dollar space) of the artifact's empirical shape table — with strong quality coupling the marginal valuation legitimately widens, so the shape claim attaches to the noise; sell-through by tier monotone decreasing; censored fraction 35–45%; Spearman correlation between `q` and realized clearing price on sold leads **> 0.3**, so the declared elasticity is verified end-to-end rather than trusted. **Diagnostics (reported, not gated):** mean-q-by-tier (must be watched descending — the adverse-selection cascade made visible directly) and floor-pinned sale share (a Model-2 threat if it stays above ~85%). Reserve-bound share and both sigmas (pooled and within-vertical) are recorded in the artifact.

## 3. Criteo Uplift → marketing silo

**Drives:** campaign treatment structure and the (small, realistic) causal effect on application probability.

| Simulator parameter | Source signal | Fitting method |
| --- | --- | --- |
| Treatment/holdout split | `treatment` flag | Match Criteo's ~85/15 treated/control ratio |
| Baseline response rate | `conversion` in control | Control-group conversion rate → baseline application probability for messaged consumers |
| True uplift effect | treated − control conversion | Absolute uplift ≈ +0.1–0.3pp (Criteo-scale, i.e. *small*); implemented as an additive shift on application probability, heterogeneous by consumer engagement segment |
| Uplift heterogeneity | `f0–f11` feature interactions | Fit a simple uplift tree on Criteo; port the *spread* (ratio of top-decile to average uplift ≈ 3–5×) into segment-level multipliers |
| Message funnel rates | — + iPinYou CTR | Send→open ≈ 35%, open→click ≈ 8% (industry-plausible assumptions), click behavior correlated with the engagement segment that also drives uplift |
| Messages per contact | — (assumption) | Poisson(λ≈3) over the nurture window, capped at 10 |

**QA gates:** simulated holdout experiment, when analyzed naively, recovers the injected uplift within its own confidence interval; Qini curve on simulated data has realistic (modest) shape, not a toy staircase.

## 4. Pathology parameters (silo fracturing)

Not calibrated to a dataset — these are the §2.3 design dials, listed here so they live in one place:

| Dial | Default | Range to tune |
| --- | --- | --- |
| Duplicate-consumer rate | 8% | 5–12% — tune until ER F1 lands in 0.85–0.95 |
| Duplicate corruption mix | nickname 40% / email typo 30% / new phone 20% / all 10% | — |
| Orphaned auction events | 5% | 3–8% |
| Marketing-only contacts | 10% of contacts | — |
| Timezones | auction UTC, CRM US/Pacific naive, marketing US/Eastern | fixed |

## 5. Deliverables checklist (Phase 1 gate)

- [x] `analysis/profiling/01_lendingclub.ipynb` — fits §1, writes `simulation/params/lendingclub_marginals.json` + copula matrix (all QA gates pass, 2026-08-03)
- [x] `analysis/profiling/02_ipinyou.ipynb` — fits §2, writes `simulation/params/auction_landscape.json` (reopened 2026-08-07 when the new elasticity gate falsified C9's value; re-closed same day under C11, then re-executed with the C12 cherry-picking layer — all four gates pass, Spearman(q, price) = 0.513, floor-pinning 0.693; gates independently reproduced from the artifact by `tests/test_waterfall.py`)
- [x] `analysis/profiling/03_criteo.ipynb` — fits §3, writes `simulation/params/uplift_params.json` (all QA gates pass, 2026-08-04; measured top-decile/average = 7.04, see C6)
- [x] `analysis/profiling/02a_ipinyou_eda.ipynb` — narrated EDA companion (INT-012 convention; first instance, 2026-08-04)
- [x] `analysis/profiling/01a_lendingclub_eda.ipynb` — narrated EDA companion (2026-08-06)
- [x] `analysis/profiling/03a_criteo_eda.ipynb` — narrated EDA companion (2026-08-04)
- [ ] Each notebook ends with the QA-gate cells and a simulated-vs-source overlay plot (these become the calibration exhibits on the site)

## 6. Changelog

| Version | Date | Changes | Trigger |
| --- | --- | --- | --- |
| v0.1 | 2026-07 | Initial spec, written during Phase 0 | design.md Section 12 item 3 |
| v0.2 | 2026-08-03 | Data-mutation ledger convention and sentinel policy added to Section 0; Section 5 checklist tracks gate status | INT-011, P-005 |
| v0.3 | 2026-08-03 | Section 2 amended: empirical valuation shape replaces the lognormal (measured inadequacy), declared elasticity replaces the negative fitted slope, QA gates restated to separate landscape round-trip from reserve mechanics | C9, C10 |
| v0.4 | 2026-08-04 | Narrated EDA companion convention added to Section 0; EDA notebooks added to the Section 5 checklist | INT-012, P-006 |
| v0.5 | 2026-08-07 | Section 2 elasticity row reframed: valid in-domain estimate, non-transferable (human ratification of C9 with corrected framing); end-to-end elasticity gate added (Spearman q-price > 0.3 on sold leads) | C9, INT-013 |
| v0.6 | 2026-08-07 | C11 triple after the gate falsified C9's value: q consumed as percentile rank (Section 1), elasticity 3.0 on rank-q, within-vertical sigma 0.860 (both sigmas recorded); shape gate restated onto the noise component; mean-q-by-tier and floor-pinning diagnostics added | C11, INT-014 |
| v0.7 | 2026-08-07 | C12 cherry-picking participation layer (kappa 2.0) added to the Section 2 participation row; floors calibrated with it active; engine + artifact-only gate tests land in simulation/ and tests/ | C12 |
| v0.8 | 2026-08-07 | Consumer engine (`simulation/consumers.py`) implements Section 1 in production: copula sampling per the notebook's gated sampler, `fico_band` derived from `fico_mid` (coherence; gate margin verified), Faker vocabularies sampled through the stage RNG, C7 duplicate injection; Section 1 + Section 4 gates reproduced from the artifact alone by `tests/test_consumers.py` | C13 |
