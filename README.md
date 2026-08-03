# Tributary

**A dual-track project: an end-to-end data science build, and the working record of a human directing AI agents to produce it.**

## The two tracks

**The global track (primary)** is the working method itself: the harness that makes AI agents more effective than out-of-the-box, transparent decomposition of human versus agent contribution, and an honest log of corrections, decisions, and steering prompts. It lives in [meta/](meta/) — start with the [charter](meta/charter.md), then the [intervention log](meta/logs/interventions.md) and [provenance ledger](meta/provenance.md). The method is the exhibit; the build below is the demonstration payload.

**The local track** is the build: Tributary simulates the data environment of a fictional two-sided lead-generation marketplace that sells personal-loan leads through a 6-tier sequential waterfall auction. Its operational data is deliberately fractured into three architecturally real silos (S3 Parquet lake, transactional Postgres, BigQuery exports), then unified with entity resolution and dimensional modeling, and finally optimized with ML: censored price models, reserve-price simulation, uplift modeling, and a waterfall-ordering bandit.

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
| `warehouse/` | dbt project: staging → entity resolution → star-schema marts (Phases 3–4) |
| `er/` | Splink pipeline + scoring vs. the hidden crosswalk (Phase 3) |
| `analysis/` | Notebooks and dashboard exports (Phase 4) |
| `models/` | ML training, model cards, strategy memo (Phases 5–6) |
| `site/` | Quarto site (Phase 7) |

## Quickstart

```bash
pip install -e ".[dev]"
python -m simulation --scale 0.01 --seed 42   # 1% scale dev run (Phase 1, WIP)
```

Or open in GitHub Codespaces — the devcontainer pre-installs everything.

## Status

Every phase gates on its local exit criteria (design doc, Section 9) **and** the global exit criterion (logs current, graph validates, provenance recorded — [meta/charter.md](meta/charter.md), Section 2).

- [x] Phase 0 — repo, devcontainer, design doc, cloud silos provisioned (S3 · Neon · BigQuery), budget alarms live
- [x] Phase 0.5 — harness build: `meta/` scaffold, logs seeded, provenance backfilled, knowledge graph + CI validation, naming and identifier corrections
- [ ] Phase 1 — simulation engine + calibration vs. iPinYou / LendingClub / Criteo
- [ ] Phase 2 — silo deployment (S3, Neon, BigQuery)
- [ ] Phase 3 — unification: dbt staging + Splink ER (target F1 ≥ 0.9)
- [ ] Phase 4 — analytics marts + dashboards
- [ ] Phase 5 — ML models 1–4
- [ ] Phase 6 — floor optimization + bandit + strategy memo
- [ ] Phase 7 — website & launch

> **Note:** The marketplace is fictional and deliberately unnamed. All data is simulated, calibrated only to public datasets (iPinYou RTB, LendingClub, Criteo Uplift).
