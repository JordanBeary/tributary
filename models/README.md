# models

Phase 5 ML workstream (design.md Section 8, models 1-4) and, in Phase 6, the
optimization strategy memo. Everything trains on the unified warehouse marts
(`warehouse/tributary.duckdb`, D10) — never on staging tables or simulation
outputs — and evaluates on a temporal split (D11).

- `common.py` — the shared feature contract (auction-time features, explicit
  leakage-exclusion list), C19 recency buckets, temporal split, mart loaders.
- `report.py` — shared evaluation-page conventions (the Phase 4 dashboard
  look: validated palette, static Plotly HTML, plotly.js from the CDN).
- `tobit.py` — left-censored Gaussian (Tobit) objective for LightGBM;
  gradient-checked in `tests/test_models.py`.
- `train_sale_propensity.py` — model 1: calibrated P(sold) + P(tier | sold).
- `train_price_landscape.py` — model 2: tier-ladder survival landscape
  (hazard x price), with the Tobit fitted as a documented specification test.
- `optimize_floors.py` — model 3: counterfactual replay of logged waterfalls
  under candidate reserve schedules; per-tier grid/coordinate descent.
- `train_uplift.py` — model 4: cross-fitted T-learner (logistic per arm) on
  the randomized nurture experiment; Qini/AUUC vs the injected heterogeneity.
- `cards/` — one-page model cards (committed).
- `out/` — metrics JSON + static evaluation reports (committed); trained
  model binaries in `out/boosters/` (git-ignored; reproducible).

Run order is irrelevant (each script is self-contained). Rebuild all:

    .venv/bin/python models/train_sale_propensity.py
    .venv/bin/python models/train_price_landscape.py
    .venv/bin/python models/optimize_floors.py
    .venv/bin/python models/train_uplift.py

Tests: `.venv/bin/pytest tests/test_models.py` (pure math + contracts; no
warehouse needed).
