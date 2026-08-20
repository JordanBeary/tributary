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

The intermediate layer (`models/intermediate/`) consumes the ER pipeline's outputs (declared as the `main_er` source; written by the `er/` scripts) into the unification spine: `int_consumer_entities` (CRM lead -> consumer entity + best-match marketing contact) and `int_auction_consumer_map` (auction lead_uuid -> consumer entity). Marts (Phase 4) join through the spine.

Staging conventions: all timestamps land as naive UTC (`*_utc` columns) — the auction silo logs UTC natively, CRM naive US/Pacific and marketing naive US/Eastern are localized via ICU; the CRM's DST fall-back ambiguity is inherent to the silo and documented in `stg_crm__leads`. Tests encode the *intended* pathologies (duplicate consumers stay duplicated; `lead_id` is unique, consumers are not) — a test that "fixes" a pathology is wrong.

The marts layer (`models/marts/`, Phase 4, D10) is wide and denormalized per P-009: `fct_auction_events` (event grain, hydrated with payload, consumer entity, CRM outcome, marketing acquisition), `fct_leads` (one row per auctioned lead: auction outcome + CRM + marketing + last-touch campaign + consumer-entity sequence and duplicate-sale flags), `fct_marketing_contacts` (contact grain with post-ER applications and revenue), `fct_channel_month` (spend ledger joined to cohort revenue), and `dim_consumer` (resolved persons). Operating points (t=0.9 clusters, 30-day last-touch, 30-day duplicate window) are stated in the model headers. Rebuild the marts alone, without re-pulling the silos, with `dbt build --select marts` (~20 s); dashboards are built from them by `analysis/dashboards/build_dashboards.py`.

The local database file (`warehouse/tributary.duckdb`) is a build artifact, git-ignored; `dbt build` regenerates it from the live silos.
