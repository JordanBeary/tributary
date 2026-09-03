# Tributary — Project Guide (Local Track)

Working companion to [docs/design.md](docs/design.md): the local workload's current state and guidance for the work ahead. When this file and reality disagree, update this file.

What the project *is* — including the global/local split and the precedence rule — lives in [meta/charter.md](meta/charter.md). Decision tables formerly in this guide live in [meta/logs/decisions.md](meta/logs/decisions.md) (ids preserved); machine and environment quirks live in [CLAUDE.md](CLAUDE.md).

Status: v2.14, 2026-09-02 (reframe ratified: D11, D14–D18 and the C1 closure) · Written against design.md v1.8
Provenance: A (original), HD (v2.0 reconciliation), A (v2.1–v2.12), HD (v2.13–v2.14 reframe, INT-017)
Project status: **Phases 0–6 complete. Phase 5 closed 2026-09-02 (D11 ratified; the models page and cards publish, with a business-problem framing per INT-018). Phase 6 closed 2026-09-02 (D18 ratified): the recommended floor schedule re-run in the engine realizes +2.98% revenue per lead over five seeds (range +2.88% to +3.15%) against the replay's +2.02%, and survives buyer bid shading only to about 0.19; the strategy memo carries the seed band. Phase 7: first release live 2026-08-28 (D12); case study repositioned per D14 (ratified 2026-09-02) with the profile and resume moved to the portfolio repository (D15, ratified); all reframe edits sit uncommitted on branch `reframe-2026-09-01`. Publishing stays manual (`workflow_dispatch`) until the reframed site deploys, then flips to on-push (D14, decision packet Q-J). Session-start context: [meta/logs/sessions/2026-09-01_reframe_session.md](meta/logs/sessions/2026-09-01_reframe_session.md) and the decision packet [meta/logs/sessions/2026-09-01_decision_requests.md](meta/logs/sessions/2026-09-01_decision_requests.md); open items in [meta/logs/ledger.md](meta/logs/ledger.md).**

---

## 1. Objectives, ranked

1. **The global track** (primary): demonstrate that the human author can direct AI agents to get real work done — the harness, provenance decomposition, and honest records defined in [meta/charter.md](meta/charter.md). A phase is not done until its global exit criterion passes (charter Section 2).
2. **Case study** (top local objective): demonstrate translating business problems into decisions backed by models and experiments (reserve-floor policy, send policy, channel spend, duplicate consumers), identity modeling with measured accuracy, calibration judgment, and the infrastructure that made it computable presented as how the lab was built. The audience is technical evaluators reading the case study. The author's profile, resume, and networking material live in the portfolio repository (`JordanBeary/JordanBeary.github.io`), which links here (D15).
3. **Provability**: the signature move is the hidden `consumer_key` crosswalk (design Section 2.4). Every unification claim gets a number (ER precision/recall/F1). Never compromise this: the crosswalk stays local, git-ignored, never uploaded to any silo.
4. **Cost discipline as a supporting exhibit**: staying under ~$5/month on free tiers is kept intact as the appendix ("how the lab was built"); receipts and the 100x-scale extrapolation remain deliverables but are not lead content (D14).
5. **Reproducibility**: one seeded command regenerates everything at any `--scale`; a devcontainer lets any reader run it in Codespaces.

## 2. Non-negotiable constraints

- **Fictionalization without fictional names**: the simulated marketplace is not the author's employer. No proprietary numbers, internal system names, or verbatim descriptions of real auction mechanics anywhere in the repo, commits, or site copy. All statistics trace to iPinYou / LendingClub / Criteo or are declared assumptions. Narrative voice is *descriptive* — "the marketplace's engineering team logs...", never a named fictional company (conventions instruction 5, INT-001).
- **Secrets and identifier hygiene**: no credentials in git — `.env` (git-ignored) + `~/.aws/credentials` profiles + ADC; raw credential files in `~/.tributary-credentials/`, outside the repo. No account ids or personal emails in committed files (conventions Section 2). The S3 bucket blocks all public access; only derived aggregate artifacts (HTML dashboards) ever go public.
- **The crosswalk never enters the cloud** — `data/private/` is git-ignored and stays on the author's machine only.
- **Free-tier fit**: CRM silo trimmed to Neon's ~0.5 GB; BigQuery within 10 GiB storage / 1 TiB query free tier; few-large-files Parquet layout on S3 (writes cost ~12x reads).

