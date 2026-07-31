# Tributary — Project Guide & Decision Log

*Written from the perspective of the AI collaborator (Claude) working on this build with Jordan. This is the working companion to [design.md](design.md): what the project is, how the design has been interpreted, every material assumption made so far, and guidance for the work ahead. When this file and reality disagree, update this file.*

Last updated: 2026-07-31 · Project status: **Phase 0 complete, Phase 1 (simulation engine) next**

---

## 1. What this project is

Tributary is a public portfolio project demonstrating the full data science lifecycle around a fictional two-sided lead-generation marketplace, **Cascadia Lead Exchange (CLX)**, which sells personal-loan leads through a 6-tier sequential waterfall auction.

The arc, in one paragraph: a Python simulator generates realistic marketplace data (consumers → loan applications → waterfall auctions → marketing touches), calibrated to three public datasets so the statistics are honest. The data is deliberately **fractured into three architecturally real silos** — an S3 Parquet event lake, a transactional Postgres CRM, and BigQuery marketing exports — with injected pathologies (incompatible keys, duplicates, orphans, grain mismatches, timezone chaos, semantic drift). The project then **unifies** the silos with dbt + Splink entity resolution, **proves** the unification worked by scoring against a hidden ground-truth crosswalk, **analyzes** marketplace economics before/after unification, and **optimizes** with ML (censored price models, reserve-price simulation, uplift, bandits). Everything ships on a public personal site that doubles as Jordan's professional profile.

## 2. Objectives, ranked

1. **Career artifact** (primary): a case study demonstrating DS project management + senior-level technical judgment — silo unification with measured accuracy, cost engineering, censored-data modeling, decision memos. The audience is recruiters and interviewers, not production users.
2. **Provability**: the signature move is the hidden `consumer_key` crosswalk (design §2.4). Every unification claim gets a number (ER precision/recall/F1). Never compromise this: the crosswalk stays local, git-ignored, never uploaded to any silo.
3. **Cost discipline as content**: staying under ~$5/month on free tiers is itself part of the story. Budget screenshots, before/after scan benchmarks, and the 100×-scale extrapolation are deliverables, not chores.
4. **Reproducibility**: one seeded command regenerates everything at any `--scale`; a devcontainer lets an interviewer run it in Codespaces.

## 3. Non-negotiable constraints

- **Fictionalization**: CLX is not Jordan's employer. No proprietary numbers, internal system names, or verbatim descriptions of real auction mechanics anywhere in the repo, commits, or site copy (design §1 confidentiality note). All statistics trace to iPinYou / LendingClub / Criteo or are declared assumptions.
- **Secrets hygiene**: no credentials in git — `.env` (git-ignored) + `~/.aws/credentials` profiles + ADC. Raw credential files live in `~/.tributary-credentials/`, outside the repo. The S3 bucket blocks all public access; only derived aggregate artifacts (HTML dashboards) ever go public.
- **The crosswalk never enters the cloud** — `data/private/` is git-ignored and stays on Jordan's machine only.
- **Free-tier fit**: CRM silo trimmed to Neon's ~0.5 GB; BigQuery within 10 GiB storage / 1 TiB query free tier; few-large-files Parquet layout on S3 (writes cost ~12× reads).

## 4. Current state (end of Phase 0)

**Repo**: https://github.com/JordanBeary/tributary.git — scaffold per design §11, devcontainer, `pyproject.toml` (Python ≥3.11), simulation package skeleton with a working CLI (`python -m simulation --scale 0.01`) and fixed stage contracts (bodies are Phase 1), infra scripts, calibration spec.

**Cloud, provisioned and verified reachable from local Python/CLI:**

| Silo | Resource | Notes |
| --- | --- | --- |
| Auction lake | S3 `clx-auction-lake-jb`, us-east-1 | Public access blocked; AWS account <AWS-ACCOUNT-ID> |
| CRM | Neon Postgres (free tier) | Connection string in `.env` (`CRM_DATABASE_URL`) |
| Marketing | BigQuery `tributary-clx:clx_marketing` | ADC auth as <GCP-AUTH-EMAIL> |

