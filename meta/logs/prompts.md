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
