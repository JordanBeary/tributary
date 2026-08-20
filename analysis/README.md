# analysis

Notebooks and dashboard exports.

- `profiling/` -- calibration notebooks (docs/calibration_spec.md Section 5); they produce the `simulation/params/` artifacts.
- `dashboards/` -- Phase 4 (design Section 7.3, D10). `build_dashboards.py` reads the dbt marts in `warehouse/tributary.duckdb` and writes six static Plotly pages to `out/` plus identity-free aggregate JSON to `data/` (`build_receipt.json` records build times and mart sizes). Every panel is tagged with the silo-audit question it answers (docs/silo_audit.md Sections 2 and 6). The pages load plotly.js from the CDN and are the cached artifacts the site (Phase 7) embeds -- no live compute.

Run: `.venv/bin/python analysis/dashboards/build_dashboards.py` after `dbt build` (or `dbt build --select marts`) in `warehouse/`.
