# Prompt Log

Significant prompts, verbatim minus marked redactions (conventions, instruction 9 bounded by the redaction rule in `meta/conventions.md` Section 2). An entry belongs here when the prompt materially shaped an artifact or steered the project.

Entry status values: `verbatim` (exact text, redactions marked) or `summary — verbatim pending` (the source chat is not accessible from this environment; the human should backfill the exact text).

---

## P-001 — Dataset scouting (Stage 0 founding prompt)

- **Date:** 2026-07 (founding chat; verbatim log at `sessions/2026-07_founding_design_session.md`, Turn 1)
- **Status:** verbatim (backfilled 2026-08-03 from the session log)
- **Content:**
  > Can you help me find a project dataset online that is similar to the data that I work with?
  (In the logged session context, this question is preceded by the standing instruction set — see P-003 for that text and a note on how it was rendered.)
- **Shaped:** the calibration triad (iPinYou RTB, LendingClub, Criteo Uplift) recommended in response; `docs/design.md` Section 3.1; `docs/calibration_spec.md`.

## P-002 — The full design brief (Stage 1 founding prompt)

- **Date:** 2026-07 (same founding chat, Turn 2 of the session log)
- **Status:** verbatim (backfilled 2026-08-03 from the session log)
- **Content:**
  > Yes, my goal is a portfolio project that resembles my day job. Help me sketch out a project design where the objective is to organize and store data, analyze, and strategize machine learning optimization.
  >
  > If storing in a cloud environment, what would the costs associated with storage/read/write be? I would like to showcase the data silo problem in some way -  can we create simulated data based on the real data you suggested and impose/add unifying keys on the data to connect them all? I will be connect to the data via VS Code, how does that work if its hosted on cloud?
  >
  > Include a project roadmap as if I am a data science project manager.
  >
  > I would like to host the project on a public website. The site will act as a personal profile containing resume, cover letter style description of who I am/what I do/how I add value to any company, and show this project.
- **Shaped:** `docs/design.md` v1.0 in its entirety (provenance HD). The "impose/add unifying keys" idea is the human seed of the hidden-crosswalk mechanism.

## P-003 — The standing instruction set (Stage 2 reframing)

- **Date:** 2026-07/08 (project instructions in the chat environment where `meta/plan.md` was drafted)
- **Status:** verbatim — human-typed form in `sessions/2026-07_founding_design_session.md` Turn 1; normative numbered restatement in `meta/conventions.md` Section 1
- **Content:** The twelve standing instructions — quality over development cost; contribution transparency; intervention log; no emojis; no fictional names; fix what looks off; organize and index for agents; comment code; the harness is the exhibit; honesty over flash; robust design document as the seed; living design doc with flagged interventions.
- **Rendering note:** the session log displays the instruction set inside Turn 1 because Claude Projects inject the project instructions into the conversation context; the log's own closing note records that the no-fictional-names instruction postdates the Turn-2 design doc, consistent with the charter's Stage-2 timeline.
- **Shaped:** The entire global track. This is the most impactful steering input the project has received: it redefined the working method as the primary exhibit and triggered the reorganization.

## P-004 — Plan adoption and conflict review (Stage 3)

- **Date:** 2026-07-31
- **Status:** verbatim
- **Content:**
  > Read this thoroughly in its entirety. Adopt the plan and begin working on reorganizing the project and repository. Are there any significant conflicts with what has already been completed? Bring these conflicts to my attention and prompt me to make decisions about the direction.
  (Accompanied by `meta/plan.md` v0.3 as an attachment.)
- **Shaped:** The 2026-08-03 migration: the `meta/` scaffold, the cloud resource recreation, and decisions D1–D3 (made by the human in the resulting conflict review).

## P-005 — Sentinel triage and the data-mutation ledger (Phase 1)

- **Date:** 2026-08-03
- **Status:** verbatim
- **Content:** (reviewing the LendingClub notebook's `describe()` output — max DTI 999, max annual income $110M)
  > This looks suspicious - is this valid data or a sentinel record? In the data cleaning and QA pipeline can you take extra measures to highlight any processes that changes the data itself (row deletion for sentinel values or too many NA/null values, imputing values, etc). Are those rows included in computing the marginals?
- **Shaped:** The data-mutation ledger convention (calibration_spec v0.2, Section 0) — now standing practice for every profiling notebook — plus the sentinel policy and the regenerated `lendingclub_marginals.json`, which carries the ledger in its metadata. Recorded with INT-011.

## P-006 — Narrated EDA as a standing deliverable (Phase 1)

- **Date:** 2026-08-04
- **Status:** verbatim
- **Content:** (after an in-chat exploratory walkthrough of the iPinYou data — sample, data dictionary, collinearity, advertiser counts, bidding mechanics — prompted by "I have never interacted with this data so assume I don't understand it all and you are teaching me all aspects of it")
  > This information should always be surfaced - let's proceed with your plan. Keep both of the existing notebooks but add an addtional notebook (*_eda.ipynb) that investigates these foundational truths and narrates throughout.
  >
  > Log this to meet our global objectives.
- **Shaped:** The EDA-companion convention (calibration_spec v0.4, Section 0): every source dataset gets a narrated `*_eda.ipynb` covering provenance and mechanics, a data dictionary, descriptive statistics with semantics, collinearity/nesting structure, and business implications — teaching-first, read-only. `02a_ipinyou_eda.ipynb` is the first instance; companions for LendingClub and Criteo added to the Section 5 checklist. Recorded with INT-012.

## P-007 — C13 ratification with domain confirmation and a terminology amendment (Phase 1)

- **Date:** 2026-08-07
- **Status:** verbatim
- **Content:** (reviewing the C13 candidate record after the consumer engine landed)
  > including duplicates in n_consumers is good - my company also has a 1:many contact to lead ratio because with small loans consumers often return for more.
  >
  > instead of Faker i would rather just call it synthetic data.
  >
  > fico_band is good
  >
  > continue with pipeline.
- **Shaped:** C13 ratified — (a) and (c) as proposed, (b) amended so the narrative term is "synthetic identity data" rather than the library's name (design.md v1.2, spec v0.9, docstrings reworded; the `faker` dependency itself is unchanged — the amendment is about how the artifact is described). The domain note (returning small-loan borrowers make person-to-lead 1:many) also supplied the realism grounding for C14, the applications-per-consumer mix correction discovered while implementing `generate_leads`.
