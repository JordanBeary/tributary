# Silo Audit Memo

Phase 2 deliverable (design Sections 7.1 and 9): the as-deployed state of the three silos, what each can and cannot answer alone, and the cost receipts. This is the "before" picture the Phase 3–4 unification work is measured against.

Status: draft v0.3, 2026-08-20 — silos re-deployed with the C18 engine (heavy-tailed repeats + identity drift, P-010/D8); inventory numbers below are the C18 world
Provenance: A

---

## 1. As-deployed inventory

All figures are from the seeded full-scale run (`--scale 1.0 --seed 42`, regenerated 2026-08-20 with the C18 engine) and verified against the live resources after load.

| Silo | Platform | Contents | Rows | Deployed size |
| --- | --- | --- | --- | --- |
| Auction lake | S3 `s3://tributary-auction-lake-jb/auction/` | Hive-partitioned Parquet, `event_date=YYYY-MM-DD/`, 366 partitions, 366 objects | 24,543,377 events | 1,194,481,319 bytes (byte-exact vs. local) |
| CRM | Neon Postgres, `leads` table (D6 shape: no street/city, hash as `BYTEA`) | full snapshot, entity grain | 2,279,550 | 0.461 GB relation; 0.469 GB database logical |
| Marketing | BigQuery `marketing` dataset | `contacts`, `messages` (partitioned by `DATE(sent_at)`, clustered by `channel`), `channel_spend` | 858,653 / 2,191,102 / 84 | ~0.09 / ~0.23 / ~0 GB logical |

Auction event mix: 8,182,661 `bid_request`, 8,178,055 `bid`, 6,740,110 `no_sale`, 1,442,551 `win`; 2,399,526 distinct `lead_uuid`s; window 2025-07-01 through 2026-07-01.

Queryability from VS Code (the Phase 2 exit check):

- S3: local DuckDB with `httpfs` + the `tributary` profile reads the lake directly; a one-month slice (October 2025) returns 696,382 bid requests and a $198.61 mean clearing price on wins in one query.
- BigQuery: the benchmark query in Section 3 runs from the local Python client under ADC.
- Neon: the deployed `leads` table answers funnel queries from local `psycopg2` — 1,187,351 sold / 909,012 closed_lost / 183,187 funded (funded on sold = 13.4%, matching the C17d artifact rate).

The crosswalk (`data/private/crosswalk.parquet`, 374 MB) was uploaded nowhere; the S3 loader refuses to run if any crosswalk artifact appears under its source tree, and the deployed object listing contains only `auction/` keys.

## 2. What each silo answers alone — and three questions it gets wrong or cannot answer

The pathologies below are the deliberate fracture defects (design Section 2.3, ratified in C17); the point of this memo is that each silo looks self-sufficient and is not.

### Auction lake (event grain, UTC, keyed by `lead_uuid`)

Answers well: sell-through rate and earnings-per-lead by tier; bid depth and win-price distributions; day-over-day volume. The C17a payload (state, loan amount, purpose, FICO band) even permits credit-band segmentation of auction metrics.

1. **"How much revenue did marketing drive?"** — unanswerable. No marketing key exists in any event; campaign attribution requires consumer identity, which the lake does not carry.
2. **"How many distinct consumers do we auction?"** — answered wrongly. 2.40M `lead_uuid`s overcount consumers ~3.8x: under C18, 52% of persons apply more than once (heavy-tailed to 100+), 43% of applications arrive under drifted identity variants, and each application is a fresh UUID. The lake cannot see that two leads are one person.
3. **"Did the leads we sold actually fund?"** — answered wrongly. "Conversion" here means *sold*; funding outcomes live only in the CRM (`status = 'funded'`), reported back 7–45 days later. Revenue-quality analysis stops at the hammer price.

### CRM (entity grain, naive US/Pacific timestamps, keyed by `lead_id` + `email_sha256`)

Answers well: application volume, quality mix (FICO band, income, purpose), funnel status counts, funded rate among sold leads.

1. **"What did this lead sell for?"** — unanswerable. No auction key, no price. The CRM sees `sold` as a status, never a dollar amount.
2. **"Which campaign sourced this applicant?"** — unanswerable. The CRM's `email_sha256` and marketing's MD5 `contact_id` are deliberately different hashes of email (C17e); no campaign identifier crosses the boundary.
3. **"How many unique applicants do we have?"** — answered wrongly, twice over. Heavy repeat applications under drifted identities (C18: new phones, new emails, name forms, moves — 43% of rows) inflate the count several-fold, and the pre-migration window is silently missing ~5% of legacy records (C17c) while their auction events live on as orphans — so the CRM both overcounts recent applicants and undercounts history.

