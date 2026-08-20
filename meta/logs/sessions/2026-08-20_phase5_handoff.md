# Phase 4 → Phase 5 Handoff

Written 2026-08-20 at the end of the Phase 4 build session: session-start context for Phase 5 (ML models 1–4). Durable state lives in the canonical docs (CLAUDE.md read-first list); this note is the delta a fresh session needs.
Provenance: A

## Decision requested before Phase 4 closes (INT-015 form)

**D10 — Phase 4 marts and dashboards** (`meta/logs/decisions.md`).

1. *What was decided and why:* the marts are wide denormalized facts at event / lead / contact grain plus one consumer dimension (P-009 applied; the design's "star schema" wording amended in v1.5); operating points are stated in one place (t=0.9 clusters, best-match contact, 30-day last-touch campaign attribution, 30-day duplicate-sale window); dashboards are six static Plotly pages built by one script, each panel tagged with the silo-audit question it answers.
2. *The ask:* accept / amend / reject. The most likely amendments are the two 30-day windows (both are single constants in `fct_leads.sql`, and the duplicate window's sensitivity is already charted) and whether `fct_marketing_contacts` should filter the contact match at p >= 0.9 rather than carry every best match.
3. *Consequences:* accept closes Phase 4 (all nine silo-audit questions answered with a chart, `docs/silo_audit.md` Section 6; logs current; graph validates). Amend a window: edit one constant, `dbt build --select marts` (20 s), rebuild dashboards (1 s), refresh Section 6 numbers. Reject the wide shape: the spine (Phase 3) is unchanged, so a star layout is a new set of models over the same intermediate tables.
4. *Recommendation:* accept. The wide shape is what the dashboards needed — no dashboard query joins two marts — and the operating points are explicit and cheap to move.

Two findings in D10 correct earlier records and need no decision, only awareness: C16's realized display ROAS (0.78x) is stale under C18 (now 1.29x; ordering and spread unchanged), and the funded flag is flat by construction (C17d).

## Where Phase 4 ended

- `warehouse/models/marts/`: `fct_auction_events` (24.5M × 37), `fct_leads` (2.40M × 54), `fct_marketing_contacts` (859k × 23), `fct_channel_month` (84 × 18), `dim_consumer` (635,580 × 15). `dbt build --select marts` rebuilds them from the existing staging/intermediate tables without touching the cloud (21 s, 19 tests).
- `analysis/dashboards/`: `build_dashboards.py` → `out/*.html` (six pages, 22–61 KB each, plotly.js from CDN) + `data/*.json` aggregates + `build_receipt.json`. Pages were rendered in headless Chrome and inspected; the exit checklist is `docs/silo_audit.md` Section 6.
- Headline numbers: 92% of revenue attributable to a marketing contact; paid ROAS 1.29x–4.16x (blended 2.64x); 635,580 consumers vs 2.40M lead_uuids; $40.0M (14%) duplicate-sale revenue to the same buyer within 30 days; nurture lift +0.125pp (CI spans zero) vs injected +0.115pp.

## What Phase 5 is

Design Section 8 (models 1–4) and Section 9 Phase 5 row: trained models + model cards + evaluation notebooks; exit = beats naive baselines, calibration and uplift Qini curves documented. Models 3–6 are droppable (risk register). Features should come from `fct_leads` / `fct_auction_events`, which already carry the consumer-entity sequence (`application_seq`, `days_since_prior_application`), the payload, CRM attributes, and marketing acquisition attributes row-wise.

## Watch items carried forward

1. **Funded flag is uninformative by construction (C17d)**: flat 13.4% across tier, price, FICO. A funded-propensity model (if one of models 1–4 targets funding) learns nothing; either target sale/price instead or amend C17d with a quality-dependent draw (a C-series decision, re-runs the simulation and the silo loads — the CRM's Neon headroom is ~6%, so no new columns).
2. **Uplift experiment is underpowered for the pooled ATE** at project scale; evaluate the uplift model on Qini / ranking against the injected per-segment effect (`simulation/params/uplift_params.json`, multipliers renormalized to mean 1 as in `simulation/marketing.py`).
3. **Censoring**: 957k unsold leads (39.9%) have no observed value; bids below floor are observed (0.8 bids per unsold lead per tier). This is the structure models 1–2 must respect.
4. **C1 price-scale watch item** (unchanged): realized tier-1 mean clearing ~$270 vs the $120 anchor; human decision before anything publishes.
5. **Warehouse file hygiene**: `warehouse/tributary.duckdb` is 4.3 GB, mostly Splink scratch tables (`main.__splink__*`); a cleanup step in `er/` would shrink it — left for an ER session.
6. **Campaign attribution is weak by construction**: monthly nurture sends with a median 86-day message-to-application lag; last-touch credit covers 19% of revenue. If a sharper campaign story is wanted, it is a simulation change (event-triggered sends), not an analytics one.

## Standing process rules most likely to bite

INT-015 (decision requests in full form), INT-010 (no AI-attribution trailers; `Provenance:` only), C13b/P-007 (synthetic data, never the library name), the redaction rule, and the session protocol (state phase and governing sections at start; candidate records at end; graph diff in the same commit as structural change).
