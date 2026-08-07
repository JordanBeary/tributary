# Project "Tributary" — Portfolio Project Design Document

**An end-to-end data science build: engineering fractured marketplace data into unified analytics and ML-driven auction optimization.**

Author: Jordan Beary · Role: Data Science Project Manager / Lead DS · Status: v1.1 (changelog in Section 13) · Companion: calibration_spec.md v0.1
Provenance: HD — drafted by the agent from the author's design brief (prompt P-002 in `../meta/logs/prompts.md`); the silo-simulation-with-hidden-crosswalk concept is jointly attributable (author's seed, agent's elaboration)

---

## 1. Executive Summary

Tributary is a self-contained portfolio project that simulates the data environment of a fictional two-sided lead-generation marketplace — referred to throughout as *the simulated marketplace* or *the exchange* — which sells personal-loan leads to lender networks through a sequential waterfall auction. This document is the seed of the project's *local* track; the project's primary objective, the working method itself, is defined in [../meta/charter.md](../meta/charter.md). The project demonstrates the full data science lifecycle:

1. **Simulate** realistic operational data grounded in three public datasets (iPinYou RTB, LendingClub loans, Criteo Uplift), deliberately fractured into three incompatible data silos.
2. **Store** each silo in a different cloud system (object storage, transactional Postgres, analytical warehouse), mirroring how silos actually arise in companies.
3. **Unify** the silos with an entity-resolution and dimensional-modeling layer, quantifying the cost of the silo problem before and after.
4. **Analyze** marketplace health: funnel economics, earnings-per-lead (EPL) by auction tier, buyer concentration, bid landscapes.
5. **Optimize** with machine learning: conversion propensity, censored winning-price models, reserve-price simulation, uplift modeling, and a multi-armed bandit for waterfall ordering.
6. **Publish** the entire project on a public personal website that doubles as a professional profile (resume, positioning statement, case study, live dashboards).

Total cash cost target: **under $5/month** during development, ~$15/year steady-state (domain name only), by designing around cloud free tiers.

> **Confidentiality note:** Because this project is public, everything is fictionalized. The simulated marketplace is not your employer; all volumes, tier structures, buyer identifiers, prices, and problem statements are invented or derived from public datasets. Do not reuse proprietary numbers, internal system names, or verbatim descriptions of your employer's auction mechanics. The scenario should be *inspired by* the industry, not a copy of your day job. Per the no-fictional-names convention, the marketplace is deliberately unnamed; simulated buyers use structured identifiers (e.g. `buyer_t2_004`).

---

## 2. The Scenario & The Silo Problem

### 2.1 The simulated marketplace

**The exchange** operates a marketplace for personal-loan leads. Consumers submit loan applications through marketplace-owned landing pages; each application becomes a *lead* that is offered to lender networks through a 6-tier sequential waterfall auction. Buyers in higher tiers see the lead first at higher floor prices; unsold leads cascade downward.

### 2.2 How the silos arose (the narrative you'll tell)

Like most real companies' silos, the exchange's are an accident of organizational history:

| Silo | Owner (fictional) | System | Why it's separate |
| --- | --- | --- | --- |
| **Auction Platform** | Engineering | Event logs → S3 data lake (Parquet) | Built by platform engineers for operational logging, not analytics |
| **Lead CRM** | Sales Ops | PostgreSQL (transactional) | Bought/configured by a different team; row-level CRUD workloads |
| **Marketing Cloud** | Growth Marketing | Third-party ESP, data exported to BigQuery | SaaS vendor; data only available as scheduled exports |

The pain: no shared key, three grains, three timezones, duplicate consumers, and no one can answer "what is the true end-to-end ROI of a marketing campaign through to auction revenue?" That question is the project's north star.

### 2.3 Deliberate silo pathologies (the showcase)

The simulator injects **parameterized, realistic defects** so the unification work is genuinely hard and measurable:

