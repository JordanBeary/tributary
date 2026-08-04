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
| C1 | Tier price scale: iPinYou provides price *shapes*; absolute lead prices are invented | tier-6 floor ~ $2 ... tier-1 clearing ~ $120 | Declared design assumption — sanity-check against public lead-gen pricing anecdotes before publishing |
| C2 | Overall sell-through target | ~60%, monotone declining by tier; censored (unsold) fraction 35–45% | Tunable dial |
| C3 | Applications per consumer | P(1)=0.75, P(2)=0.18, P(3)=0.07 → ~1.6 leads/consumer | Chosen to hit design's 1.5M consumers → 2.4M leads |
| C4 | Marginal-fit QA gates | KS < 0.05 numeric; ±1pp categorical; copula max corr error < 0.1 | Agent-proposed thresholds; tighten/loosen with evidence |
| C5 | Message funnel | send→open 35%, open→click 8%; Poisson(λ≈3) messages/contact, cap 10 | Industry-plausible inventions — Criteo has no email funnel |
| C6 | Uplift | ~85/15 treated/control; +0.1–0.3pp absolute; top-decile ≈ 3–5× average uplift | Criteo-derived scale |
| C7 | Duplicate corruption mix | nickname 40% / email typo 30% / new phone 20% / all three 10% | Invented; tune until ER F1 lands in 0.85–0.95 (design's own target band) |
| C8 | LendingClub rejected file used only for tail-widening + acceptance model | — | Its schema is far narrower than the accepted file |

### C-series additions (Phase 1, agent-proposed, pending human review)

| # | Assumption | Value | Status |
| --- | --- | --- | --- |
| C9 | Valuation-quality elasticity: the fitted iPinYou CTR-decile slope is **negative** (−0.149 — high-CTR display inventory clears cheaper, a remnant-inventory artifact with the wrong sign for a lead marketplace, where quality must drive price for the design's adverse-selection cascade to exist) | Empirical slope recorded in the artifact; simulator uses a **declared elasticity of +1.0** log-price units per unit `q` (same declared-assumption pattern as C1's price levels) | Proposed 2026-08-03; sanity-check the magnitude when Phase 3 ER and Phase 5 pricing models are live |
| C10 | Winning-price distribution model: iPinYou's advertiser-standardized log prices deviate from lognormal by up to 24% pooled / 40% per advertiser at deciles 1–9 — the spec's original "lognormal + ±10% Q-Q gate" pair is unsatisfiable with its own model | Valuation noise drawn from the **empirical standardized log-price shape** (1000-point inverse-CDF table in the artifact, house style per A1/01); per-advertiser (mu, sigma) retained for location/scale; lognormal-adequacy measurements kept as a documented finding | Proposed 2026-08-03; spec amended v0.3 |

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

## Q-series — Open questions (parked, non-blocking)

| # | Question | Status |
| --- | --- | --- |
| Q1 | Domain name choice + registrar (Phase 7 hard requirement, nice-to-have earlier) | Open |
| Q2 | Repo visibility | **Resolved by D1** |
| Q3 | All-AWS variant (A3) | Closed unless target roles shift |
| Q4 | Demo a PR-based workflow for portfolio optics (A6) | Open |
| Q5 | iPinYou sampling strategy — full seasons 2–3 (~35 GB) vs. a 3–5 day sample per season | **Resolved by D4** (Kaggle mirror, day sample) |
