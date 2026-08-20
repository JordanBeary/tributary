# Phase 3 → Phase 4 Handoff

Written 2026-08-20 at Phase 3 close, at the human's request: session-start context for the Phase 4 (analytics marts + dashboards) session. Durable state lives in the canonical docs (CLAUDE.md read-first list); this note is the delta a fresh session needs.
Provenance: HD (human-requested, agent-drafted)

## Where Phase 3 ended

The unification stack runs end to end and every exit criterion is measured against the hidden crosswalk (commit 5c6b57d; scorecard in `er/scorecard.json`, prose table in `er/README.md`):

- **dbt staging** (`warehouse/`, dbt-duckdb): five models over the three live silos — S3 via httpfs, Neon attached read-only, BigQuery via local Parquet exports (`warehouse/export_marketing.py`). All timestamps naive-UTC (`*_utc`). 22 tests green. Full rebuild pulls ~2 GB and takes ~7–9 min; the S3 auction pull dominates.
- **ER pipeline** (`er/`): four scripts, run in order after `dbt build` — `link_crm_marketing.py` (Splink, no shared key), `dedupe_crm.py` (Splink), `link_auction_crm.py` (deterministic payload+time, D9a), `build_clusters.py` (components at t=0.9, D9b) — then `score.py`. All take `--local` to run against `data/generated/` without cloud pulls (writes `data/tuning.duckdb`).
- **Intermediate spine** (`warehouse/models/intermediate/`): `int_consumer_entities` (lead → consumer entity + best-match contact), `int_auction_consumer_map` (lead_uuid → entity). 8 tests green. **Marts join through the spine.**
- **Numbers**: link F1 0.879, dedupe F1 0.873 (D8 band 0.8–0.9, human-set); auction events **95.3% consumer-joinable** (94.8% correctly; gap ≈ the ~5% migration orphans, unjoinable by construction; 0% before ER); cluster purity 0.9998, 98.1% of persons unsplit.

**The world is C18** (heavy-tailed repeats + channel-dependent identity drift, from the author's industry data, P-010): 639k persons, mean 3.76 applications each (tail to 150), 43% of applications under drifted identity variants. Silos: 24.5M auction events (366 objects, byte-exact), CRM 2,279,550 rows at 0.469 GB (D6 shape — no street/city, hash as BYTEA; ~6% Neon headroom), marketing 858,653 contacts / 2.19M messages. Disk (`data/generated/`) holds the matching full-scale run; `warehouse/tributary.duckdb` holds built staging + intermediate + `main_er` tables.

## What Phase 4 is

Design Section 9, Phase 4 row: star-schema marts + 4–6 dashboards + before/after silo analysis. **Exit criterion: every Section 7.1 "unanswerable" question answered with a chart.** The nine concrete questions (three per silo) are enumerated in `docs/silo_audit.md` Section 2 — that section is the exit checklist.

Section 7.3 names the analyses: full-funnel (impressions → applications → auctioned → sold → funded) with drop-off economics; EPL by tier × credit band; buyer concentration (HHI) by tier; duplicate-consumer cost in dollars; marketing → revenue attribution and per-channel ROAS through to auction revenue (C16 economics span 0.78x display to 2.7x affiliate by construction — a real finding to surface); the uplift experiment's revenue lift (in_holdout is in the contacts table).

## Standing directives that shape Phase 4

- **Mart shape (P-009, human preference)**: wide, denormalized fact tables — event grain carrying consumer/demographic attributes row-wise, not narrow facts requiring joins. The spine exists precisely to hydrate wide facts.
- **Site is a presentation layer only (human directive, 2026-08-20)**: all analytics products must surface as *static cached artifacts* (Plotly HTML etc.) — no live compute behind the site. Build every dashboard as a cacheable export from day one.
- **Cost artifacts as you go**: bytes-scanned receipts for mart queries; the existing partitioning receipt (`silos/marketing_bq/benchmark_receipt.json`) documents the pre-C18 experiment — re-run against C18 tables if marts query BigQuery directly.
- Local dev pattern: build marts in DuckDB on the warehouse file (design 4.1); "production" transforms in BigQuery only where the story needs them.

## Open items carried into Phase 4

1. **C1 price-scale watch item** (unchanged): realized mean clearing price ~$198.61 vs the $120 tier-1 anchor. Not blocking Phase 4; needs a human decision before anything publishes (Phase 7).
2. **Event volume**: 24.5M realized vs the design's ~9M target — declared within tolerance (decisions, "Interpretations"); free-tier fine.
3. **Neon headroom is thin** (~6%): no schema additions to the CRM silo without re-measuring; history retention stays at console minimum.
4. **ER threshold choice for marts**: the spine's `contact_match_probability` is carried per lead; marts filtering on it should state the operating point (link metrics are threshold-insensitive in 0.5–0.99, so 0.9 is a safe default).

## Standing process rules most likely to bite

- **INT-015**: decision requests state the concrete ask, options, consequences, and a recommendation — never bare id lists.
- **INT-010**: no AI-attribution trailers on commits; `Provenance: H|HD|A` (+ optional `Directs: P-xxx`) only.
- **C13b (P-007)**: generated identities are "synthetic data"; never feature the generating library's name in narrative.
- **Redaction rule**: the P-010 raw table stays in `data/private/`; committed artifacts carry only the fitted form. The employer is never named.
- Session protocol (conventions Section 3): state phase and governing design sections at session start; draft candidate records at session end; graph diff ships in the same commit as any structural change.