- **Incompatible keys:** Auction silo uses `lead_uuid` (UUIDv4). CRM uses `lead_id` (integer sequence) + `email_sha256`. Marketing uses `contact_id` (MD5 of lowercased email) + campaign IDs. No silo contains another silo's key.
- **Duplicate consumers (~8%):** the same person applies multiple times with slightly different data (nickname vs. legal name, typo'd email, new phone) — echoing real duplicate-flooding problems in lead marketplaces.
- **Orphans (~5%):** auction events with no CRM record (data loss during a fictional "migration"), marketing contacts who never converted to leads.
- **Grain mismatches:** auction silo is event-grain (one row per bid), CRM is entity-grain (one row per lead, mutable/overwritten), marketing is message-grain.
- **Timezone chaos:** auction logs in UTC, CRM in US/Pacific naive timestamps, marketing exports in US/Eastern.
- **Semantic drift:** "conversion" means *sold lead* in the auction silo, *funded loan* in the CRM, and *email click* in marketing.

### 2.4 The hidden ground truth (your evaluation trick)

The simulator generates every consumer with a true `consumer_key`, then **strips it from all three silos** and saves it to a private crosswalk file that never enters the cloud environment. Entity-resolution accuracy (precision/recall of matched identities) is later scored against this crosswalk. This is the single most impressive artifact of the project: *you can prove your silo unification worked, with numbers.*

---

## 3. Source Data & Simulation Design

### 3.1 Public datasets used as statistical ground truth

| Dataset | What it contributes | Where |
| --- | --- | --- |
| **iPinYou RTB** (seasons 2–3) | Bid/win-price distributions, auction event structure, CTR/CVR base rates, censoring dynamics (you only observe the winning price when you win) | data.computational-advertising.org |
| **LendingClub accepted + rejected loans** | Personal-loan applicant features (amount, purpose, employment length, DTI, FICO band, state), accept/reject funnel shape | Kaggle: `wordsforthewise/lending-club` |
| **Criteo Uplift** | Treatment/control response structure for the marketing silo (realistic uplift signal size — small!) | Criteo AI Lab |

### 3.2 Simulation pipeline (`simulation/` package)

A single reproducible Python package (seeded) with five stages:

```
generate_consumers → generate_leads → run_waterfall → generate_marketing → fracture_into_silos
```

1. **`generate_consumers(n=1_500_000)`** — samples demographic + credit features by fitting marginal distributions and a correlation structure (Gaussian copula, e.g., via the SDV library or hand-rolled with scipy) to LendingClub accepted+rejected data. Emits the hidden `consumer_key` and synthetic identity attributes (name, email, phone, address), with duplicate-injection.
2. **`generate_leads`** — consumers submit 1–3 applications over a 12-month window; application features drawn conditioned on consumer credit profile. ~2.4M leads.
3. **`run_waterfall`** — the heart of the simulator. For each lead: 6 tiers, each with 2–5 fictional buyers whose private valuations come from a lognormal landscape calibrated to iPinYou winning-price distributions, conditioned on lead quality score. Buyers bid; if max bid ≥ tier floor, the lead sells and the cascade stops; otherwise it falls to the next tier. Emits event-grain logs: `bid_request`, `bid`, `win`, `no_sale`. ~9M events. This produces *naturally censored* price data — the exact structure needed for the ML workstream.
4. **`generate_marketing`** — pre-submission nurture campaigns (email/SMS sends, opens, clicks) with a randomized holdout flag and a small true uplift effect on application probability, calibrated to Criteo Uplift effect sizes. ~4M messages.
5. **`fracture_into_silos`** — applies the pathologies from §2.3, formats each silo in its native schema, and writes: Parquet (auction), CSV/SQL inserts (CRM), newline-JSON exports (marketing). Saves the private crosswalk locally.

**Why simulate rather than use the raw datasets directly?** (a) You get unifying keys with controllable messiness — impossible with unrelated public datasets; (b) you get a ground-truth crosswalk for evaluation; (c) you control scale to fit free tiers; (d) the narrative coheres as one company. The public datasets keep the *statistics* honest so models learn realistic patterns.

### 3.3 Target volumes & sizes

| Silo | Grain | Rows | On-disk size (compressed) |
| --- | --- | --- | --- |
| Auction (Parquet on S3) | event | ~9M | ~3–5 GB |
| CRM (Postgres) | lead | ~2.4M | ~0.4 GB (trimmed to fit free tier) |
| Marketing (BigQuery) | message | ~4M | ~1 GB |
| Unified warehouse (derived) | mixed | — | ~3–4 GB |
| **Total cloud footprint** |  |  | **~8–10 GB** |

Scale is a dial: the simulator takes `--scale` so you can develop at 1% locally and deploy at 100%.

---

## 4. Architecture: Storage, Compute & Unification

### 4.1 Recommended architecture (free-tier hybrid, ~$1–5/month)

```
                        ┌─────────────────────────────┐
                        │   simulation/ (local Python) │
                        └──────┬───────┬───────┬──────┘
                               │       │       │
              SILO 1           │  SILO 2       │   SILO 3
        ┌──────────────┐  ┌────▼─────────┐  ┌──▼──────────────┐
        │  AWS S3       │  │ Neon/Supabase│  │ BigQuery         │
        │  (Parquet     │  │ Postgres     │  │ (marketing       │
        │  auction lake)│  │ (CRM)        │  │  exports)        │
        └──────┬───────┘  └────┬─────────┘  └──┬──────────────┘
               │               │               │
               └───────┬───────┴───────┬───────┘
                       ▼               ▼
              ┌────────────────────────────────┐
              │  UNIFICATION LAYER              │
              │  DuckDB (dev) / BigQuery (prod) │
              │  + dbt (staging → ER → marts)   │
              │  + Splink (entity resolution)   │
              └───────────────┬────────────────┘
                              ▼
              ┌────────────────────────────────┐
              │  CONSUMPTION                    │
              │  Notebooks · ML training ·      │
              │  Static Plotly dashboards →     │
              │  published on personal site     │
              └────────────────────────────────┘
```

Design choices, and why:

- **Three genuinely different systems** is the point — the silo problem must be *architecturally real*, not just three folders. Object store + OLTP database + cloud warehouse is the canonical trio.
- **DuckDB as the local unification engine.** DuckDB reads S3 Parquet directly (`httpfs`), attaches Postgres directly (`postgres` extension), and reads local exports from BigQuery. You can develop the entire dbt project locally against real cloud silos for $0 compute, then run "production" transforms in BigQuery.
- **dbt** structures the transformation story recruiters recognize: `staging` (per-silo cleaning, timezone normalization, semantic alignment) → `intermediate` (entity resolution outputs) → `marts` (star schema: `fct_auction_events`, `fct_lead_sales`, `fct_messages`, `dim_consumer`, `dim_buyer`, `dim_campaign`).
- **Splink** (open-source probabilistic record linkage, runs on DuckDB) does the entity resolution — blocking rules on email hash/phone/name+zip, Fellegi-Sunter model, match probability thresholds. Scored against the hidden crosswalk.

### 4.2 Alternative: all-AWS variant (if you want a pure-AWS story)

S3 + Athena/Glue (replaces BigQuery/DuckDB) + RDS Postgres (replaces Neon). Cleaner vendor story, but RDS has no meaningful always-free tier — expect ~$15–30/month for a small instance unless covered by new-account credits. Athena costs $5 per TB scanned; with partitioned Parquet, project-scale queries scan MBs, so realistically <$1/month. Choose this variant only if AWS-depth is the skill you most want to signal.

---

## 5. Cloud Cost Analysis

Prices below are US-East list prices as of mid-2026; always re-check the provider pricing pages/calculators. Regions vary ~5–30%.

### 5.1 The pricing model you're working with

Cloud data cost has four levers — this project touches all four, which itself is a nice talking point:

1. **Storage at rest** ($/GB-month, varies by class)
2. **Requests** (per-1,000 API operations: writes cost more than reads)
3. **Query compute** (warehouse scans, $/TB)
4. **Egress** (data leaving the cloud to the internet)

### 5.2 Line-item estimates at project scale (~10 GB total)

| Item | Unit price | Project usage | Monthly cost |
| --- | --- | --- | --- |
| S3 Standard storage | $0.023/GB-mo (first 50 TB) | ~6 GB (raw + lake) | **$0.14** |
| S3 PUT/COPY/POST/LIST | $0.005 per 1,000 | ~5K writes (initial load + reruns) | **$0.03** |
| S3 GET | $0.0004 per 1,000 | ~500K reads (DuckDB scans, dev) | **$0.20** |
| S3 egress to internet | $0.09/GB after 100 GB/mo free (account-wide) | ~20–40 GB to your laptop | **$0.00** (inside free allowance) |
| BigQuery storage | ~$0.02/GB-mo, **first 10 GiB free** | ~1–2 GB | **$0.00** |
| BigQuery on-demand queries | ~$6.25/TB scanned, **first 1 TiB/mo free** | ~50–200 GB scanned | **$0.00** |
| Neon/Supabase Postgres | Free tier (~0.5 GB storage) | CRM trimmed to fit | **$0.00** |
| Optional: EC2 spot for ML training | ~$0.03–0.09/hr (t3/g4dn spot) | ~20 hrs/mo | **$1–2** (or $0: train locally/Colab) |
| **Total (recommended path)** |  |  | **≈ $0.50–3/month** |

Notes that make you sound like you've done this before:

- **Writes are ~12× the price of reads on S3** ($0.005 vs $0.0004 per 1,000). Design consequence: write *few, large* Parquet files (128–512 MB partitions), never millions of tiny objects.
- **Egress is the silent killer at real scale** — $0.09/GB adds up; the first 100 GB/month account-wide is free. Design consequence: push compute to the data (BigQuery/Athena) rather than repeatedly downloading raw data; for this project your dev pulls fit inside the free allowance.
- **Warehouse scans are priced by bytes scanned**, so partitioning (by event date) and columnar formats cut query cost 10–100×. Demonstrate this with a before/after benchmark in the write-up — a concrete FinOps artifact.
- **New AWS accounts (post-July-2025) get $200 in credits for 6 months** instead of the old perpetual 5 GB free tier — effectively this project is free on AWS for its whole build period.
- **Steady-state after development:** move raw simulation outputs to S3 Glacier Instant/Deep Archive (as low as ~$0.001–0.004/GB-mo) or simply keep only the 10 GB working set: **≈ $0.25/month** to keep the project alive indefinitely.

### 5.3 What it would cost at "realistic company scale" (a great section for the write-up)

Add a table extrapolating to 4M leads/month with full event logging (~1 TB/yr): S3 ≈ $23/TB-mo, warehouse scans become the dominant line, and egress discipline becomes mandatory. Showing you can reason about cost at 100× scale is a differentiator for DS-PM roles.

---

## 6. Development Workflow: VS Code ↔ Cloud

Key mental model: **your code runs where you launch it; the cloud is reached over authenticated APIs.** For 95% of this project, VS Code runs *locally* and talks to cloud storage — you are not "logging into the cloud" so much as making HTTPS calls to it.

### 6.1 Pattern A — Local VS Code, cloud data (default, use this)

1. **Authenticate once per provider:**
   - AWS: install AWS CLI → `aws configure` (stores an access key for a least-privilege IAM user in `~/.aws/credentials`). boto3, DuckDB `httpfs`, and pandas/pyarrow all pick it up automatically.
   - GCP: `gcloud auth application-default login` (browser OAuth flow; credentials cached locally). The BigQuery Python client picks it up automatically.
   - Postgres: a connection string (`postgresql://user:pass@host/db`) kept in a `.env` file (git-ignored) loaded with `python-dotenv`.
2. **Query from anywhere in VS Code:**
   - Notebooks (Jupyter extension) → `duckdb.sql("SELECT ... FROM read_parquet('s3://tributary-auction-lake-jb/events/date=*/**.parquet')")`
   - SQL files → **SQLTools** extension with Postgres + BigQuery drivers gives you connection explorer, autocomplete, and result grids inside VS Code.
   - dbt → **dbt Power User** extension: compile, run, test, and view lineage without leaving the editor.
3. **Recommended extensions:** Python, Jupyter, SQLTools (+ drivers), dbt Power User, AWS Toolkit, Rainbow CSV, GitLens.

Latency reality check: interactive queries against S3/BigQuery from your laptop feel near-local at this data size because only column chunks/result sets travel over the wire.

### 6.2 Pattern B — Remote-SSH (when training needs cloud compute)

For the heavier ML phases you can rent an EC2 spot instance, and VS Code's **Remote-SSH** extension runs a VS Code server *on the VM*: your editor UI stays local, but the terminal, Python interpreter, and file system are the remote machine's — zero egress for data already in S3 (same region), and it feels identical to local dev. Start/stop the instance per session; a stopped instance bills only its EBS volume (~$0.08/GB-mo).

### 6.3 Pattern C — Dev Containers / GitHub Codespaces (reproducibility flex)

Ship a `.devcontainer/devcontainer.json` (Python version, DuckDB, dbt, Splink pre-installed). Anyone — including an interviewer — can open the repo in GitHub Codespaces and run your pipeline in one click. Codespaces has a meaningful free monthly allowance for personal accounts.

### 6.4 Secrets & security hygiene (mention this on the site; recruiters notice)

- Least-privilege IAM: one user/role per silo, read-only where possible.
- No credentials in git — `.env` + `.gitignore`, plus a committed `.env.example`.
- S3 bucket blocks public access; the *website* only ever hosts derived, aggregate artifacts (HTML dashboards), never raw data.
- Budget alarm: an AWS Budgets + GCP budget alert at $10/month. Screenshot it for the write-up — cost governance is part of the PM story.

---

## 7. Analytics Workstream (the "so what" of unification)

Structure the analysis as **before vs. after unification** — this makes the silo problem visceral.

### 7.1 Before: what each silo can (and can't) answer alone
- Auction silo: sell-through rate and EPL by tier — but can't segment by consumer credit profile (that's in the CRM).
- CRM: application volume and quality mix — but can't see revenue outcomes.
- Marketing: opens/clicks by campaign — but "conversion" stops at the click; true ROI is unknowable.
- Deliverable: a short "silo audit" memo with three business questions each silo answers *wrongly or not at all*.

