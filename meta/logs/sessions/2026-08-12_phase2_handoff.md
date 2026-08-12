# Phase 1 → Phase 2 Handoff

Written 2026-08-12 at Phase 1 close, at the human's request: session-start context for the Phase 2 (silo deployment) session. Durable state lives in the canonical docs (CLAUDE.md read-first list); this note is the delta a fresh session needs and the operational facts that are otherwise scattered.
Provenance: HD (human-requested, agent-drafted)

## Where Phase 1 ended

All five simulation stages are production code, artifact-driven (A1), each with tests that reproduce the calibration QA gates from `simulation/params/*.json` alone — 42 tests, all green. One seeded command regenerates everything: `.venv/bin/python -m simulation --scale 0.01` (1.8 s) or `--scale 1.0` (~2.5 min, ~22 GB peak RSS during fracture). Decision records C9–C17 are all human-ratified; the design doc is at v1.3, the calibration spec at v0.12, the project guide at v2.2.

**Current disk state**: `data/generated/` and `data/private/` hold a **scale 0.01** run. Phase 2 must regenerate at `--scale 1.0` before uploading. The CLI has no `--private-dir` flag, so the crosswalk always writes to `data/private/` regardless of `--out-dir` — fine for the standard invocation, but do not point `--out-dir` at a staging area and assume the crosswalk followed it.

## What Phase 2 is

Design Section 9, Phase 2 row: load the three silos into their clouds — S3 lake (partitioned Parquet), Neon Postgres (CRM), BigQuery (marketing) — with loaders in `silos/` (graph node `silos-dir`, contract: loaders depend on `simulation-pkg`). Exit criteria: each silo queryable from VS Code; silo audit memo drafted. Plus the global criterion (charter Section 2): logs current, graph validates, provenance recorded.

What gets uploaded per silo (fracture outputs, under `data/generated/`):

| Silo | Files | Destination | Size at scale 1.0 |
| --- | --- | --- | --- |
| Auction | `auction/event_date=*/**.parquet` | `s3://tributary-auction-lake-jb` | 1.3 GB (~367 partitions, 24.5M events) |
| CRM | `crm/leads.csv` + `crm/schema.sql` | Neon Postgres (`CRM_DATABASE_URL` in `.env`) | 561 MB CSV — see open item 1 |
| Marketing | `marketing/{contacts,messages,channel_spend}.jsonl` | `tributary-jb:marketing` (BigQuery) | 1.2 GB JSONL |

**The crosswalk (`data/private/crosswalk.parquet`) uploads nowhere, ever** (design 2.4). Verify no upload path touches `data/private/`.

## Operational facts (beyond CLAUDE.md's machine quirks)

- **AWS**: use `--profile tributary` (least-privilege, S3-only, scoped to the one bucket). The admin key stays deactivated — Phase 2 needs no IAM or infra changes. S3 writes cost ~12x reads (design Section 5): upload the few-large-files layout once, don't iterate remotely.
- **Neon**: connection string in `.env` as `CRM_DATABASE_URL`; `psycopg2-binary` is in the `[dev]` extras, so the loader can be pure Python (or `psql \copy` per `crm/schema.sql` if psql is available).
- **BigQuery**: ADC auth is done; quota project `tributary-jb`. `bq`/`gcloud` need `CLOUDSDK_PYTHON` exported in non-interactive shells (see CLAUDE.md). `google-cloud-bigquery` is in `[dev]` extras.
- **Cost artifacts are deliverables** (project_guide Section 1, item 4): screenshot budgets before/after load; in BigQuery, record bytes-scanned for a benchmark query before and after partitioning/clustering — the FinOps write-up and Section 5.3's 100x extrapolation need these receipts.

## Open items carried into Phase 2

1. **CRM free-tier trim — decision needed early in Phase 2** (C17 watch item). `leads.csv` is 561 MB against Neon's ~0.5 GB free tier; the design's own rule is free-tier limits take precedence over row counts. First measure the *actual Postgres table size* (CSV size ≠ heap size; 2.4M rows may land under the limit or well over it with indexes). If over, options to put to the human per the INT-015 protocol: (a) trim columns from the CRM load (street_address/city are the fattest and least analytically load-bearing), (b) load a scale slice of leads, (c) accept the paid tier. Do not decide unilaterally.
2. **C1 price-scale watch item**: realized full-scale mean clearing price is $198 vs the $120 tier-1 anchor (C11 elasticity right tail). Not blocking Phase 2; needs a human decision before anything publishes (Phase 7).
3. **ER difficulty**: the F1 target band is 0.85–0.95 (Phase 3). The dials are C7's corruption mix and the identity-field overlap decided in C17e (names/phones/zips, dual-hash email isolation). Nothing to do in Phase 2 except not "fixing" the pathologies while loading.
4. **Event volume**: 24.5M events vs the design's ~9M target — within the declared volumes-are-targets tolerance (decisions, "Interpretations" section); free-tier fine. If it ever needs reducing, the lever is dropping per-tier `bid_request` rows (derivable from terminal events), but that changes the C17a payload carrier — a human decision.

## Standing process rules most likely to bite in Phase 2

- **INT-015**: decision requests to the human must state the concrete ask, options, consequences, and a recommendation — never a bare list of ids.
- **INT-010**: no AI-attribution trailers on commits; `Provenance: H|HD|A` (+ optional `Directs: P-xxx`) only.
- **C13b (P-007)**: generated identities are "synthetic data" in all narrative; never feature the generating library's name.
- **P-009**: the author prefers wide, denormalized OLAP fact tables — relevant when the Phase 3/4 dbt work starts.
- Session protocol (conventions Section 3): state phase and governing design sections at session start; draft candidate records at session end; graph diff ships in the same commit as any structural change.
