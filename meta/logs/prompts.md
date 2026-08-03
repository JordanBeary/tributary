# Prompt Log

Significant prompts, verbatim minus marked redactions (conventions, instruction 9 bounded by the redaction rule in `meta/conventions.md` Section 2). An entry belongs here when the prompt materially shaped an artifact or steered the project.

Entry status values: `verbatim` (exact text, redactions marked) or `summary — verbatim pending` (the source chat is not accessible from this environment; the human should backfill the exact text).

---

## P-001 — Dataset scouting (Stage 0 founding prompt)

- **Date:** 2026-07 (founding chat: "Finding similar project datasets online")
- **Status:** summary — verbatim pending human backfill from the founding chat
- **Content (summary):** Asked for public datasets similar to the data the author works with professionally — lead-generation marketplace auctions. Materially shaped: the calibration triad (iPinYou RTB, LendingClub, Criteo Uplift) recommended in response.
- **Shaped:** `docs/design.md` Section 3.1; `docs/calibration_spec.md`.

## P-002 — The full design brief (Stage 1 founding prompt)

- **Date:** 2026-07 (same founding chat)
- **Status:** summary — verbatim pending human backfill from the founding chat
- **Content (summary):** Set the complete project brief: a portfolio project resembling the day job, covering data organization and storage, analytics, and ML optimization strategy; an explicit request to showcase the data silo problem via simulated data with imposed unifying keys; cloud storage/read/write cost analysis; a VS Code-to-cloud workflow explanation; a PM-voice roadmap; and a public site doubling as a professional profile. The "impose unifying keys on simulated data" idea is the human seed of the hidden-crosswalk mechanism.
- **Shaped:** `docs/design.md` v1.0 in its entirety (provenance HD).

## P-003 — The standing instruction set (Stage 2 reframing)

- **Date:** 2026-07/08 (project instructions in the chat environment where `meta/plan.md` was drafted)
- **Status:** verbatim (restated in full in `meta/conventions.md` Section 1)
- **Content:** The twelve standing instructions — quality over development cost; contribution transparency; intervention log; no emojis; no fictional names; fix what looks off; organize and index for agents; comment code; the harness is the exhibit; honesty over flash; robust design document as the seed; living design doc with flagged interventions.
- **Shaped:** The entire global track. This is the most impactful steering input the project has received: it redefined the working method as the primary exhibit and triggered the reorganization.

## P-004 — Plan adoption and conflict review (Stage 3)

- **Date:** 2026-07-31
- **Status:** verbatim
- **Content:**
  > Read this thoroughly in its entirety. Adopt the plan and begin working on reorganizing the project and repository. Are there any significant conflicts with what has already been completed? Bring these conflicts to my attention and prompt me to make decisions about the direction.
  (Accompanied by `meta/plan.md` v0.3 as an attachment.)
- **Shaped:** The 2026-08-03 migration: the `meta/` scaffold, the cloud resource recreation, and decisions D1–D3 (made by the human in the resulting conflict review).