### 7.2 Entity resolution & reconciliation report (centerpiece)
- Splink model: blocking on `email_sha256`/phone/(surname + zip), comparison levels on name (Jaro-Winkler), DOB, address.
- **Scorecard vs. hidden crosswalk:** precision, recall, F1 of consumer matching; duplicate-cluster purity; orphan detection rate.
- Reconciliation stats: % of auction events joinable to a consumer before ER (should be ~0%) vs. after (target >95%); revenue attributable to marketing before vs. after.

### 7.3 After: unified marketplace analytics
- Full-funnel: impressions → applications → auction offered → sold → (simulated) funded, with drop-off economics.
- EPL by tier × credit band; buyer concentration (HHI) by tier; duplicate-consumer cost quantified in dollars.
- Marketing → revenue attribution: campaign ROI measured through to auction sale price, only possible post-unification.
- Deliverables: 4–6 static interactive dashboards (Plotly HTML) embedded on the website.

## 8. ML Optimization Workstream

Ordered by increasing sophistication; each model gets a one-page model card on the site.

| # | Model | Technique | Business question |
| --- | --- | --- | --- |
| 1 | Sale propensity | Gradient boosting (LightGBM), calibrated | Which leads will sell, and at which tier? |
| 2 | Winning-price landscape | **Censored regression** (Tobit / survival framing) — you only observe the clearing price on sales | What would buyers pay? (foundation for pricing) |
| 3 | Reserve/floor optimization | Counterfactual simulation over the calibrated landscape; grid + Bayesian optimization of tier floors | What floor schedule maximizes expected EPL? |
| 4 | Marketing uplift | T-learner / uplift trees on the randomized holdout | Who should we message at all? |
| 5 | Waterfall ordering bandit | Thompson sampling over tier/buyer orderings in a simulator loop | Can adaptive routing beat the static waterfall? |
| 6 | *(Stretch)* Off-policy evaluation | IPS / doubly-robust estimates of the new floor policy from logged data | Can we trust the policy without an A/B test? |

