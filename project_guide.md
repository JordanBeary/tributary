# Tributary — Project Guide (Local Track)

Working companion to [docs/design.md](docs/design.md): the local workload's current state and guidance for the work ahead. When this file and reality disagree, update this file.

What the project *is* — including the global/local split and the precedence rule — lives in [meta/charter.md](meta/charter.md). Decision tables formerly in this guide live in [meta/logs/decisions.md](meta/logs/decisions.md) (ids preserved); machine and environment quirks live in [CLAUDE.md](CLAUDE.md).

Status: v2.4, 2026-08-20 (Phase 3 started) · Written against design.md v1.3
Provenance: A (original), HD (v2.0 reconciliation), A (v2.1–v2.4)
Project status: **Phases 0–2 complete (Phase 2 closed 2026-08-14: three silos live, audit memo, cost receipts). Phase 3 in progress — dbt staging layer over all three silos built and green (5 models, 17 tests, `warehouse/`; D7 ratified); Splink ER pipeline built and scored: link F1 0.976, dedupe F1 0.997 — both above the 0.85–0.95 band; pathology-dial decision D8 pending (blocks ER finalization, not other work).**

---

## 1. Objectives, ranked

1. **The global track** (primary): demonstrate that the human author can direct AI agents to get real work done — the harness, provenance decomposition, and honest records defined in [meta/charter.md](meta/charter.md). A phase is not done until its global exit criterion passes (charter Section 2).
2. **Career artifact** (top local objective): a case study demonstrating DS project management + senior-level technical judgment — silo unification with measured accuracy, cost engineering, censored-data modeling, decision memos. The audience is recruiters and interviewers, not production users.
3. **Provability**: the signature move is the hidden `consumer_key` crosswalk (design Section 2.4). Every unification claim gets a number (ER precision/recall/F1). Never compromise this: the crosswalk stays local, git-ignored, never uploaded to any silo.
4. **Cost discipline as content**: staying under ~$5/month on free tiers is itself part of the story. Budget screenshots, before/after scan benchmarks, and the 100x-scale extrapolation are deliverables, not chores.
5. **Reproducibility**: one seeded command regenerates everything at any `--scale`; a devcontainer lets an interviewer run it in Codespaces.

## 2. Non-negotiable constraints

- **Fictionalization without fictional names**: the simulated marketplace is not the author's employer. No proprietary numbers, internal system names, or verbatim descriptions of real auction mechanics anywhere in the repo, commits, or site copy. All statistics trace to iPinYou / LendingClub / Criteo or are declared assumptions. Narrative voice is *descriptive* — "the marketplace's engineering team logs...", never a named fictional company (conventions instruction 5, INT-001).
- **Secrets and identifier hygiene**: no credentials in git — `.env` (git-ignored) + `~/.aws/credentials` profiles + ADC; raw credential files in `~/.tributary-credentials/`, outside the repo. No account ids or personal emails in committed files (conventions Section 2). The S3 bucket blocks all public access; only derived aggregate artifacts (HTML dashboards) ever go public.
- **The crosswalk never enters the cloud** — `data/private/` is git-ignored and stays on the author's machine only.
- **Free-tier fit**: CRM silo trimmed to Neon's ~0.5 GB; BigQuery within 10 GiB storage / 1 TiB query free tier; few-large-files Parquet layout on S3 (writes cost ~12x reads).

## 3. Current state (end of Phase 1 build)

**Simulation engine (Phase 1, complete 2026-08-10)**: all five stages implemented and artifact-driven (A1) — consumers (C13), leads (C14), waterfall (C11/C12), marketing with the uplift experiment and acquisition channels (C15/C16), and fracture with the Section 2.3 pathologies (C17). One seeded command (`python -m simulation --scale X`) regenerates everything: 1.8 s at 1%, ~2.5 min at 100% (1.5M consumer records, 2.4M leads, 24.5M auction events, 4.05M messages, three native-format silos, crosswalk in `data/private/`). 42 tests reproduce the calibration QA gates from the params artifacts alone. Phase 2 watch items in C17: CRM CSV is 561 MB vs the ~0.4 GB Neon target; fracture peaks ~22 GB RSS at full scale.

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

**Not yet done**: domain purchase (Q1); everything else Phase 1+.

## 4. Guidance for the work ahead

- **Gate on exit criteria, not enthusiasm.** Each phase's local exit criteria are in design Section 9; the global exit criterion is in charter Section 2. Don't start Phase N+1 while Phase N's criteria are unmet — the roadmap's cut-lines (models 3–6 are droppable; the site ships after Phase 4 regardless) only work if phases actually close.
- **Publish incrementally.** Every phase ends in a committable, showable artifact (the design's burnout mitigation). Prefer a finished small thing over a half-built big thing.
- **Phase 1 order**: profiling notebooks first (they produce the param artifacts), then stages in pipeline order (consumers → leads → waterfall → marketing → fracture), each validated at `--scale 0.01` before scaling. The waterfall stage is the heart — budget the most care there, since models 1–3 and 5–6 all depend on its censoring structure being right.
- **Realism check that matters most**: ER difficulty. If Splink hits F1 ~ 1.0, the pathologies are too clean — turn the dials (C7) up. Target band 0.85–0.95.
- **Cost artifacts as you go**: screenshot budgets, note bytes-scanned before/after partitioning, keep the receipts — Section 5.3's 100x-scale analysis and the FinOps write-up need them.
- **Site (Phase 7) is a presentation layer only** (human directive, 2026-08-20): analysis, modeling, and DS products surface as *static cached artifacts* on the public site once complete — no live compute or backends behind it. This sharpens design Section 10's $0-hosting stance: build every deliverable so its presentation form is a cacheable static export.
- **Mart shape (Phase 4)**: prefer wide, denormalized fact tables — event grain carrying consumer/demographic attributes row-wise — over narrow facts requiring joins (the author's stated OLAP preference, P-009/C17).
- **When adding dependencies**, they go in `pyproject.toml` (runtime) or `[dev]`/`[ml]` extras — the devcontainer and Codespaces flow depend on `pip install -e '.[dev]'` being sufficient.
- **Session records**: follow the trigger table in [meta/conventions.md](meta/conventions.md) Section 3 — interventions, decisions, prompt candidates, graph diffs.