**Cost governance**: $10/month budgets on both clouds with 50/80/100% alerts (AWS → <ALERT-EMAIL>; GCP screenshot at [img/gcp-budget-thresholds.png](img/gcp-budget-thresholds.png)).

**AWS profiles**: `tributary-admin` (setup only; consider deactivating its key) and `tributary` (least-privilege, S3-only, single bucket — use for all daily work).

**Not yet done**: domain purchase; Kaggle token + dataset downloads (LendingClub via Kaggle CLI, iPinYou manual, Criteo via curl — see `scripts/download_datasets.sh`); everything Phase 1+.

## 5. Assumptions & decisions made along the way

These are choices I made that go beyond the letter of the design doc. Each is revisable — flagging one is cheap, silently diverging is not.

### Architecture & workflow

| # | Decision | Rationale |
| --- | --- | --- |
| A1 | **Simulator reads only fitted parameter artifacts** (`simulation/params/*.json`), never the raw public datasets | Keeps the simulator runnable without ~35 GB of downloads; makes calibration a one-time, versioned, reviewable step. The profiling notebooks are the only code that touches raw data. |
| A2 | Stage contracts (inputs/outputs/formats per stage) were frozen in `simulation/stages.py` docstrings before implementation | Lets silo loaders, dbt sources, and the ER pipeline be built in parallel against stable interfaces. |
| A3 | Free-tier hybrid architecture (design §4.1) chosen over the all-AWS variant (§4.2) | The design recommends it; nothing Jordan said suggested wanting the pure-AWS story. Revisit only if the target roles are AWS-specific. |
| A4 | `us-east-1` for AWS; `US` multi-region for BigQuery; Neon in us-east-2 | Cheapest/default regions; cross-region latency is irrelevant at this scale. |
| A5 | Python 3.12 via uv-managed standalone interpreter; project venv at `.venv/` | Machine's system Pythons (3.7/3.8) predate every dependency. See §7. |
| A6 | Incremental commit-and-push to `main` (no PR flow) | Solo portfolio project; review theater adds friction without value. Can switch to branches if Jordan wants the git history to demo PR discipline. |

### Naming & configuration

| # | Decision | Value |
| --- | --- | --- |
| B1 | S3 bucket name | `clx-auction-lake-jb` (globally-unique suffix = initials) |
| B2 | BigQuery dataset | `clx_marketing` |
| B3 | Budget alert email | <ALERT-EMAIL> (AWS); GCP budget set in console by Jordan |
| B4 | Budget amount/thresholds | $10/month, alerts at 50/80/100% actual spend, both clouds |
| B5 | IAM daily-work user | `tributary`: S3 Get/Put/Delete/List on the one bucket only |

### Calibration spec (docs/calibration_spec.md) — quantitative assumptions

The design doc names the source datasets but not the fitting details. These numbers are my proposals, to be validated or revised in the Phase 1 profiling notebooks:

