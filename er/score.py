"""Score ER predictions against the hidden crosswalk (design Section 2.4).

Usage:
    .venv/bin/python er/score.py

Reads the main_er prediction tables from the warehouse DuckDB and the
private crosswalk (data/private/ -- local only, never committed or
uploaded), and writes aggregate metrics to er/scorecard.json. The scorecard
contains counts and rates only; no identity data leaves data/private/.

Two tasks:
  - crm_marketing_link: every CRM lead maps to exactly one marketing
    contact; a predicted (lead, contact) pair is correct iff the crosswalk
    contains it. Selection: best match per lead.
  - crm_dedupe: pairs of CRM leads sharing a consumer_key. Recall is
    reported separately for corrupted pairs (at least one side is a C7
    duplicate -- the intended difficulty) and clean repeat-application
    pairs (same identity verbatim; easy by construction).
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = REPO_ROOT / "warehouse" / "tributary.duckdb"
CROSSWALK = REPO_ROOT / "data" / "private" / "crosswalk.parquet"
OUT_PATH = Path(__file__).resolve().parent / "scorecard.json"
THRESHOLDS = [0.5, 0.7, 0.9, 0.95, 0.99]


def score_link(con: duckdb.DuckDBPyConnection) -> dict:
    con.execute(f"""
        CREATE OR REPLACE TEMP VIEW truth_link AS
        SELECT crm_lead_id, contact_id
        FROM read_parquet('{CROSSWALK}')
        WHERE crm_lead_id IS NOT NULL
    """)
    n_truth = con.sql("SELECT count(*) FROM truth_link").fetchone()[0]
    results = []
    for t in THRESHOLDS:
        tp, pred = con.sql(f"""
            SELECT sum(hit), count(*) FROM (
                SELECT (t.crm_lead_id IS NOT NULL)::int AS hit
                FROM main_er.crm_contact_best_match p
                LEFT JOIN truth_link t
                  ON p.crm_lead_id = t.crm_lead_id
                 AND p.contact_id = t.contact_id
                WHERE p.match_probability >= {t})
        """).fetchone()
        tp = int(tp or 0)
        precision = tp / pred if pred else 0.0
        recall = tp / n_truth
        f1 = 2 * precision * recall / (precision + recall) if tp else 0.0
        results.append({
            "threshold": t, "predicted_pairs": pred, "true_positives": tp,
            "precision": round(precision, 4), "recall": round(recall, 4),
            "f1": round(f1, 4),
        })
        print(f"link   t>={t:<5} pred={pred:>9,} P={precision:.4f} "
              f"R={recall:.4f} F1={f1:.4f}")
    return {"task": "crm_marketing_link", "ground_truth_pairs": n_truth,
            "selection": "best_match_per_lead", "by_threshold": results}


def score_dedupe(con: duckdb.DuckDBPyConnection) -> dict:
    # True pairs: CRM leads sharing a consumer_key; a pair is "corrupted"
    # if either side is a C7 duplicate application.
    con.execute(f"""
        CREATE OR REPLACE TEMP VIEW truth_dedupe AS
        SELECT a.crm_lead_id AS lead_id_l, b.crm_lead_id AS lead_id_r,
               (a.is_duplicate OR b.is_duplicate) AS corrupted
        FROM read_parquet('{CROSSWALK}') a
        JOIN read_parquet('{CROSSWALK}') b
          ON a.consumer_key = b.consumer_key
         AND a.crm_lead_id < b.crm_lead_id
        WHERE a.crm_lead_id IS NOT NULL AND b.crm_lead_id IS NOT NULL
    """)
    n_truth, n_corr = con.sql(
        "SELECT count(*), sum(corrupted::int) FROM truth_dedupe").fetchone()
    results = []
    for t in THRESHOLDS:
        tp, pred, tp_corr = con.sql(f"""
            SELECT sum(hit), count(*),
                   sum(CASE WHEN corrupted THEN hit ELSE 0 END) FROM (
                SELECT (t.lead_id_l IS NOT NULL)::int AS hit, t.corrupted
                FROM main_er.crm_dedupe_matches p
                LEFT JOIN truth_dedupe t
                  ON least(p.lead_id_l, p.lead_id_r) = t.lead_id_l
                 AND greatest(p.lead_id_l, p.lead_id_r) = t.lead_id_r
                WHERE p.match_probability >= {t})
        """).fetchone()
        tp = int(tp or 0); tp_corr = int(tp_corr or 0)
        precision = tp / pred if pred else 0.0
        recall = tp / n_truth
        recall_corr = tp_corr / n_corr
        f1 = 2 * precision * recall / (precision + recall) if tp else 0.0
        results.append({
            "threshold": t, "predicted_pairs": pred, "true_positives": tp,
            "precision": round(precision, 4), "recall": round(recall, 4),
            "f1": round(f1, 4), "recall_corrupted_pairs": round(recall_corr, 4),
        })
        print(f"dedupe t>={t:<5} pred={pred:>9,} P={precision:.4f} "
              f"R={recall:.4f} F1={f1:.4f} R_corr={recall_corr:.4f}")
    return {"task": "crm_dedupe", "ground_truth_pairs": int(n_truth),
            "corrupted_pairs": int(n_corr), "selection": "pairwise",
            "by_threshold": results}


def main() -> None:
    con = duckdb.connect(str(DB_PATH), read_only=True)
    tasks = [score_link(con)]
    have_dedupe = con.sql("""
        SELECT count(*) FROM information_schema.tables
        WHERE table_schema = 'main_er' AND table_name = 'crm_dedupe_matches'
    """).fetchone()[0]
    if have_dedupe:
        tasks.append(score_dedupe(con))
    OUT_PATH.write_text(json.dumps({"tasks": tasks}, indent=2) + "\n")
    print(f"scorecard written to {OUT_PATH}")


if __name__ == "__main__":
    main()
