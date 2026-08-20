"""Consumer clusters: connected components over the dedupe match pairs.

Usage:
    .venv/bin/python er/build_clusters.py [--local] [--threshold 0.9]

Collapses CRM leads into consumer entities: nodes are lead_ids, edges are
dedupe pairs at or above the threshold (default 0.9, where measured pairwise
precision is 0.9998 -- transitive closure amplifies any false edge, so the
high-precision operating point is the right one for clustering). Components
via scipy sparse csgraph.

Writes main_er.consumer_clusters (crm_lead_id -> cluster_id). Cluster purity
vs. the crosswalk is measured in er/score.py.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = REPO_ROOT / "warehouse" / "tributary.duckdb"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--local", action="store_true")
    ap.add_argument("--threshold", type=float, default=0.9)
    args = ap.parse_args()
    db = REPO_ROOT / "data" / "tuning.duckdb" if args.local else DB_PATH
    con = duckdb.connect(str(db))

    # Node universe = every CRM lead (leads with no match edge anywhere
    # still form singleton consumer entities).
    if args.local:
        gen = REPO_ROOT / "data" / "generated"
        universe = f"SELECT lead_id FROM read_csv('{gen}/crm/leads.csv')"
    else:
        universe = "SELECT lead_id FROM main_staging.stg_crm__leads"
    leads = con.sql(universe).df()["lead_id"].to_numpy()
    edges = con.sql(f"""
        SELECT lead_id_l, lead_id_r FROM main_er.crm_dedupe_matches
        WHERE match_probability >= {args.threshold}
    """).df()

    # Dense node indexing over every lead seen anywhere, so singleton leads
    # (no dedupe edge) still receive a cluster id.
    idx = pd.Series(np.arange(len(leads)), index=leads)
    n = len(leads)
    g = coo_matrix((np.ones(len(edges)),
                    (idx[edges["lead_id_l"]].to_numpy(),
                     idx[edges["lead_id_r"]].to_numpy())), shape=(n, n))
    n_comp, labels = connected_components(g, directed=False)

    out = pd.DataFrame({"crm_lead_id": leads, "cluster_id": labels})
    con.execute("CREATE SCHEMA IF NOT EXISTS main_er")
    con.register("clusters_df", out)
    con.execute("""CREATE OR REPLACE TABLE main_er.consumer_clusters AS
                   SELECT * FROM clusters_df""")
    print(f"{n:,} leads -> {n_comp:,} clusters (threshold {args.threshold})")
    con.close()


if __name__ == "__main__":
    main()