The censoring in #2 and the OPE in #6 mirror genuinely hard problems in auction data science — they signal senior-level judgment far more than another CTR model.

Strategy deliverable: a **3-page "Optimization Strategy Memo"** written for the marketplace's (simulated) exec team — expected EPL lift, risk register, rollout/gating plan, and what you'd A/B test first. This is the artifact that shows DS *management*, not just modeling.

---

## 9. Project Roadmap (PM view)

Assumes ~8–10 focused hours/week; ~14 weeks total. Phases gate on exit criteria, not dates.

| Phase | Wks | Focus | Key deliverables | Exit criteria |
| --- | --- | --- | --- | --- |
| 0 | 1 | Setup & scoping | Repo + devcontainer; cloud accounts; IAM; budget alarms; this design doc committed | All clouds reachable from VS Code; $10 budget alerts live |
| 0.5 | 1 | Harness build | `meta/` (charter, conventions, provenance, logs, knowledge graph); `CLAUDE.md`; naming and identifier corrections | Graph validates in CI; logs seeded; provenance backfilled |
| 1 | 2–3 | Simulation engine | `simulation/` package; calibration notebooks vs. iPinYou/LendingClub/Criteo; hidden crosswalk | 1% and 100% scale runs reproducible from one seeded command; distribution QA passes |
| 2 | 1 | Silo deployment | S3 lake (partitioned Parquet); Neon Postgres loaded; BigQuery marketing dataset | Each silo queryable from VS Code; silo audit memo drafted |
| 3 | 2 | Unification | dbt staging models; Splink ER pipeline; reconciliation scorecard | ER F1 ≥ 0.9 vs. crosswalk; >95% auction events consumer-joinable |
| 4 | 2 | Analytics | Star schema marts; 4–6 dashboards; before/after silo analysis | Every §7.1 "unanswerable" question now answered with a chart |
| 5 | 3 | ML models 1–4 | Trained models + model cards; evaluation notebooks | Beats naive baselines; calibration & uplift Qini curves documented |
| 6 | 1–2 | Optimization & strategy | Floor-price simulation; bandit experiment; Strategy Memo | Simulated EPL lift quantified with uncertainty bands |
| 7 | 2 | Website & launch | Site live: profile, resume, case study, dashboards, repo | Domain live; Lighthouse ≥ 90; case study reviewed by 2 peers |