### Marketing (message grain, naive US/Eastern timestamps, keyed by `contact_id`)

Answers well: send/open/click rates by campaign and channel; acquisition-channel spend and contact acquisition cost; holdout assignment for the uplift experiment.

1. **"What is campaign ROI?"** — answered wrongly. "Conversion" in this silo is a click. Spend is known to the dollar (`channel_spend`), but revenue lives two silos away; any ROI computed here is click-value fiction.
2. **"Did the people we messaged apply or fund?"** — unanswerable. No CRM or auction key; ~10% of contacts never became leads at all and are indistinguishable from converters.
3. **"What did the holdout experiment lift?"** — answerable only in click terms. The `in_holdout` flag is present, but true revenue lift per contact requires auction outcomes the silo cannot reach.

## 3. Cost receipts

- **S3 load**: a few hundred PUT-class requests per deploy (366 objects since C18; multipart parts included) — well under $0.02 one-time; ~1.23 GB standard storage ≈ $0.03/month. The few-large-files layout was uploaded once; the writes-cost-~12x-reads rule (design Section 5) is why the loader syncs rather than iterates remotely.
- **BigQuery load**: load jobs are free; ~0.59 GB total logical storage, inside the 10 GiB free tier.
- **Bytes-scanned benchmark** (`silos/marketing_bq/benchmark_receipt.json`): a representative dashboard query (one channel, one month, per-campaign open/click rollup) scanned **124,325,982 bytes against the unpartitioned `messages` table and 11,430,092 bytes after `PARTITION BY DATE(sent_at)` + `CLUSTER BY channel` — a 10.9x reduction**. At the on-demand rate of $6.25/TiB this table is effectively free at project scale either way; at the design Section 5.3 100x extrapolation (~40 GB table), the same query goes from ~12 GB scanned to ~1.1 GB — the difference between burning the 1 TiB free tier in ~80 dashboard loads versus ~900.
- **Neon**: $0 — the full silo fits the free tier by measurement (Section 4), which avoided a ~$15/month typical-spend paid tier.
- **Billing console receipts at phase close (2026-08-14):** AWS month-to-date **$0.01** ([screenshot](img/aws-cost-2026-08-14.png)); GCP August 1–14 **$0.00** ([screenshot](img/gcp-cost-2026-08-14.png)). The whole Phase 2 deployment — 3 GB uploaded, three silos live — cost one cent.

## 4. CRM free-tier fit (measured, decided, resolved)

The C17 watch item asked for a measurement before any trim decision, because CSV size is not heap size. Measured on Neon (scale-0.01 probe, 22,716 rows loaded into a throwaway table, then dropped):

- 270.8 bytes/row total at full column width — extrapolating to 2,279,540 rows gives **~0.62 GB against the ~0.5 GB free tier**, over by ~24% before any secondary index.
- Column weight was not where the handoff guessed: `email_sha256` stored as hex `CHAR(64)` was the single fattest column at **27.4%** of row bytes; `street_address` + `city` together 13.3%; names 5.9%; phone 5.5% — so dropping street/city alone would not have cleared the tier.

**Resolution (D6, human-ratified 2026-08-14):** the deployed table drops `street_address`/`city` (neither is in the C17e entity-resolution ladder) and stores the hash as 32-byte `BYTEA`, hex-decoded in-stream by the loader; the generated CSV and `schema.sql` are untouched fracture artifacts, and Phase 3 staging re-encodes losslessly with `encode(email_sha256, 'hex')`. Measured after the full load: **0.462 GB relation, 0.470 GB database logical — under the tier with ~6% headroom**, hash round-trip verified exact. Headroom is thin: history retention stays at the console minimum, and any schema addition re-measures first. Also confirmed in-console (2026-08-14): the first paid tier is usage-based with typical spend ~$15/month, which is why the free-tier fit was worth engineering.

## 5. Standing verifications

- Silo key isolation, orphan mechanics, timezone pathologies, and crosswalk confinement are asserted by `tests/test_fracture.py` against the generated artifacts; this memo's job was to confirm the *deployed* copies match the generated ones (byte-exact on S3; row-exact on BigQuery; row-exact on Neon minus the two D6-dropped columns, with the hash recoding verified lossless).
- Naive wall-clock timestamps were loaded into BigQuery as `DATETIME` (not `TIMESTAMP`) precisely so the timezone pathology survives deployment instead of being silently "fixed" by a UTC assumption.
