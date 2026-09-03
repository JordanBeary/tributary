# Tributary

**A dual-track project: a data science case study — a lead marketplace's business questions turned into decisions — and the working record of a human directing AI agents to produce it.**

Author: Jordan Beary — [profile and resume](https://jordanbeary.github.io/) · [case-study site](https://jordanbeary.github.io/tributary/)

## The two tracks

**The global track (primary)** is the working method itself: the harness that makes AI agents more effective than out-of-the-box, transparent decomposition of human versus agent contribution, and an honest log of corrections, decisions, and steering prompts. It lives in [meta/](meta/) — start with the [charter](meta/charter.md), then the [intervention log](meta/logs/interventions.md) and [provenance ledger](meta/provenance.md). The method is the exhibit; the build below is the demonstration payload.

**The local track** is the case study: a simulated two-sided marketplace sells personal-loan leads through a 6-tier sequential waterfall auction, and the study answers the questions its business would ask — which channels earn their spend, what a duplicate consumer costs, where reserve floors should sit, whom a nurture campaign should reach — with identity modeling scored against hidden ground truth, calibrated models (sale propensity, a censored winning-price landscape, counterfactual floor optimization validated by re-running the engine, uplift on a randomized holdout), and a strategy memo. The lab those answers come from is deliberately fractured operational data in three architecturally real systems (S3 Parquet lake, transactional Postgres, BigQuery exports), unified with entity resolution and wide analytical marts; the waterfall-ordering bandit and off-policy evaluation (design models 5–6) remain droppable stretch items.

The trick that makes it measurable: the simulator generates every consumer with a hidden `consumer_key`, strips it from all three silos, and keeps it in a private crosswalk. Entity-resolution accuracy is scored against that ground truth — the silo unification is *provably* correct, with numbers.

```text
             simulation/ (local Python, seeded, --scale dial)
                  │            │            │
          ┌───────▼──┐   ┌─────▼─────┐  ┌───▼──────────┐
          │ AWS S3   │   │ Neon      │  │ BigQuery     │
          │ auction  │   │ Postgres  │  │ marketing    │
          │ lake     │   │ CRM       │  │ exports      │
          └───────┬──┘   └─────┬─────┘  └───┬──────────┘
                  └──────┬─────┴─────┬──────┘
                         ▼           ▼
              DuckDB/BigQuery + dbt + Splink (unification)
                         │
                         ▼
        Notebooks · ML training · Plotly dashboards · public site
```

Full design: [docs/design.md](docs/design.md) · Calibration spec: [docs/calibration_spec.md](docs/calibration_spec.md) · Current state and guidance: [project_guide.md](project_guide.md)

## Repository map

| Path | Contents |
| --- | --- |
| `meta/` | Global track: charter, conventions, provenance, logs, knowledge graph |
| `CLAUDE.md` | Agent entry point (auto-loaded by Claude Code) |
| `project_guide.md` | Local-track working companion: current state + phase guidance |
| `docs/` | Design doc (the local seed) + calibration spec |
| `simulation/` | Consumer/lead/waterfall/marketing generators + silo fracturing (Phase 1) |
| `infra/` | Cloud setup scripts: buckets, IAM policies, budget alarms (Phase 0) |
| `silos/` | Loaders that deploy fractured outputs to S3 / Postgres / BigQuery (Phase 2) |
| `warehouse/` | dbt project: staging → entity resolution → wide denormalized marts (Phases 3–4, D10) |
| `er/` | Splink pipeline + scoring vs. the hidden crosswalk (Phase 3) |
| `analysis/` | Notebooks and dashboard exports (Phase 4) |
| `models/` | ML training, model cards, strategy memo (Phases 5–6) |
| `site/` | Quarto case-study site (Phase 7). The author's profile and resume live in the portfolio repository, [JordanBeary.github.io](https://github.com/JordanBeary/JordanBeary.github.io) |

## Quickstart

```bash
pip install -e ".[dev]"
python -m simulation --scale 0.01 --seed 42   # 1% scale run in ~2 s; --scale 1.0 takes ~2.5 min
```

Or open in GitHub Codespaces — the devcontainer pre-installs everything.

## Status

Every phase gates on its local exit criteria (design doc, Section 9) **and** the global exit criterion (logs current, graph validates, provenance recorded — [meta/charter.md](meta/charter.md), Section 2).

- [x] Phase 0 — repo, devcontainer, design doc, cloud silos provisioned (S3 · Neon · BigQuery), budget alarms live
- [x] Phase 0.5 — harness build: `meta/` scaffold, logs seeded, provenance backfilled, knowledge graph + CI validation, naming and identifier corrections
- [x] Phase 1 — simulation engine, calibrated vs. iPinYou / LendingClub / Criteo and the author's industry tables (C18, C19); one seeded command; 48 engine tests
- [x] Phase 2 — silo deployment (S3, Neon, BigQuery), silo audit memo, cost receipts
- [x] Phase 3 — unification: dbt staging + Splink ER scored against the hidden crosswalk (link F1 0.879, dedupe F1 0.873, band 0.8–0.9 per D8/P-010; 95.3% of auction events consumer-joinable)
- [x] Phase 4 — wide analytics marts + six static dashboards; all nine silo-audit questions answered
- [x] Phase 5 — ML models 1–4 with cards and static evaluation reports (D11 ratified 2026-09-02): calibrated sale propensity, a censored winning-price landscape, replay-based floor optimization, uplift on the randomized holdout
- [x] Phase 6 — floor policy validated by re-running the engine at the recommended schedule: +2.98% revenue per lead over five seeds (range +2.88% to +3.15%), break-even buyer bid shading about 0.19 (D18 ratified 2026-09-02) + strategy memo
- [ ] Phase 7 — site: first release live 2026-08-28, repositioned per D14 (ratified 2026-09-02) with the profile and resume moved to the portfolio repository (D15); deploy of the reframed site, then publish-on-push, domain and peer review outstanding

> **Note:** The marketplace is fictional and deliberately unnamed. All data is simulated, calibrated only to public datasets (iPinYou RTB, LendingClub, Criteo Uplift).
