"""Link auction lead_uuids to CRM leads via payload + submission-time proximity.

Usage:
    .venv/bin/python er/link_auction_crm.py [--local]

No key crosses this boundary by construction (C17a): the linkage signal is
the offer payload the bid_request rows carry (state, loan amount, purpose,
FICO band -- observed to agree exactly for true pairs) plus the tight lag
between CRM submission and first auction event (0-540 s at this
marketplace, shifted by -3600 s for CRM rows inside the DST fall-back hour,
whose staged UTC is off by one hour -- the C17f pathology, accommodated
rather than repaired). Deterministic SQL, no probabilistic model: with an
exact composite payload and a nine-minute window, nearest-in-time is the
right tool, and its failures (payload doppelgangers inside the window) are
honest ambiguity.

Writes main_er.auction_crm_matches (lead_uuid -> crm_lead_id). Scoring
against the crosswalk lives in er/score.py.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = REPO_ROOT / "warehouse" / "tributary.duckdb"

# Lag acceptance window and its center (seconds); see module docstring.
LAG_MIN, LAG_MAX, LAG_CENTER = -3600, 540, 420


def connect(local: bool) -> duckdb.DuckDBPyConnection:
    if not local:
        con = duckdb.connect(str(DB_PATH))
    else:
        con = duckdb.connect(str(REPO_ROOT / "data" / "tuning.duckdb"))
    con.execute("CREATE SCHEMA IF NOT EXISTS main_er")
    return con


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--local", action="store_true",
                    help="read local fracture outputs (dial tuning)")
    args = ap.parse_args()
    con = connect(args.local)

    if args.local:
        gen = REPO_ROOT / "data" / "generated"
        con.execute(f"""
            CREATE OR REPLACE VIEW link_events AS
            SELECT lead_uuid, event_type, event_at AS event_at_utc, state,
                   cast(loan_amount AS integer) AS loan_amount, purpose, fico_band
            FROM read_parquet('{gen}/auction/event_date=*/*.parquet',
                              hive_partitioning = true)
        """)
        con.execute(f"""
            CREATE OR REPLACE VIEW link_crm AS
            SELECT lead_id, state, loan_amount, purpose, fico_band,
                   timezone('UTC', timezone('America/Los_Angeles',
                                            submitted_at)) AS submitted_at_utc
            FROM read_csv('{gen}/crm/leads.csv')
        """)
        src_ev, src_crm = "link_events", "link_crm"
    else:
        src_ev = "main_staging.stg_auction__events"
        src_crm = "main_staging.stg_crm__leads"

    # One row per lead_uuid: first bid_request carries the payload and the
    # auction start time. Candidates share the exact payload and land inside
    # the lag window; nearest-to-center wins, ties broken by lead_id for
    # determinism.
    con.execute(f"""
        CREATE OR REPLACE TABLE main_er.auction_crm_matches AS
        WITH first_ev AS (
            SELECT lead_uuid, min(event_at_utc) AS first_at,
                   any_value(state) AS state, any_value(loan_amount) AS loan_amount,
                   any_value(purpose) AS purpose, any_value(fico_band) AS fico_band
            FROM {src_ev}
            WHERE event_type = 'bid_request'
            GROUP BY lead_uuid),
        candidates AS (
            SELECT f.lead_uuid, c.lead_id AS crm_lead_id,
                   date_diff('second', c.submitted_at_utc, f.first_at) AS lag_s,
                   row_number() OVER (
                       PARTITION BY f.lead_uuid
                       ORDER BY abs(date_diff('second', c.submitted_at_utc,
                                              f.first_at) - {LAG_CENTER}),
                                c.lead_id) AS rk
            FROM first_ev f
            JOIN {src_crm} c
              ON c.state = f.state
             AND c.loan_amount = f.loan_amount
             AND c.purpose = f.purpose
             AND c.fico_band = f.fico_band
             AND date_diff('second', c.submitted_at_utc, f.first_at)
                 BETWEEN {LAG_MIN} AND {LAG_MAX})
        SELECT lead_uuid, crm_lead_id, lag_s
        FROM candidates WHERE rk = 1
    """)
    n, uuids = con.sql("""SELECT count(*), count(DISTINCT lead_uuid)
                          FROM main_er.auction_crm_matches""").fetchone()
    total = con.sql(f"SELECT count(DISTINCT lead_uuid) FROM {src_ev}").fetchone()[0]
    print(f"matched {n:,} lead_uuids of {total:,} ({n / total:.1%})")
    con.close()


if __name__ == "__main__":
    main()
