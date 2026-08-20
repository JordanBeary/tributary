"""Entity resolution: link CRM leads to marketing contacts with Splink.

Usage:
    .venv/bin/python er/link_crm_marketing.py

The two silos share no key by construction (sha256 vs md5 email hashes,
C17e): the linkage signal is names, phones, and zips, corrupted per C7
(nicknames, new phones, typos). Fellegi-Sunter model on DuckDB per design
Section 7.2.

Reads the dbt-built staging tables from warehouse/tributary.duckdb, writes:
  - main_er.crm_contact_matches (pairwise predictions >= threshold, plus a
    best-match-per-lead selection) back into the same database;
  - er/models/crm_marketing_model.json (trained m/u parameters -- aggregate
    statistics only, safe to commit).

Scoring against the private crosswalk lives in er/score.py, not here: this
script never touches data/private/.
"""

from __future__ import annotations

from pathlib import Path

import argparse

import duckdb
from splink import DuckDBAPI, Linker, SettingsCreator, block_on
import splink.comparison_library as cl

REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = REPO_ROOT / "warehouse" / "tributary.duckdb"
MODEL_PATH = Path(__file__).resolve().parent / "models" / "crm_marketing_model.json"
THRESHOLD = 0.5


def connect(local: bool):
    """warehouse DB + staging views (default), or a scratch DB over the local
    fracture outputs (--local, for D8 dial tuning without touching the cloud)."""
    import duckdb as _duck
    if not local:
        con = _duck.connect(str(DB_PATH))
        con.execute("CREATE SCHEMA IF NOT EXISTS main_er")
        return con
    con = _duck.connect(str(REPO_ROOT / "data" / "tuning.duckdb"))
    con.execute("CREATE SCHEMA IF NOT EXISTS main_er")
    gen = REPO_ROOT / "data" / "generated"
    con.execute(f"""
        CREATE OR REPLACE VIEW local_crm AS
        SELECT lead_id, email_sha256, first_name, last_name, phone,
               state, zip_code
        FROM read_csv('{gen}/crm/leads.csv')
    """)
    con.execute(f"""
        CREATE OR REPLACE VIEW local_mkt AS
        SELECT contact_id, first_name, last_name, phone, state, zip_code
        FROM read_json('{gen}/marketing/contacts.jsonl')
    """)
    return con


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--local", action="store_true",
                    help="read local fracture outputs (dial tuning)")
    args = ap.parse_args()
    con = connect(args.local)

    # Unified input views: Splink needs a shared schema and a unique_id.
    src_crm = "local_crm" if args.local else "main_staging.stg_crm__leads"
    src_mkt = "local_mkt" if args.local else "main_staging.stg_marketing__contacts"
    con.execute(f"""
        CREATE OR REPLACE VIEW er_in_crm AS
        SELECT lead_id AS unique_id, first_name, last_name, phone, zip_code, state
        FROM {src_crm}
    """)
    src_crm = "local_crm" if args.local else "main_staging.stg_crm__leads"
    src_mkt = "local_mkt" if args.local else "main_staging.stg_marketing__contacts"
    con.execute(f"""
        CREATE OR REPLACE VIEW er_in_mkt AS
        SELECT contact_id AS unique_id, first_name, last_name, phone, zip_code, state
        FROM {src_mkt}
    """)

    settings = SettingsCreator(
        link_type="link_only",
        # Prediction blocking: three overlapping passes so each C7 corruption
        # mode still has a surviving block (new phone -> name+zip blocks;
        # nickname -> phone / surname+zip blocks; typo'd surname -> phone /
        # forename+zip blocks).
        blocking_rules_to_generate_predictions=[
            block_on("phone"),
            block_on("last_name", "zip_code"),
            block_on("first_name", "zip_code"),
        ],
        comparisons=[
            cl.JaroWinklerAtThresholds("first_name", [0.92, 0.8]),
            cl.JaroWinklerAtThresholds("last_name", [0.92, 0.8]),
            cl.ExactMatch("phone"),
            cl.ExactMatch("zip_code"),
            cl.ExactMatch("state"),
        ],
        retain_intermediate_calculation_columns=False,
    )

    linker = Linker(
        ["er_in_crm", "er_in_mkt"],
        settings,
        db_api=DuckDBAPI(connection=con),
        input_table_aliases=["crm", "mkt"],
    )

    # Training: lambda from a high-precision deterministic rule, u from
    # random sampling, m via EM on two complementary blocks (each trains
    # the parameters its blocking key holds fixed).
    linker.training.estimate_probability_two_random_records_match(
        [block_on("phone", "first_name", "last_name")], recall=0.8
    )
    linker.training.estimate_u_using_random_sampling(max_pairs=1e7)
    linker.training.estimate_parameters_using_expectation_maximisation(
        block_on("phone")
    )
    linker.training.estimate_parameters_using_expectation_maximisation(
        block_on("last_name", "zip_code")
    )

    predictions = linker.inference.predict(threshold_match_probability=THRESHOLD)

    # Persist pairwise predictions and a best-match-per-lead view (a CRM
    # lead has at most one true contact; a contact may hold many leads --
    # duplicate applications collapse to one marketing identity).
    con.execute(f"""
        CREATE OR REPLACE TABLE main_er.crm_contact_matches AS
        SELECT unique_id_l AS crm_lead_id,
               unique_id_r AS contact_id,
               match_probability,
               match_weight
        FROM {predictions.physical_name}
    """)
    con.execute("""
        CREATE OR REPLACE TABLE main_er.crm_contact_best_match AS
        SELECT crm_lead_id, contact_id, match_probability
        FROM (SELECT *, row_number() OVER (
                  PARTITION BY crm_lead_id
                  ORDER BY match_probability DESC, contact_id) AS rk
              FROM main_er.crm_contact_matches)
        WHERE rk = 1
    """)

    linker.misc.save_model_to_json(str(MODEL_PATH), overwrite=True)

    n_pairs = con.sql("SELECT count(*) FROM main_er.crm_contact_matches").fetchone()[0]
    n_best = con.sql("SELECT count(*) FROM main_er.crm_contact_best_match").fetchone()[0]
    print(f"pairs >= {THRESHOLD}: {n_pairs:,}; leads with a best match: {n_best:,}")
    print(f"model saved to {MODEL_PATH}")
    con.close()


if __name__ == "__main__":
    main()
