# warehouse

dbt project (dbt-duckdb): unifies the three cloud silos locally per design Section 4.1 — staging (per-silo cleaning and semantic alignment) → intermediate (entity-resolution outputs, Phase 3) → marts (Phase 4).

How the silos are read (profiles.yml):

- Auction: Parquet straight from S3 over httpfs (least-privilege `tributary` AWS profile via credential chain).
- CRM: Neon Postgres attached read-only as database `crm` (connection string from the repo `.env`).
- Marketing: local Parquet exports of the BigQuery tables — refresh with `.venv/bin/python warehouse/export_marketing.py` (writes git-ignored `data/silo_exports/marketing/`).

Run from this directory with the repo `.env` exported:

```sh
set -a; . ../.env; set +a
../.venv/bin/dbt build          # models + tests
```

Staging conventions: all timestamps land as naive UTC (`*_utc` columns) — the auction silo logs UTC natively, CRM naive US/Pacific and marketing naive US/Eastern are localized via ICU; the CRM's DST fall-back ambiguity is inherent to the silo and documented in `stg_crm__leads`. Tests encode the *intended* pathologies (duplicate consumers stay duplicated; `lead_id` is unique, consumers are not) — a test that "fixes" a pathology is wrong.

The local database file (`warehouse/tributary.duckdb`) is a build artifact, git-ignored; `dbt build` regenerates it from the live silos.
