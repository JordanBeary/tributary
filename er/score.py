"""Score ER predictions against the hidden crosswalk (design Section 2.4).

Usage:
    .venv/bin/python er/score.py

Reads the main_er prediction tables from the warehouse DuckDB and the
private crosswalk (data/private/ -- local only, never committed or
uploaded), and writes aggregate metrics to er/scorecard.json. The scorecard
contains counts and rates only; no identity data leaves data/private/.

Four tasks:
  - crm_marketing_link: every CRM lead maps to exactly one marketing
    contact; a predicted (lead, contact) pair is correct iff the crosswalk
    contains it. Selection: best match per lead.
  - crm_dedupe: pairs of CRM leads sharing a consumer_key. Recall is
    reported separately for corrupted pairs (at least one side is a
    drifted variant, C18) and clean same-identity pairs.
  - auction_link: lead_uuid -> crm_lead_id from payload + time proximity;
    scored per lead and per event (the design's >95% consumer-joinable
    criterion), with orphan specificity (migration-orphan uuids correctly
    left unmatched).
  - clusters: connected-component consumer entities vs. true persons --
    weighted purity, exact-partition rate, and cluster/person counts.
"""

from __future__ import annotations

import argparse
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


def score_auction_link(con: duckdb.DuckDBPyConnection) -> dict:
    con.execute(f"""
        CREATE OR REPLACE TEMP VIEW truth_auction AS
        SELECT lead_uuid, crm_lead_id
        FROM read_parquet('{CROSSWALK}')
    """)
    lead_tp, lead_pred = con.sql("""
        SELECT sum((t.crm_lead_id IS NOT NULL
                AND t.crm_lead_id = p.crm_lead_id)::int), count(*)
        FROM main_er.auction_crm_matches p
        JOIN truth_auction t USING (lead_uuid)
    """).fetchone()
    n_uuids, n_orphan = con.sql("""
        SELECT count(*), sum((crm_lead_id IS NULL)::int) FROM truth_auction
    """).fetchone()
    orphan_matched = con.sql("""
        SELECT count(*) FROM main_er.auction_crm_matches p
        JOIN truth_auction t USING (lead_uuid)
        WHERE t.crm_lead_id IS NULL
    """).fetchone()[0]

    # Event grain: the exit criterion counts events, not leads
    ev_total, ev_joined, ev_correct = con.sql("""
        SELECT count(*),
               sum((p.crm_lead_id IS NOT NULL)::int),
               sum((p.crm_lead_id = t.crm_lead_id)::int)
        FROM main_staging.stg_auction__events e
        LEFT JOIN main_er.auction_crm_matches p USING (lead_uuid)
        LEFT JOIN truth_auction t ON t.lead_uuid = e.lead_uuid
    """).fetchone()

    res = {
        "task": "auction_link",
        "lead_uuids": int(n_uuids), "orphan_uuids": int(n_orphan),
        "lead_precision": round(lead_tp / lead_pred, 4),
        "lead_recall_nonorphan": round(lead_tp / (n_uuids - n_orphan), 4),
        "orphan_specificity": round(1 - orphan_matched / n_orphan, 4),
        "events_total": int(ev_total),
        "events_joinable_pct": round(ev_joined / ev_total, 4),
        "events_correctly_joined_pct": round(ev_correct / ev_total, 4),
        "events_joinable_before_er_pct": 0.0,
    }
    print(f"auction lead P={res['lead_precision']} "
          f"R={res['lead_recall_nonorphan']} "
          f"orphan_spec={res['orphan_specificity']} | events joinable "
          f"{res['events_joinable_pct']:.1%} correct "
          f"{res['events_correctly_joined_pct']:.1%}")
    return res


def score_clusters(con: duckdb.DuckDBPyConnection) -> dict:
    # Weighted purity: for each predicted cluster, the share of its leads
    # belonging to its majority person, weighted by cluster size.
    purity, n_clusters, n_leads = con.sql(f"""
        WITH truth AS (
            SELECT crm_lead_id, consumer_key FROM read_parquet('{CROSSWALK}')
            WHERE crm_lead_id IS NOT NULL),
        joined AS (
            SELECT c.cluster_id, t.consumer_key
            FROM main_er.consumer_clusters c JOIN truth t USING (crm_lead_id)),
        per_cluster AS (
            SELECT cluster_id, max(cnt) AS majority, sum(cnt) AS size
            FROM (SELECT cluster_id, consumer_key, count(*) AS cnt
                  FROM joined GROUP BY 1, 2)
            GROUP BY 1)
        SELECT sum(majority)::float / sum(size), count(*), sum(size)
        FROM per_cluster
    """).fetchone()
    n_persons = con.sql(f"""
        SELECT count(DISTINCT consumer_key) FROM read_parquet('{CROSSWALK}')
        WHERE crm_lead_id IS NOT NULL
    """).fetchone()[0]
    exact = con.sql(f"""
        WITH truth AS (
            SELECT crm_lead_id, consumer_key FROM read_parquet('{CROSSWALK}')
            WHERE crm_lead_id IS NOT NULL),
        joined AS (
            SELECT c.cluster_id, t.consumer_key
            FROM main_er.consumer_clusters c JOIN truth t USING (crm_lead_id)),
        cluster_person AS (
            SELECT cluster_id, count(DISTINCT consumer_key) AS persons_in
            FROM joined GROUP BY 1),
        person_cluster AS (
            SELECT consumer_key, count(DISTINCT cluster_id) AS clusters_of
            FROM joined GROUP BY 1)
        SELECT (SELECT count(*) FROM cluster_person WHERE persons_in = 1),
               (SELECT count(*) FROM person_cluster WHERE clusters_of = 1)
    """).fetchone()
    res = {
        "task": "clusters",
        "clusters": int(n_clusters), "true_persons": int(n_persons),
        "clustered_leads": int(n_leads),
        "weighted_purity": round(purity, 4),
        "pure_cluster_share": round(exact[0] / n_clusters, 4),
        "unsplit_person_share": round(exact[1] / n_persons, 4),
    }
    print(f"clusters {res['clusters']:,} vs persons {res['true_persons']:,} | "
          f"purity={res['weighted_purity']} pure={res['pure_cluster_share']:.1%} "
          f"unsplit={res['unsplit_person_share']:.1%}")
    return res


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--local", action="store_true",
                    help="score the tuning DB (local fracture outputs)")
    args = ap.parse_args()
    db = REPO_ROOT / "data" / "tuning.duckdb" if args.local else DB_PATH
    con = duckdb.connect(str(db), read_only=True)
    tasks = [score_link(con)]
    have_dedupe = con.sql("""
        SELECT count(*) FROM information_schema.tables
        WHERE table_schema = 'main_er' AND table_name = 'crm_dedupe_matches'
    """).fetchone()[0]
    if have_dedupe:
        tasks.append(score_dedupe(con))
    for tbl, fn in (("auction_crm_matches", score_auction_link),
                    ("consumer_clusters", score_clusters)):
        if con.sql(f"""SELECT count(*) FROM information_schema.tables
                       WHERE table_schema = 'main_er'
                       AND table_name = '{tbl}'""").fetchone()[0]:
            tasks.append(fn(con))
    OUT_PATH.write_text(json.dumps({"tasks": tasks}, indent=2) + "\n")
    print(f"scorecard written to {OUT_PATH}")


if __name__ == "__main__":
    main()
