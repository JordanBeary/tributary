# Calibration Spec — Source Datasets → Simulator Parameters

Status: v0.2 · Written against design.md v1.1, Section 3 · Changes cite trigger ids per `../meta/plan.md` Section 7 (changelog in Section 6)
Provenance: A — agent-proposed quantitative assumptions (decision log C1–C8), to be validated in the Phase 1 profiling notebooks

This spec defines, parameter by parameter, how the three public datasets drive the simulator. Every simulator parameter must trace to either (a) a fitted distribution from a source dataset, or (b) an explicitly declared design assumption. Calibration notebooks in `analysis/profiling/` must reproduce every fit and emit the side-by-side QA plots referenced in the design doc's risk register.

## 0. Conventions

- **Fit artifacts** are JSON files written to `simulation/params/` (e.g. `lendingclub_marginals.json`), versioned in git — the simulator reads *only* these artifacts, never the raw datasets. This keeps the simulator runnable without the multi-GB downloads.
- **QA gates**: each fitted distribution gets a quantitative acceptance check (KS distance, quantile table, or rate comparison) in its profiling notebook. Gates listed per section below.
- Randomness: all sampling is driven by a single seed via `numpy.random.default_rng(seed)` threaded through `SimConfig`.
- **Data-mutation ledger** (v0.2, INT-011): every profiling notebook records each operation that alters data — row drops, sentinel-to-NaN coercion, winsorization clips (with bounds), recategorization, imputation — with row counts, disposition, and rationale. The ledger is displayed in the executed notebook and embedded in the emitted params JSON under `metadata.data_mutations`, so each artifact carries its own cleaning provenance. Sentinel values (e.g., accepted `dti = 999`, the rejected file's negative DTI) are excluded from marginals, never winsorized into them; winsorized rows remain, clipped to stored bounds.

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
| Lead quality score `q` | accept/reject label | Logistic regression of acceptance on features above; the fitted linear score (rescaled to [0,1]) becomes `q`. The accepted/rejected *shape* is the realism anchor — not reused as an outcome |
| Applications per consumer (1–3) | — (assumption) | Zipf-ish: P(1)=0.75, P(2)=0.18, P(3)=0.07 — tuned so total leads ≈ 1.6× consumers |

**QA gates:** KS distance < 0.05 on each numeric marginal (simulated vs. source sample); categorical mixes within ±1pp; correlation matrix max absolute error < 0.1; simulated `q` distribution visually matches the accept-score histogram.

**Note on rejected loans:** the rejected file has far fewer columns (amount, DTI, state, emp length, risk score). Fit the full copula on accepted; use rejected only to (a) widen the DTI/amount tails and (b) fit the acceptance model. Document the column mapping (`Amount Requested`→`loan_amnt`, `Debt-To-Income Ratio`→`dti`, etc.) in the profiling notebook.

## 2. iPinYou RTB (seasons 2–3) → waterfall auction

**Drives:** buyer valuation landscape, bid participation, win/censoring dynamics.

| Simulator parameter | Source signal | Fitting method |
| --- | --- | --- |
| Winning-price landscape | `paying_price` in impression logs | Fit lognormal (μ, σ) per advertiser-vertical group; map the *shape* (σ, tail behavior) to the marketplace's tiers, rescaling μ to lead-market price points (tier-6 floor ≈ $2 … tier-1 clearing ≈ $120 — design assumption, documented) |
| Valuation ~ quality coupling | `paying_price` vs. CTR-proxy features | Regress log price on predicted CTR decile; the fitted slope becomes the elasticity of buyer valuation w.r.t. lead quality `q` |
| Bidders per auction (2–5 per tier) | bid density across season files | Empirical distribution of competing bids per auction, truncated to 2–5 |
| Bid/no-bid participation rate | bid vs. impression volume ratios | Per-buyer participation probability ~ Beta fit to observed rates |
| Floor-price dynamics | `floor_price` field | Distribution of floor-to-clearing ratios → sets tier floor schedule so sell-through cascades realistically (target: ~60% overall sell-through, declining by tier) |
| Censoring structure | second-price win logs | Structural: only the winning tier's clearing price is observed; losing tiers emit bids without prices. Validate that simulated censoring fraction (~40% unsold) matches the design target |
| CTR/CVR base rates | click/conversion logs | Base rates for the marketing silo's click model and the post-sale funded-loan rate (CRM `funded` flag ≈ CVR-scaled) |

**QA gates:** simulated log winning-price Q-Q plot vs. rescaled iPinYou within ±10% at deciles 1–9; sell-through by tier monotone decreasing; censored fraction 35–45%.

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
- [ ] `analysis/profiling/02_ipinyou.ipynb` — fits §2, writes `simulation/params/auction_landscape.json`
- [ ] `analysis/profiling/03_criteo.ipynb` — fits §3, writes `simulation/params/uplift_params.json`
- [ ] Each notebook ends with the QA-gate cells and a simulated-vs-source overlay plot (these become the calibration exhibits on the site)

## 6. Changelog

| Version | Date | Changes | Trigger |
| --- | --- | --- | --- |
| v0.1 | 2026-07 | Initial spec, written during Phase 0 | design.md Section 12 item 3 |
| v0.2 | 2026-08-03 | Data-mutation ledger convention and sentinel policy added to Section 0; Section 5 checklist tracks gate status | INT-011, P-005 |
