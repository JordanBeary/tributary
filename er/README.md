# er

Splink entity-resolution pipeline (Phase 3): probabilistic linkage over the dbt staging layer in `warehouse/tributary.duckdb`, scored against the hidden crosswalk (`data/private/`, never committed or uploaded — design 2.4).

| Script | Task | Output |
| --- | --- | --- |
| `link_crm_marketing.py` | CRM leads ↔ marketing contacts (no shared key; names/phones/zips) | `main_er.crm_contact_matches` + best-match table; `models/crm_marketing_model.json` |
| `dedupe_crm.py` | CRM leads → consumer clusters (C7 corrupted duplicates) | `main_er.crm_dedupe_matches`; `models/crm_dedupe_model.json` |
| `score.py` | Precision/recall/F1 vs. crosswalk, by threshold; corrupted-pair recall split | `scorecard.json` (aggregates only) |

Run order: `dbt build` in `warehouse/`, then the two model scripts, then `score.py`. Committed artifacts (model JSONs, scorecard) contain aggregate parameters and metrics only — no identity data.

Current finding (2026-08-20, D8): both tasks score above the design's 0.85–0.95 difficulty band (link F1 0.976 = its ambiguity ceiling; dedupe F1 0.997). The pathology dials are pending a human decision before any tuning.