| # | Assumption | Value | Status |
| --- | --- | --- | --- |
| C1 | Tier price scale: iPinYou provides price *shapes*; absolute lead prices are invented | tier-6 floor ≈ $2 … tier-1 clearing ≈ $120 | Declared design assumption — sanity-check against public lead-gen pricing anecdotes before publishing |
| C2 | Overall sell-through target | ~60%, monotone declining by tier; censored (unsold) fraction 35–45% | Tunable dial |
| C3 | Applications per consumer | P(1)=0.75, P(2)=0.18, P(3)=0.07 → ~1.6 leads/consumer | Chosen to hit design's 1.5M consumers → 2.4M leads |
| C4 | Marginal-fit QA gates | KS < 0.05 numeric; ±1pp categorical; copula max corr error < 0.1 | My thresholds; tighten/loosen with evidence |
| C5 | Message funnel | send→open 35%, open→click 8%; Poisson(λ≈3) messages/contact, cap 10 | Industry-plausible inventions — Criteo has no email funnel |
| C6 | Uplift | ~85/15 treated/control; +0.1–0.3pp absolute; top-decile ≈ 3–5× average uplift | Criteo-derived scale |
| C7 | Duplicate corruption mix | nickname 40% / email typo 30% / new phone 20% / all three 10% | Invented; tune until ER F1 lands in 0.85–0.95 (design's own target band) |
| C8 | LendingClub rejected file used only for tail-widening + acceptance model | — | Its schema is far narrower than the accepted file |

### Interpretations of ambiguous design points

- **"Conversion" semantics** will be implemented as three genuinely different column definitions in the three silos (sold lead / funded loan / email click) — the semantic-drift pathology must be real enough to bite during unification, not just documented.
- **CRM mutability** (design §2.3 "mutable/overwritten"): the CRM export will represent *current state* with overwritten fields, meaning the auction log and CRM can legitimately disagree — this is intended, not a bug to fix.
- **Design doc's cost/pricing figures** (§5) are treated as planning estimates from mid-2026; re-verify against provider pricing pages before publishing the cost write-up rather than citing the design doc.
- **Volumes** (9M events, etc.) are targets at `--scale 1.0`, not exact requirements; hitting free-tier limits takes precedence over hitting row counts.

## 6. Guidance for the work ahead

- **Gate on exit criteria, not enthusiasm.** Each phase's exit criteria are in design §9. Don't start Phase N+1 work while Phase N's criteria are unmet — the roadmap's cut-lines (models 3–6 are droppable; the site ships after Phase 4 regardless) only work if phases actually close.
- **Publish incrementally.** Every phase ends in a committable, showable artifact (design's burnout mitigation). Prefer a finished small thing over a half-built big thing.
- **Phase 1 order**: profiling notebooks first (they produce the param artifacts), then stages in pipeline order (consumers → leads → waterfall → marketing → fracture), each validated at `--scale 0.01` before scaling. The waterfall stage is the heart — budget the most care there, since models 1–3 and 5–6 all depend on its censoring structure being right.
- **Realism check that matters most**: ER difficulty. If Splink hits F1 ≈ 1.0, the pathologies are too clean — turn the dials (C7) up. Target band 0.85–0.95.
- **Keep the narrative voice fictional** in all repo text: "CLX's engineering team logs…", never anything that reads as Jordan's employer.
- **Cost artifacts as you go**: screenshot budgets, note bytes-scanned before/after partitioning, keep the receipts — §5.3's 100×-scale analysis and the FinOps write-up need them.
- **When adding dependencies**, they go in `pyproject.toml` (runtime) or `[dev]`/`[ml]` extras — the devcontainer and Codespaces flow depend on `pip install -e '.[dev]'` being sufficient.

## 7. Machine & environment quirks (read before running anything)

This machine deviates from defaults in ways that matter:

- **Homebrew is partially broken** (`/usr/local/share/man/man8` not user-writable; fix needs sudo). All CLIs were installed user-locally instead: `gh`, `aws` (`~/aws-cli`), `gcloud`/`bq` (`~/google-cloud-sdk`), `uv` — all symlinked into `~/.local/bin`, which is on PATH for *interactive* shells via `~/.zshrc`.
- **System Pythons are 3.7/3.8 — too old for everything.** Use `.venv/bin/python` (3.12, all dev deps installed) for project code. `gcloud` needs `CLOUDSDK_PYTHON` pointing at the uv 3.12 interpreter (exported in `~/.zshrc`; non-interactive scripts must set it explicitly).
- **Git auth** goes through `gh`'s credential helper (HTTPS). A broken `gh` binary exists in the `pBot` conda env; the real one is `~/.local/bin/gh`.
- **AWS calls**: use `--profile tributary` (least-privilege) for data work; `tributary-admin` only for infra changes.

## 8. Open questions (parked, non-blocking)

1. Domain name choice + registrar (Phase 7 hard requirement, nice-to-have earlier for site scaffolding).
2. Whether the GitHub repo stays public from the start or flips public at first publishable milestone (currently: public).
3. All-AWS variant (§A3) — closed unless Jordan's target roles shift.
4. Whether to demo a PR-based workflow for portfolio optics (§A6).
5. iPinYou sampling strategy — full seasons 2–3 (~35 GB) vs. a 3–5 day sample per season for calibration (spec currently assumes a sample is sufficient).