## 3. Current state (Phases 0–6 complete; Phase 7 first release live, reframed release pending deploy)

**Simulation engine (Phase 1, complete 2026-08-10)**: all five stages implemented and artifact-driven (A1) — consumers (C13), leads (C14), waterfall (C11/C12), marketing with the uplift experiment and acquisition channels (C15/C16), and fracture with the Section 2.3 pathologies (C17). One seeded command (`python -m simulation --scale X`) regenerates everything: 1.8 s at 1%, ~2.5 min at 100% (1.5M consumer records, 2.4M leads, 26.4M auction events (C19), 2.19M messages, three native-format silos, crosswalk in `data/private/`). 42 tests reproduce the calibration QA gates from the params artifacts alone. Phase 2 watch items in C17: CRM CSV is 561 MB vs the ~0.4 GB Neon target; fracture peaks ~22 GB RSS at full scale.

**Repo**: scaffold per design Section 11, devcontainer, `pyproject.toml` (Python >= 3.11), simulation package with a working CLI (`python -m simulation --scale 0.01`), infra scripts, calibration spec, and the `meta/` harness (charter, conventions, provenance, logs, knowledge graph).

**Cloud, provisioned and verified reachable from local Python/CLI** (renamed 2026-08-03 per decisions D2/D3):

| Silo | Resource | Notes |
| --- | --- | --- |
| Auction lake | S3 `tributary-auction-lake-jb`, us-east-1 | Public access blocked |
| CRM | Neon Postgres (free tier) | Connection string in `.env` (`CRM_DATABASE_URL`) |
| Marketing | BigQuery `tributary-jb:marketing` | ADC auth done; quota project `tributary-jb` |

**Cost governance**: $10/month budgets on both clouds with 50/80/100% alerts (alert email in the AWS Budgets console; GCP budget is account-wide, screenshot at [docs/img/gcp-budget-thresholds.png](docs/img/gcp-budget-thresholds.png)).

**AWS profiles**: `tributary` (least-privilege, S3-only, single bucket — use for all daily work) and `tributary-admin` (infra only; its access key is kept **deactivated** between infra sessions, INT-005).

**Source datasets** (downloaded 2026-08-03 to git-ignored `data/raw/`, per `scripts/download_datasets.sh`): LendingClub accepted+rejected (gzip-verified), Criteo Uplift v2.1 (gzip-verified), and the D4 iPinYou day sample — 32 files across seasons 2–3, all verified against the dataset's `files.md5`. Kaggle token lives in `~/.tributary-credentials/` (never in the repo).

**Open items (2026-09-02, after the decision packet was answered)**: commit the reframe on `reframe-2026-09-01` and deploy it, then the publish-on-push workflow trigger (D14, Q-J); the business-problem framing for each model card and the models page (INT-018); two peer reviews. C1 is closed, D11 and D14–D18 are ratified, and the domain question (Q1) transferred to the portfolio repository (D15). Open items are tracked in `meta/logs/ledger.md`.

## 4. Guidance for the work ahead

