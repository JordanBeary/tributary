"""Refresh local Parquet exports of the BigQuery marketing silo.

Usage:
    .venv/bin/python warehouse/export_marketing.py

Design Section 4.1: DuckDB unifies locally against S3 and Postgres directly,
but reads the BigQuery silo from local exports. This script is that export:
each marketing table is downloaded once (BigQuery Storage read; free-tier
scale) into git-ignored data/silo_exports/marketing/, where the dbt staging
sources point. Re-run only after the silo itself is reloaded.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import bigquery

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPORT_DIR = REPO_ROOT / "data" / "silo_exports" / "marketing"
TABLES = ["contacts", "messages", "channel_spend"]


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")
    project = os.environ["GCP_PROJECT_ID"]
    dataset = os.environ["BQ_MARKETING_DATASET"]
    client = bigquery.Client(project=project)
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    for name in TABLES:
        table = client.get_table(f"{project}.{dataset}.{name}")
        # Arrow round-trip keeps BigQuery types (DATETIME stays naive).
        arrow = client.list_rows(table).to_arrow()
        out = EXPORT_DIR / f"{name}.parquet"
        import pyarrow.parquet as pq

        pq.write_table(arrow, out, compression="zstd")
        print(f"{name}: {arrow.num_rows:,} rows -> {out} "
              f"({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
