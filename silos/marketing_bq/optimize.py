"""Partition and cluster the messages table; record the bytes-scanned receipt.

Usage:
    .venv/bin/python silos/marketing_bq/optimize.py

Runs a representative analytical query (one channel, one month) against the
unpartitioned `messages` table as loaded by load.py, rewrites the table
partitioned by DATE(sent_at) and clustered by channel, reruns the identical
query, and writes both bytes-scanned figures to benchmark_receipt.json.
These receipts feed the FinOps write-up and the design Section 5.3 100x
extrapolation. Query cache is disabled so both runs bill real bytes.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import bigquery

REPO_ROOT = Path(__file__).resolve().parents[2]
RECEIPT_PATH = Path(__file__).resolve().parent / "benchmark_receipt.json"

# Representative slice query: campaign performance for one channel in one
# month -- the shape Phase 4 dashboards will run constantly.
BENCHMARK_SQL = """
SELECT campaign_id,
       COUNT(*) AS sent,
       COUNTIF(opened_at IS NOT NULL) AS opened,
       COUNTIF(clicked_at IS NOT NULL) AS clicked
FROM `{table}`
WHERE channel = 'sms'
  AND sent_at >= DATETIME '2025-10-01'
  AND sent_at <  DATETIME '2025-11-01'
GROUP BY campaign_id
ORDER BY campaign_id
"""


def run_benchmark(client: bigquery.Client, table_id: str) -> dict:
    job = client.query(
        BENCHMARK_SQL.format(table=table_id),
        job_config=bigquery.QueryJobConfig(use_query_cache=False),
    )
    rows = list(job.result())
    return {
        "table": table_id,
        "bytes_processed": job.total_bytes_processed,
        "bytes_billed": job.total_bytes_billed,
        "result_rows": len(rows),
    }


def main() -> None:
    load_dotenv(REPO_ROOT / ".env")
    project = os.environ["GCP_PROJECT_ID"]
    dataset = os.environ["BQ_MARKETING_DATASET"]
    client = bigquery.Client(project=project)
    table_id = f"{project}.{dataset}.messages"

    # Guard: skip the rewrite if the table is already partitioned, so re-runs
    # do not pay the full-table scan again.
    table = client.get_table(table_id)
    if table.time_partitioning is not None:
        print(f"{table_id} already partitioned; benchmarking current state only")
        after = run_benchmark(client, table_id)
        print(json.dumps(after, indent=2))
        return

    before = run_benchmark(client, table_id)
    print(f"before: {before['bytes_processed']:,} bytes scanned")

    # Rewrite via create-new / drop / rename: BigQuery refuses CREATE OR
    # REPLACE with a different partitioning spec. One full-table scan
    # (~1 GB, well inside the 1 TiB free query tier), then the optimized
    # layout is the silo's end state.
    staging_id = f"{table_id}_partitioned"
    client.query(f"""
        CREATE OR REPLACE TABLE `{staging_id}`
        PARTITION BY DATE(sent_at)
        CLUSTER BY channel
        AS SELECT * FROM `{table_id}`
    """).result()
    client.delete_table(table_id)
    client.query(
        f"ALTER TABLE `{staging_id}` RENAME TO `{table_id.rsplit('.', 1)[1]}`"
    ).result()
    print("rewritten: PARTITION BY DATE(sent_at) CLUSTER BY channel")

    after = run_benchmark(client, table_id)
    print(f"after:  {after['bytes_processed']:,} bytes scanned")

    receipt = {
        "benchmark_sql": BENCHMARK_SQL.strip(),
        "before": before,
        "after": after,
        "reduction_factor": round(
            before["bytes_processed"] / max(after["bytes_processed"], 1), 1
        ),
    }
    RECEIPT_PATH.write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"receipt written to {RECEIPT_PATH}")


if __name__ == "__main__":
    main()
