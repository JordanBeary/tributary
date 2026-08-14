"""Deploy the marketing silo: load the three JSONL exports into BigQuery.

Usage:
    .venv/bin/python silos/marketing_bq/load.py [--source-dir data/generated/marketing]

Reads GCP_PROJECT_ID and BQ_MARKETING_DATASET from .env; auth is ADC.
Loads each table with an explicit schema (no autodetect) and
WRITE_TRUNCATE, so re-runs replace the silo snapshot. Load jobs are free
in BigQuery, so this costs storage only.

Timestamps are loaded as DATETIME, not TIMESTAMP: the fracture stage
exports naive wall-clock times (a deliberate silo pathology, design.md
Section 2.3), and DATETIME preserves them without asserting a zone.
Tables land unpartitioned, as a vendor export would; optimize.py applies
partitioning/clustering and records the before/after bytes-scanned receipt.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import bigquery

from simulation.config import SimConfig

REPO_ROOT = Path(__file__).resolve().parents[2]

# Explicit schemas for the three fracture outputs (see simulation/fracture.py).
SCHEMAS: dict[str, list[bigquery.SchemaField]] = {
    "contacts": [
        bigquery.SchemaField("contact_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("first_name", "STRING"),
        bigquery.SchemaField("last_name", "STRING"),
        bigquery.SchemaField("phone", "STRING"),
        bigquery.SchemaField("state", "STRING"),
        bigquery.SchemaField("zip_code", "STRING"),
        bigquery.SchemaField("acquisition_channel", "STRING"),
        bigquery.SchemaField("engagement_segment", "INT64"),
        bigquery.SchemaField("in_holdout", "BOOL"),
        bigquery.SchemaField("acquired_at", "DATETIME"),
        bigquery.SchemaField("converted", "BOOL"),
    ],
    "messages": [
        bigquery.SchemaField("message_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("contact_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("campaign_id", "STRING"),
        bigquery.SchemaField("channel", "STRING"),
        bigquery.SchemaField("sent_at", "DATETIME"),
        bigquery.SchemaField("opened_at", "DATETIME"),
        bigquery.SchemaField("clicked_at", "DATETIME"),
    ],
    "channel_spend": [
        bigquery.SchemaField("month", "STRING"),
        bigquery.SchemaField("channel", "STRING"),
        bigquery.SchemaField("new_contacts", "INT64"),
        # visits/impressions are counts, but the export writes them as
        # float-or-null (nullable-column artifact, kept as exported), and
        # BigQuery will not coerce "98105.0" into INT64.
        bigquery.SchemaField("visits", "FLOAT64"),
        bigquery.SchemaField("impressions", "FLOAT64"),
        bigquery.SchemaField("spend_usd", "FLOAT64"),
    ],
}


def main() -> None:
    cfg = SimConfig()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-dir", type=Path, default=REPO_ROOT / cfg.out_dir / "marketing",
        help="directory holding contacts/messages/channel_spend JSONL",
    )
    parser.add_argument(
        "--table", choices=list(SCHEMAS), default=None,
        help="load a single table instead of all three",
    )
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")
    project = os.environ["GCP_PROJECT_ID"]
    dataset = os.environ["BQ_MARKETING_DATASET"]
    client = bigquery.Client(project=project)

    tables = {args.table: SCHEMAS[args.table]} if args.table else SCHEMAS
    for table_name, schema in tables.items():
        source = args.source_dir / f"{table_name}.jsonl"
        if not source.is_file():
            sys.exit(f"missing {source}; run the simulation first")

        job_config = bigquery.LoadJobConfig(
            source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
            schema=schema,
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        )
        table_id = f"{project}.{dataset}.{table_name}"
        with open(source, "rb") as f:
            job = client.load_table_from_file(f, table_id, job_config=job_config)
        job.result()  # blocks until the load job finishes

        table = client.get_table(table_id)
        print(f"{table_id}: {table.num_rows:,} rows, "
              f"{table.num_bytes / 1e9:.3f} GB logical")


if __name__ == "__main__":
    main()
