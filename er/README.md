# er

Splink entity-resolution pipeline (Phase 3): probabilistic linkage over the dbt staging layer in `warehouse/tributary.duckdb`, scored against the hidden crosswalk (`data/private/`, never committed or uploaded — design 2.4).

| Script | Task | Output |
| --- | --- | --- |
| `link_crm_marketing.py` | CRM leads ↔ marketing contacts (no shared key; names/phones/zips) | `main_er.crm_contact_matches` + best-match table; `models/crm_marketing_model.json` |
| `dedupe_crm.py` | CRM leads → consumer clusters (C7 corrupted duplicates) | `main_er.crm_dedupe_matches`; `models/crm_dedupe_model.json` |
| `link_auction_crm.py` | Auction lead_uuid ↔ CRM lead (C17a payload + time proximity; deterministic, D9) | `main_er.auction_crm_matches` |
| `build_clusters.py` | Consumer entities: connected components over dedupe pairs at t=0.9 (D9) | `main_er.consumer_clusters` |
| `score.py` | All four tasks vs. crosswalk: P/R/F1 by threshold, corrupted-pair recall, event joinability, cluster purity | `scorecard.json` (aggregates only) |

Run order: `dbt build` in `warehouse/`, then the four model scripts (link, dedupe, auction link, clusters), then `score.py`; the dbt intermediate layer (`int_consumer_entities`, `int_auction_consumer_map`) consumes the `main_er` outputs. Committed artifacts (model JSONs, scorecard) contain aggregate parameters and metrics only — no identity data.

## Reconciliation scorecard (Phase 3 exit, measured 2026-08-20)

| Claim | Number |
| --- | --- |
| CRM ↔ marketing link (no shared key; drifted names/phones/zips) | F1 0.879 (P 0.895 / R 0.864) |
| CRM dedupe into consumer entities | F1 0.873 (P 0.990 / R 0.781); corrupted-pair recall 0.743 |
| Auction events consumer-joinable (was 0% before ER) | **95.3%** (94.8% correctly; the gap is the ~5% migration orphans, unjoinable by construction) |
| Auction linkage, lead grain | P 0.995 / R 0.998 (non-orphan); orphan specificity 0.934 |
| Consumer clusters | 636,164 vs. 623,470 true persons; purity 0.9998; 98.1% of persons unsplit |

Every number is scored against the hidden crosswalk (design 2.4) — the ground truth no silo, and no cloud, ever saw.

D8 resolution (2026-08-20): the original engine scored above the band (link F1 0.976 = its ambiguity ceiling; dedupe 0.997). C18 (heavy-tailed repeat applications + channel-dependent identity drift, P-010) landed both tasks in the human-amended 0.8–0.9 band: link F1 0.879, dedupe F1 0.873 (corrupted-pair recall 0.743). Both model scripts take `--local` to tune dials against `data/generated/` without touching the cloud silos; the committed scorecard is the cloud-path run.
