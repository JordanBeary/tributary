# silos

Loaders that deploy the fracture outputs (`data/generated/`) to the three cloud silos (Phase 2). Each is idempotent: re-running replaces the silo snapshot. All read config from `.env`; none ever touches `data/private/` (the s3 loader refuses to run if a crosswalk artifact is anywhere under its source tree).

| Loader | Destination | Run |
| --- | --- | --- |
| `s3_lake/load.py` | `s3://$TRIBUTARY_S3_BUCKET/auction/` (Hive-partitioned Parquet) | `.venv/bin/python silos/s3_lake/load.py [--dry-run]` |
| `crm_postgres/load.py` | Neon Postgres `leads` table (`CRM_DATABASE_URL`) | `.venv/bin/python silos/crm_postgres/load.py` |
| `marketing_bq/load.py` | `$GCP_PROJECT_ID.$BQ_MARKETING_DATASET.{contacts,messages,channel_spend}` | `.venv/bin/python silos/marketing_bq/load.py [--table X]` |
| `marketing_bq/optimize.py` | partitions/clusters `messages`; writes `benchmark_receipt.json` | `.venv/bin/python silos/marketing_bq/optimize.py` |

The as-deployed state, per-silo capabilities, and cost receipts are recorded in the silo audit memo, `docs/silo_audit.md`.
