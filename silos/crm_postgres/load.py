"""Deploy the CRM silo: create the leads table on Neon Postgres and COPY the CSV.

Usage:
    .venv/bin/python silos/crm_postgres/load.py [--source-dir data/generated/crm]

Reads CRM_DATABASE_URL from .env. Idempotent: drops and recreates the table,
then streams the CSV via COPY. Prints heap/index/total sizes afterward — the
free-tier fit evidence the silo audit memo records.

Free-tier fit (D6, ratified 2026-08-14): the full-column table measures
~0.62 GB against Neon's ~0.5 GB free tier, so the deployed table diverges
from the generated export in exactly two ways, both applied in-stream here
while the CSV and crm/schema.sql stay untouched as fracture artifacts:

- street_address and city are not loaded (13.3% of row bytes; neither is in
  the C17e entity-resolution ladder of names/phones/zips);
- email_sha256 is stored as 32-byte BYTEA instead of hex CHAR(64) (27.4% of
  row bytes at 65 bytes stored; BYTEA halves it, losslessly — Phase 3
  staging re-encodes with encode(email_sha256, 'hex')).

Projected deployed size: ~0.48 GB. Re-measure after every load; if it
exceeds the tier, the D6 fallback is the paid tier, not further trimming.
"""

from __future__ import annotations

import argparse
import csv
import io
import os
import sys
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

from simulation.config import SimConfig

REPO_ROOT = Path(__file__).resolve().parents[2]

# Deployed DDL (D6): crm/schema.sql minus street_address/city, hash as BYTEA.
DEPLOYED_DDL = """
-- CRM silo: entity-grain lead table (one mutable row per lead).
-- Timestamps are naive US/Pacific wall-clock, as exported by the CRM vendor.
-- Deployed shape per decision D6 (free-tier fit): street_address/city not
-- loaded; email_sha256 stored as BYTEA (hex-decoded from the export).
CREATE TABLE leads (
    lead_id           BIGINT PRIMARY KEY,
    email_sha256      BYTEA NOT NULL,
    first_name        TEXT,
    last_name         TEXT,
    phone             TEXT,
    state             CHAR(2),
    zip_code          CHAR(5),
    loan_amount       INTEGER,
    purpose           TEXT,
    fico_band         TEXT,
    employment_length TEXT,
    annual_income     INTEGER,
    submitted_at      TIMESTAMP,
    status            TEXT,
    updated_at        TIMESTAMP
)
"""

# Export CSV column order (crm/schema.sql); the two dropped columns.
EXPORT_COLUMNS = [
    "lead_id", "email_sha256", "first_name", "last_name", "phone",
    "street_address", "city", "state", "zip_code", "loan_amount", "purpose",
    "fico_band", "employment_length", "annual_income", "submitted_at",
    "status", "updated_at",
]
DROPPED = {"street_address", "city"}


class TransformedCSV(io.RawIOBase):
    """File-like view of the export CSV with the D6 transform applied row-wise.

    Streams for COPY FROM STDIN: drops the D6 columns and rewrites the hex
    hash as Postgres hex-format BYTEA input (\\x prefix), without ever
    materializing a second 0.5 GB file.
    """

    def __init__(self, csv_path: Path):
        self._file = open(csv_path, newline="")
        reader = csv.reader(self._file)
        header = next(reader)
        if header != EXPORT_COLUMNS:
            raise ValueError(f"unexpected CSV header: {header}")
        self._keep = [i for i, c in enumerate(EXPORT_COLUMNS) if c not in DROPPED]
        self._email_idx = EXPORT_COLUMNS.index("email_sha256")
        self._reader = reader
        self._buffer = b""
        # One reusable StringIO + writer keeps per-row overhead low across
        # the 2.3M-row stream.
        self._row_io = io.StringIO()
        self._row_writer = csv.writer(self._row_io, lineterminator="\n")

    def readable(self) -> bool:
        return True

    def read(self, size: int = -1) -> bytes:
        target = float("inf") if size < 0 else size
        buf = self._buffer
        while len(buf) < target:
            row = next(self._reader, None)
            if row is None:
                break
            row[self._email_idx] = "\\x" + row[self._email_idx]
            self._row_io.seek(0)
            self._row_io.truncate()
            self._row_writer.writerow([row[i] for i in self._keep])
            buf += self._row_io.getvalue().encode()
        if size < 0 or len(buf) <= size:
            self._buffer = b""
            return buf
        self._buffer = buf[size:]
        return buf[:size]

    def close(self) -> None:
        self._file.close()
        super().close()


def main() -> None:
    cfg = SimConfig()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-dir", type=Path, default=REPO_ROOT / cfg.out_dir / "crm",
        help="directory holding leads.csv",
    )
    args = parser.parse_args()

    csv_path = args.source_dir / "leads.csv"
    if not csv_path.is_file():
        sys.exit(f"missing {csv_path}; run the simulation first")

    load_dotenv(REPO_ROOT / ".env")
    conn = psycopg2.connect(os.environ["CRM_DATABASE_URL"])
    conn.autocommit = True
    cur = conn.cursor()

    # Drop-and-recreate so the deployed schema always matches this loader;
    # the silo is a full snapshot, not an increment.
    cur.execute("DROP TABLE IF EXISTS leads")
    cur.execute(DEPLOYED_DDL)

    src = TransformedCSV(csv_path)
    try:
        cur.copy_expert("COPY leads FROM STDIN WITH (FORMAT csv)", src)
    finally:
        src.close()

    # Verification: row count and on-disk size (the D6 free-tier evidence).
    cur.execute("SELECT count(*) FROM leads")
    rows = cur.fetchone()[0]
    cur.execute(
        """SELECT pg_table_size('leads'), pg_indexes_size('leads'),
                  pg_total_relation_size('leads'),
                  pg_database_size(current_database())"""
    )
    table_b, index_b, total_b, db_b = cur.fetchone()
    print(f"loaded {rows:,} rows from {csv_path}")
    print(f"table {table_b / 1e9:.3f} GB + indexes {index_b / 1e9:.3f} GB "
          f"= {total_b / 1e9:.3f} GB total; database logical size {db_b / 1e9:.3f} GB")
    conn.close()


if __name__ == "__main__":
    main()
