# er

Splink entity-resolution pipeline (Phase 3): probabilistic linkage over the dbt staging layer in `warehouse/tributary.duckdb`, scored against the hidden crosswalk (`data/private/`, never committed or uploaded — design 2.4).

| Script | Task | Output |
| --- | --- | --- |
| `link_crm_marketing.py` | CRM leads ↔ marketing contacts (no shared key; names/phones/zips) | `main_er.crm_contact_matches` + best-match table; `models/crm_marketing_model.json` |
| `dedupe_crm.py` | CRM leads → consumer clusters (C7 corrupted duplicates) | `main_er.crm_dedupe_matches`; `models/crm_dedupe_model.json` |
| `score.py` | Precision/recall/F1 vs. crosswalk, by threshold; corrupted-pair recall split | `scorecard.json` (aggregates only) |

Run order: `dbt build` in `warehouse/`, then the two model scripts, then `score.py`. Committed artifacts (model JSONs, scorecard) contain aggregate parameters and metrics only — no identity data.

D8 resolution (2026-08-20): the original engine scored above the band (link F1 0.976 = its ambiguity ceiling; dedupe 0.997). C18 (heavy-tailed repeat applications + channel-dependent identity drift, P-010) landed both tasks in the human-amended 0.8–0.9 band: link F1 0.879, dedupe F1 0.873 (corrupted-pair recall 0.743). Both model scripts take `--local` to tune dials against `data/generated/` without touching the cloud silos; the committed scorecard is the cloud-path run.
