"""Entity resolution: dedupe CRM leads into consumer clusters with Splink.

Usage:
    .venv/bin/python er/dedupe_crm.py

The same consumer appears as multiple lead_ids (repeat applications, ~1.6x
per consumer), and ~8% of applications are corrupted duplicates (C7:
nickname 40% / email typo 30% / new phone 20% / all three 10%). Clean
repeats share an email hash and are trivial; the corrupted ones are the
intended difficulty. Fellegi-Sunter dedupe on DuckDB.

Writes main_er.crm_dedupe_matches (pairwise predictions) and
er/models/crm_dedupe_model.json. Scoring lives in er/score.py.
"""

from __future__ import annotations

from pathlib import Path

import argparse

import duckdb
from splink import DuckDBAPI, Linker, SettingsCreator, block_on
import splink.comparison_library as cl

REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = REPO_ROOT / "warehouse" / "tributary.duckdb"
MODEL_PATH = Path(__file__).resolve().parent / "models" / "crm_dedupe_model.json"
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
    src_crm = "local_crm" if args.local else "main_staging.stg_crm__leads"
    src_mkt = "local_mkt" if args.local else "main_staging.stg_marketing__contacts"
    con.execute(f"""
        CREATE OR REPLACE VIEW er_in_crm_dedupe AS
        SELECT lead_id AS unique_id, email_sha256, first_name, last_name,
               phone, zip_code, state
        FROM {src_crm}
    """)

    settings = SettingsCreator(
        link_type="dedupe_only",
        # Each C7 corruption mode leaves at least one blocking key intact:
        # email typo -> phone / name+zip blocks; new phone -> email / name+zip;
        # nickname -> email / phone / surname+zip.
        blocking_rules_to_generate_predictions=[
            block_on("email_sha256"),
            block_on("phone"),
            block_on("last_name", "zip_code"),
            block_on("first_name", "zip_code"),
        ],
        comparisons=[
            cl.ExactMatch("email_sha256"),
            cl.JaroWinklerAtThresholds("first_name", [0.92, 0.8]),
            cl.JaroWinklerAtThresholds("last_name", [0.92, 0.8]),
            cl.ExactMatch("phone"),
            cl.ExactMatch("zip_code"),
            cl.ExactMatch("state"),
        ],
        retain_intermediate_calculation_columns=False,
    )

    linker = Linker(
        "er_in_crm_dedupe",
        settings,
        db_api=DuckDBAPI(connection=con),
    )

    linker.training.estimate_probability_two_random_records_match(
        [block_on("email_sha256")], recall=0.55
    )
    linker.training.estimate_u_using_random_sampling(max_pairs=1e7)
    # Two EM passes with complementary fixed keys, as in the link model.
    linker.training.estimate_parameters_using_expectation_maximisation(
        block_on("email_sha256")
    )
    linker.training.estimate_parameters_using_expectation_maximisation(
        block_on("last_name", "zip_code")
    )

    predictions = linker.inference.predict(threshold_match_probability=THRESHOLD)
    con.execute(f"""
        CREATE OR REPLACE TABLE main_er.crm_dedupe_matches AS
        SELECT unique_id_l AS lead_id_l,
               unique_id_r AS lead_id_r,
               match_probability, match_weight
        FROM {predictions.physical_name}
    """)
    linker.misc.save_model_to_json(str(MODEL_PATH), overwrite=True)

    n = con.sql("SELECT count(*) FROM main_er.crm_dedupe_matches").fetchone()[0]
    print(f"dedupe pairs >= {THRESHOLD}: {n:,}")
    print(f"model saved to {MODEL_PATH}")
    con.close()


if __name__ == "__main__":
    main()