**Global exit criterion (every phase, in addition to the table above):** a phase is not done until `meta/logs/` is current for the phase, `meta/graph/graph.yaml` validates, and provenance is recorded for the phase's artifacts. See [../meta/charter.md](../meta/charter.md) Section 2.

**Risk register (top 5):**

| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| Scope creep (this doc is ambitious) | High | Phases 5–6 are cuttable to models 1–2 only; site ships after Phase 4 regardless |
| Synthetic data too clean → trivial ER | Medium | Pathology injection is parameterized; tune until ER F1 lands in 0.85–0.95, not 1.0 |
| Free-tier limits shift | Medium | Scale dial (§3.3); Postgres silo is deliberately the smallest |
| Simulation realism questioned in interviews | Medium | Calibration notebooks showing simulated vs. source-data distributions side-by-side |
| Burnout / stall | High | Every phase ends in a publishable artifact; publish incrementally, not big-bang |

---

## 10. Public Website & Portfolio Presentation

### 10.1 Stack (all $0 hosting)

- **Recommended: Quarto** — Markdown + rendered Jupyter notebooks → static site; publishes to **GitHub Pages** free; DS-native and low-maintenance. (Alternative: Astro/Next.js on Vercel or Netlify free tiers if you want a more designed feel.)
- Interactive charts: export Plotly figures as self-contained HTML and embed — interactivity with zero servers. If you want one *live* app (e.g., the bandit simulator), Streamlit Community Cloud hosts it free.
- Custom domain: ~$10–15/year (the project's only mandatory recurring cost). Point it at GitHub Pages/Vercel.

### 10.2 Site architecture

```
yourname.com
├── /            Home: positioning statement ("cover letter" voice) —
│                who you are, how you create value, 3 proof points
├── /resume      HTML resume + downloadable PDF (keep both in sync)
├── /tributary   The case study (the main event)
│   ├── Overview: problem → architecture diagram → results in 60 seconds
│   ├── The Silo Problem: before/after, ER scorecard
│   ├── Cost engineering: the $3/month architecture + 100× scale analysis
│   ├── Dashboards (embedded)
│   ├── ML & Strategy Memo
│   ├── "How this was built": the human-directs-agents working method,
│   │       generated from meta/ (charter, interventions, provenance)
│   └── "Run it yourself": Codespaces badge + repo link
└── /writing     (optional) short posts: censored price modeling, FinOps for DS, etc.
```

### 10.3 Case study writing guidance

- Lead with outcomes, not tools: "Unified three incompatible data systems and recovered 95% of previously unjoinable revenue events; identified a simulated +X% EPL floor-price policy."
- One architecture diagram above the fold; details expandable.
- Show the scorecards (ER F1, cost table, calibration plots) — numbers beat adjectives.
- Every claim links to the notebook/model card that produced it.

---

## 11. Repository Structure

```
tributary/
├── .devcontainer/          # one-click reproducible environment
├── simulation/             # consumer/lead/waterfall/marketing generators + calibration
├── infra/                  # setup scripts (bucket creation, IAM policy JSON, budget alarms)
├── silos/                  # loaders: s3_lake/, crm_postgres/, marketing_bq/
├── warehouse/              # dbt project (staging → intermediate → marts)
├── er/                     # Splink pipeline + scoring vs. crosswalk
├── analysis/               # notebooks + dashboard exports
├── models/                 # ML training, model cards, strategy memo
├── site/                   # Quarto project
└── README.md               # the 60-second pitch + architecture diagram
```

---

## 12. Immediate Next Actions

1. Buy the domain; create AWS + GCP accounts; set budget alarms (30 min).
2. Download iPinYou (seasons 2–3), LendingClub (accepted + rejected), Criteo Uplift; run profiling notebooks (Phase 1 start).
3. Write the calibration spec: which distributions from each source dataset drive which simulator parameters.
4. Stand up the repo with devcontainer and this document as `docs/design.md`.

---

## 13. Changelog

Per-document versioning (`../meta/plan.md` Section 7): every change cites the intervention or decision id that triggered it.

| Version | Date | Changes | Trigger |
| --- | --- | --- | --- |
| v1.0 | 2026-07 | Initial design, drafted from the author's brief in the founding chat | P-002 |
| v1.1 | 2026-08-03 | Fictional company name replaced with descriptive terms; confidentiality-note emoji removed; author placeholder resolved; example S3 path corrected to the real bucket; provenance front matter added; reframing sentence linking `meta/charter.md`; Phase 0.5 and the global exit criterion added to the roadmap; "How this was built" page added to the site plan; companion-version discipline adopted | INT-001, INT-003, INT-004, INT-007, INT-008; D1–D3 |
| v1.2 | 2026-08-07 | Section 3.2: identity attributes described as synthetic data — the narrative names the data, not the generating library (ratification amendment to C13b) | C13, P-007 |