- **Gate on exit criteria, not enthusiasm.** Each phase's local exit criteria are in design Section 9; the global exit criterion is in charter Section 2. Don't start Phase N+1 while Phase N's criteria are unmet — the roadmap's cut-lines (models 3–6 are droppable; the site ships after Phase 4 regardless) only work if phases actually close.
- **Publish incrementally.** Every phase ends in a committable, showable artifact (the design's burnout mitigation). Prefer a finished small thing over a half-built big thing.
- **Phase 1 order**: profiling notebooks first (they produce the param artifacts), then stages in pipeline order (consumers → leads → waterfall → marketing → fracture), each validated at `--scale 0.01` before scaling. The waterfall stage is the heart — budget the most care there, since models 1–3 and 5–6 all depend on its censoring structure being right.
- **Realism check that matters most**: ER difficulty. If Splink saturates, the pathologies are too clean — turn the drift dials (C18) up. Target band 0.8–0.9 (D8/P-010, supersedes the design's original 0.85–0.95).
- **Cost artifacts as you go**: screenshot budgets, note bytes-scanned before/after partitioning, keep the receipts — Section 5.3's 100x-scale analysis and the FinOps write-up need them.
- **Site (Phase 7) is a presentation layer only** (human directive, 2026-08-20): analysis, modeling, and DS products surface as *static cached artifacts* on the public site once complete — no live compute or backends behind it. This sharpens design Section 10's $0-hosting stance: build every deliverable so its presentation form is a cacheable static export. **Scaffolded 2026-08-28 (D12)**: Quarto → GitHub Pages; `site/tools/prerender.sh` copies dashboards and receipts from their source-of-truth locations (copies git-ignored); first release scoped to Phases 0–4 content. Home and resume pages were built 2026-08-28 (D13) and moved to the portfolio repository `JordanBeary/JordanBeary.github.io` on 2026-09-01 (D15); the site root is now a case-study landing and `resume.qmd` is a redirect stub to the portfolio site. First deploy 2026-08-28: GitHub Pages live at the github.io address (Actions source), manual `workflow_dispatch` publishing. Lighthouse (mobile) ≥ 95 on every page and category after three performance/accessibility passes. Outstanding before launch: deploy the reframed site and read it once, then the publish-on-push workflow trigger as a separate final commit (D14, decision packet Q-J); two peer reviews. The domain question (Q1) transferred to the portfolio repository.
- **Mart shape (Phase 4, built)**: wide, denormalized fact tables — event grain carrying consumer/demographic attributes row-wise — over narrow facts requiring joins (the author's stated OLAP preference, P-009/C17; realized as D10). Phase 5 features come from `fct_leads` / `fct_auction_events`, not from staging.
- **Phase 5 realism watch items (D10, amended by C19)**: C19 (2026-08-24, pending ratification) supersedes the two flagged gaps -- the funded flag now rides a modest price gradient (mean preserved) and recent repeat consumers win less and clear lower, both calibrated from the author's duplicate-performance data (P-011). Overall sell-through moves ~60% -> ~49% (the source data's own overall). C19 was ratified and redeployed 2026-08-24: silos, warehouse, scorecard, marts, and dashboards all reflect the C19 world (S3 + Neon reloaded; BigQuery untouched — marketing outputs byte-identical). The nurture experiment remains underpowered for the pooled ATE, so evaluate uplift models on Qini/ranking.
- **Phase 6 inputs (D11)**: model 3's recommended reserve schedule is validated by re-running the engine at those floors and measuring realized EPL against the replay's prediction — that comparison is the Phase 6 exit ("simulated EPL lift quantified with uncertainty bands"). The strategy memo draws on the four model cards and the m3 response curves; the bandit (design model 5) and OPE (model 6) remain droppable per the risk register. Built 2026-09-01: engine floor override (`SimConfig.floor_multipliers`, `--floor-multipliers`), `models/validate_floors.py`, five seeds at scale 0.2; realized lift +2.98% (range +2.88% to +3.15%) vs replay +2.02%; break-even bid shading about 0.19. Method and results ratified 2026-09-02 (D18) as the Phase 6 exit measurement.
- **When adding dependencies**, they go in `pyproject.toml` (runtime) or `[dev]`/`[ml]` extras — the devcontainer and Codespaces flow depend on `pip install -e '.[dev]'` being sufficient.
- **Session records**: follow the trigger table in [meta/conventions.md](meta/conventions.md) Section 3 — interventions, decisions, prompt candidates, graph diffs.
