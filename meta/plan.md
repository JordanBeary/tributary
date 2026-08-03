# Tributary — Global Charter and Reorganization Plan

Status: v0.3, adopted 2026-08-03. The migration decisions left open in Section 8 (repository visibility, GCP project replacement, resource names) were resolved at adoption; see decisions D1–D3 in `meta/logs/decisions.md`.
Provenance: HD — agent-drafted from the human instruction set and retrieved session history; adopted by the human with three explicit decisions (taxonomy defined in Section 5.3)
Portability: written to be transferred into Claude Code and read cold, without access to the chat sessions that produced it. The governing instruction set is restated in full in Section 2.
Redaction note: this document is destined for the repository, which is currently public. It therefore refers to sensitive identifiers by pointer (e.g., "the account id in project_guide.md Section 4") rather than repeating them, and never names the author's employer. See Section 8, items 2–3.
Location: `meta/plan.md`, with Sections 1–3 extracted into `meta/charter.md` and `meta/conventions.md` during migration.

---

## 1. What this project is — read this first

**Tributary is not only an end-to-end data science project.** It is a dual-track project, and the data science build is the subordinate track.

- **The global track (primary).** The objective is to demonstrate that the human author can direct AI agents to get real work done: designing the harness that makes agents more effective than out-of-the-box, maintaining transparent decomposition of human contribution from agent contribution, and keeping an honest record of corrections, guidance, and decisions. The standing instruction set restated in Section 2 *is* the global objective — it is not commentary on the project; it defines the project.
- **The local track (the workload).** The end-to-end data science build specified in `docs/design.md` and operationalized in `project_guide.md`: simulation of a fractured lead-marketplace data environment, silo deployment, entity resolution, analytics, and ML optimization. It is a genuine deliverable, but it is the demonstration payload, not the thesis.

**Precedence rule.** Where the global instruction set conflicts with the local documents, the global instruction set wins. Every such conflict is resolved by amending the local document and logging the amendment (`meta/logs/interventions.md`). Sections 6 and 8 list the conflicts already identified — several of which are in `project_guide.md`, which was written before the reframing.

Any agent joining this project must internalize this ordering before touching the local work. Optimizing the data science output while neglecting the records, provenance, and harness duties is a failure of the project's primary objective, even if the code is excellent.

## 2. The global objective, stated normatively

The following standing instructions are the global objective. They originated as project instructions in the chat environment where this document was drafted; they are restated here so they survive transfer to Claude Code, and are to be mirrored into `meta/conventions.md` and root-level `CLAUDE.md` so every agent session inherits them.

1. **Quality over development cost.** In technical decisions, put little weight on development cost; prefer quality, simplicity, robustness, scalability, and long-term maintainability.
2. **Contribution transparency.** Maintain high transparency about what the human contributed versus what the agent contributed. It must be simple for an evaluator to decompose the human's contributions from an AI merely taking a seed and running with it.
3. **Intervention log.** Keep a simple log of agent errors that were corrected, together with the specific human guidance that corrected them.
4. **No emojis.** Anywhere in the repository.
5. **No fictional names for hypothetical entities.** A fictional company name is meaningless; use descriptive terms or structured identifiers instead.
6. **Fix what looks off.** If something clearly looks wrong, even outside the current task, get it fixed along the way (and log the fix).
7. **Organize and index for agents.** Spend extra effort organizing and indexing the repository so agents navigate it efficiently; produce and maintain a clean knowledge graph.
8. **Comment code.** Write clear comments for blocks of code that perform distinct functions.
9. **The harness is the exhibit.** A future employer evaluating this project would look for the harness built to make agents more effective than out-of-the-box, the plans developed to push work forward, and possibly a log of the most significant or impactful prompts.
10. **Honesty over flash.** The goal is not to impress with a flashy end product but to demonstrate that the human can effectively drive the tools to get real things done.
11. **Robust design document as the seed.** Build a robust design document and present it as the seed of the project.
12. **Living design doc with flagged interventions.** The harness must encourage flagging and saving meaningful interventions that correct misunderstandings of the design doc, and must keep the design doc actively updated as work proceeds.

**Charter-level reconciliation:** instruction 9's prompt log ("verbatim") is bounded by the confidentiality constraint in `project_guide.md` Section 3 — prompt-log entries are recorded verbatim *minus* redactions of the author's employer and personal identifiers, with each redaction marked in place. Confidentiality and no-fictional-names are compatible: the scenario stays fictionalized; it just goes unnamed (Section 8, item 1).

## 3. Context: how the project got here (firsthand history)

This section previously carried an evidence-based reconstruction. The founding chat has since been moved into this project workspace and retrieved directly, so the narrative below is grounded in the actual session transcript plus `project_guide.md`. One deliberate omission: that chat identifies the author's employer by name; per the confidentiality constraint, the employer is never named in any committed document, including this history.

- **Stage 0 — dataset scouting (chat: "Finding similar project datasets online").** The opening prompt asked for public datasets similar to the data the author works with professionally (lead-generation marketplace auctions). The agent surveyed candidates — iPinYou RTB, Criteo (click, conversion, and uplift datasets), LendingClub accepted/rejected loans, YOYI, Home Credit — and recommended combining iPinYou (auction mechanics), LendingClub (loan-vertical features), and Criteo Uplift (marketing treatment structure), noting that no public dataset mirrors a lead-gen waterfall directly.
- **Stage 1 — the design brief and design doc (same session).** The author's second prompt set the full brief: a portfolio project resembling the day job, covering data organization and storage, analytics, and ML optimization strategy; an explicit request to showcase the data silo problem via simulated data with imposed unifying keys; cloud storage/read/write cost analysis; a VS Code-to-cloud workflow explanation; a PM-voice roadmap; and a public site doubling as a professional profile. The agent drafted `design.md` v1.0 in response. Two provenance facts worth preserving: the silo-simulation-with-hidden-crosswalk concept was seeded by the author's "impose unifying keys on simulated data" idea and elaborated by the agent; and the fictional company name was introduced *by the agent* as a confidentiality device ("so nothing proprietary from your actual employer ends up on a public site"). Both founding prompts are the first entries for `meta/logs/prompts.md`.
- **Stage 1.5 — execution in Claude Code.** Phase 0 was completed against the v1.0 design: repo scaffold, devcontainer, simulation package skeleton with frozen stage contracts, and provisioned cloud silos (S3 bucket, Neon Postgres, BigQuery dataset) with budget alarms on both clouds. The Claude Code agent wrote `project_guide.md` — a working companion recording current state, ranked objectives, assumptions and decisions (its A/B/C-series tables), interpretations of ambiguous design points, and machine quirks. This document is significant for the global track: it is a *proto-meta layer that emerged organically* because the work needed it, before any instruction demanded it — but it is written entirely in the Stage-1 frame (fictional company name throughout, "career artifact" as the primary objective, no harness or provenance apparatus).
- **Stage 2 — the reframing.** The standing instruction set (Section 2) arrived and changed what the project is about: the working method became the primary exhibit. It retroactively put the Stage-1 artifacts out of compliance — the fictional name (now baked into live cloud resource names), an emoji in the design doc, no provenance records, no logs, no knowledge graph, no global deliverables in the roadmap.
- **Stage 3 — formalization and transfer (this document).** The shift made structural: a global/local split, the instruction set promoted to a normative charter, `project_guide.md` reconciled into the split (Section 6), a migration plan to bring Stage-1 artifacts into compliance, and execution continuing in Claude Code under the Section 9 operating loop.

**Operational consequence:** `docs/design.md` remains authoritative for *what the local workload is*; `project_guide.md` (post-reconciliation) for *the local workload's current state and working guidance*; this document and its `meta/` extractions for *what the project is and how it is run*.

## 4. Target repository structure

```
tributary/
├── README.md                  # router: 60-second pitch + explains both tracks
├── CLAUDE.md                  # agent entry point, auto-loaded by Claude Code:
│                              #   conventions digest, precedence rule, read-first list,
│                              #   logging duties, machine/environment quirks
├── meta/                      # ── GLOBAL TRACK ──
│   ├── plan.md                # this document
│   ├── charter.md             # Sections 1–3 extracted: objectives + per-phase global gates
│   ├── conventions.md         # Section 2 mirrored as working agreements + redaction rule
│   ├── provenance.md          # contribution taxonomy + commit trailer spec + ledger
│   ├── logs/
│   │   ├── interventions.md   # agent errors corrected + the specific human guidance
│   │   ├── prompts.md         # significant prompts, verbatim minus marked redactions
│   │   └── decisions.md       # ADR log — seeded from project_guide.md A/B/C tables
│   └── graph/
│       ├── graph.yaml         # machine-readable knowledge graph of the repo
│       └── validate_graph.py  # CI check: no dangling paths, no orphan nodes
├── docs/                      # ── LOCAL TRACK ──
│   ├── design.md              # the local seed (what to build)
│   └── calibration_spec.md
├── project_guide.md           # local working companion (current state + guidance),
│                              #   slimmed per Section 6 — decision tables move to meta/
├── simulation/  infra/  silos/  warehouse/  er/  analysis/  models/  site/
└── ...
```

**Structural decision — do not nest local content under a `project/` directory.** The split is `meta/` versus everything else, with the root `README.md` as router. Wrapping `simulation/`, `warehouse/`, etc. would churn package paths, the devcontainer, and CI for zero organizational gain.

**Claude Code adjustment.** The agent entry point is `CLAUDE.md` at the repository root because Claude Code loads it automatically at session start — the harness engages without relying on the agent choosing to read it. It carries a digest of the conventions, the precedence rule, pointers into `meta/`, the session protocol from Section 9, and the machine/environment quirks currently in `project_guide.md` Section 7 (entry-point material: an agent must know about the interpreter and PATH quirks *before* running anything).

## 5. Global track: artifacts and their jobs

### 5.1 `charter.md` — the global seed document

Extraction of Sections 1–3, so the objectives and their history are auditable rather than implicit. The charter adds a **global exit criterion to every local phase**: a phase is not done until its logs are current, the graph validates, and provenance is recorded for its artifacts.

### 5.2 `conventions.md` — working agreements

The Section 2 instruction set mirrored verbatim, plus the redaction rule and the trigger table from Section 9. Any future amendment to the conventions is itself a logged decision.

### 5.3 `provenance.md` — contribution transparency

- **Three-level taxonomy**, applied to every committed artifact:
  - `H` — human-authored.
  - `HD` — human-directed: agent drafted from specific human instructions, human edited and approved. The directing prompt is a candidate for `logs/prompts.md`.
  - `A` — agent-drafted, human-reviewed only.
- **Mechanics:** git commit trailers (`Provenance: HD`, `Directs: <prompt-log id>`) make commits the ground truth; `provenance.md` maintains a per-artifact ledger for evaluator convenience. Design docs carry a provenance line in their front matter, as this document does.
- **Backfill honestly.** Stage 0–1.5 artifacts get retroactive provenance entries reflecting what actually happened. The retrieved founding chat makes this concrete: `design.md` is `HD` (author's brief, agent's draft); `project_guide.md` is `A` (it states it was written from the agent's perspective); the hidden-crosswalk concept is jointly attributable, and saying so precisely is exactly the kind of honesty instruction 10 demands.

### 5.4 `logs/` — the three record types

- `interventions.md` — the centerpiece. Fixed schema per entry: id, date, phase, what the agent did or proposed, **classification** (agent misread a clear doc, versus the doc was ambiguous and got clarified), the specific human guidance (quoted), resolution, and a reference to any resulting doc change. The fictional-name reversal is the inaugural entry and a model example: the agent introduced fictional naming with a defensible rationale (confidentiality), the human overruled it as meaningless, and the resolution (descriptive naming, Section 8 item 1) satisfies both concerns.
- `prompts.md` — significant prompts verbatim minus marked redactions. Seed entries from the founding chat: the dataset-scouting prompt and the full design brief. The Stage-2 instruction set is recorded as the third entry — it is the most impactful steering input the project has received.
- `decisions.md` — ADR log covering both tracks, **seeded by migrating the A/B/C-series tables from `project_guide.md` Section 5 with their existing ids preserved** (A1–A6, B1–B5, C1–C8), plus its "interpretations of ambiguous design points" and open questions. Those tables are already well-formed decision records; they just live in the wrong document and predate the id/citation discipline.

### 5.5 `graph/` — the knowledge graph and repo index

- `graph.yaml`: node types `document`, `directory`, `phase`, `dataset`, `silo`, `model`, `decision`, `log-entry`; edge types `implements`, `calibrates`, `gates`, `depends-on`, `documents`, `corrected-by`. Human-readable, diffable, cheap for an agent to load at session start.
- `validate_graph.py` runs in CI: every node's `path` must exist; every phase must have at least one `gates` edge; warn on files unreachable from any node. **Any structural change to the repo ships with a graph diff in the same commit.**

## 6. Local track: reconciling the existing documents

- **`docs/design.md`** remains authoritative for the local workload. Additions: a versioned changelog citing intervention/decision ids; provenance front matter; a reframing sentence in its executive summary linking to `meta/charter.md`; and a site-plan addition — a "How this was built" page generated from `meta/`, making the global track publishable content.
- **`project_guide.md`** is kept — it earned its place — but split along the global/local seam:
  - *Moves to `meta/logs/decisions.md`:* Section 5's decision tables and interpretations (ids preserved), Section 8's open questions.
  - *Moves to `CLAUDE.md`:* Section 7's machine and environment quirks.
  - *Stays, updated:* current state (Section 4), phase guidance (Section 6), constraints (Section 3) — rewritten for the corrections below. Its "Objectives, ranked" list gets the global objective inserted at rank 1, demoting "career artifact" to the top *local* objective; its instruction to "keep the narrative voice fictional (e.g., a named fictional company's engineering team)" is amended to *descriptive* voice ("the marketplace's engineering team"), which preserves the confidentiality intent without a fictional name.
- **`docs/calibration_spec.md`** stays, gains front matter, version status aligned with the design doc.

## 7. Design-doc lifecycle

The design doc is live, per instruction 12. Every change is triggered — by an intervention, a decision, or drift found in review — and the trigger id appears in the changelog entry. A short weekly pass confirms the doc still matches implementation reality; drift found in that pass is itself logged. Versions advance per document, independently, with cross-references stating the companion version they were written against.

## 8. Corrections to apply during migration (things that look off)

Each fix becomes a seed entry in `logs/interventions.md`.

1. **Fictional company name — now including live cloud resources.** The name violates instruction 5 across `design.md`, `calibration_spec.md`, `README.md`, `project_guide.md`, and — per the guide's Section 4 — three provisioned resources: the S3 bucket, the BigQuery project id, and the BigQuery dataset. None of these support in-place rename, but **all are cheap to recreate while the silos are empty, which is exactly the current window** — after Phase 2 loads data, this becomes a migration project. Recommendation: before Phase 2, recreate the bucket and dataset under Tributary-derived names (e.g., `tributary-auction-lake-jb`, dataset `marketing`); for the GCP project id (immutable, requires a replacement project with billing, budget, and auth re-linked), decide replace-versus-accept-and-document as an explicit `decisions.md` entry. In prose everywhere, replace the name with "the simulated marketplace" / "the exchange"; simulated buyers get structured identifiers (`buyer_t2_004`), not invented company names. Also fixes en route: the design doc's example S3 path omits the real bucket's suffix. *(Resolved at adoption: decision D3 — executed 2026-08-03.)*
2. **Sensitive identifiers in a public repo.** `project_guide.md` Section 4 embeds the AWS account id and personal email addresses, and the guide's own open question 2 records the repo as currently public — in tension with the guide's own secrets-hygiene constraint. Account ids and emails are not credentials, but neither belongs in public: scrub them from all committed files (pointer language or a git-ignored local supplement, e.g. `meta/local/identifiers.md`), and resolve open question 2 (repo visibility) as an explicit decision. Recommendation: private until the first publishable milestone, since early harness logs will be messy and redaction discipline is still being established. *(Resolved at adoption: decision D1 — the human chose to stay public and rewrite git history to scrub the identifiers instead.)*
3. **Employer-name redaction rule.** The founding chat names the author's employer; the confidentiality constraint must therefore extend explicitly to `meta/` — prompt-log and history entries are committed only after redaction, with redactions marked. Codified in `conventions.md`.
4. **Stale admin credential.** The guide flags "consider deactivating" the admin IAM user's access key; per instruction 6, do it — deactivate the key now, re-enable only for infra sessions. *(Sequencing amendment at execution: the key is deactivated at the end of the migration, after step 4's bucket/dataset recreation, which itself requires admin credentials. See INT-006.)*
5. **Emoji in design.md.** The warning symbol prefixing the confidentiality note violates instruction 4; replace with the words "Confidentiality note:".
6. **Placeholder author line.** `Author: [Your Name]` in design.md — resolve or remove.
7. **Roadmap has no global deliverables.** Add the global exit criterion (logs current, graph validates, provenance recorded) to every phase; add the harness build itself as a reopened Phase 0 item or a Phase 0.5, since the README marks Phase 0 complete while the harness does not exist.
8. **Version inconsistency.** design.md "v1.0" versus its authoritative companion calibration spec at "Draft v0.1"; adopt the Section 7 scheme.
9. **README duplication risk.** Keep the README a thin router — pitch, two-track explanation, repo map, quickstart — and link to the design doc for everything else, so there is one source of truth per fact.

## 9. Operating loop: how global records local work

Applies to every Claude Code session (and any other agent environment).

**Session protocol.**

1. *Start:* Claude Code auto-loads `CLAUDE.md`; the agent reads `conventions.md` and `graph.yaml`, then states which phase and which design-doc sections govern the session.
2. *Work:* local-track work proceeds under the conventions.
3. *End:* agent drafts candidate records — intervention entries (if corrected), prompt-log candidates (if a prompt was pivotal), decision entries (if a choice with alternatives was made), design-doc deltas (if implementation revealed a gap), and a graph diff (if structure changed).
4. *Review:* human accepts, edits, or rejects each record; commits carry provenance trailers. The human review step keeps the logs honest — agents propose records, humans ratify them.

**Trigger table (mandatory records).**

| Event during local work | Required global record |
| --- | --- |
| Human corrects an agent misunderstanding of the design doc | `interventions.md` entry, with classification |
| Design doc changes for any reason | design.md changelog entry citing an intervention or decision id |
| A choice is made between real alternatives | `decisions.md` entry |
| Repo structure changes | `graph.yaml` diff in the same commit |
| A prompt materially shaped an artifact | `prompts.md` candidate entry (redacted per Section 8, item 3) |
| Something off-topic is found and fixed | `interventions.md` entry flagged "en-route fix" |

**Cadence:** graph validation runs in CI on every push; the weekly design-doc drift pass per Section 7.

## 10. Migration sequence

Ordered, roughly one working session each, executed in Claude Code. **Nothing in Phase 1 (simulation) starts until step 7 is done**, so all Phase 1 work is captured by the harness from its first commit — and critically, the resource renames in step 4 happen while the silos are still empty.

1. Transfer this document into the repository as `meta/plan.md` (provenance `HD`); create root `CLAUDE.md` per Section 4, absorbing the machine-quirks content from `project_guide.md` Section 7.
2. Scaffold the rest of `meta/`: extract charter and conventions from Sections 1–3 (including the redaction rule), write the provenance spec, create the logs. Seed `decisions.md` from the guide's A/B/C tables (ids preserved); seed `prompts.md` with the two founding prompts (redacted) and the Stage-2 instruction set; seed `interventions.md` with the fictional-name reversal as the worked example.
3. Slim `project_guide.md` per Section 6 (decision tables out, objectives re-ranked, narrative-voice guidance amended); scrub sensitive identifiers from all committed files; record the repo-visibility decision; deactivate the admin access key. *(Execution amendment: key deactivation moved after step 4 — see Section 8, item 4.)*
4. Execute the naming corrections: recreate the S3 bucket and BigQuery dataset under Tributary-derived names while empty; record the GCP-project-id decision (replace versus accept-and-document); update `.env`, infra scripts, and doc references; sweep the fictional name from all prose.
5. Apply the remaining Section 8 corrections to `docs/design.md`, `docs/calibration_spec.md`, and `README.md`; write the corresponding intervention entries; backfill provenance for all Stage 0–1.5 artifacts per Section 5.3.
6. Build `graph.yaml` covering the repo and document structure; write `validate_graph.py`; wire into CI (or a pre-commit hook until CI exists).
7. Update the design-doc roadmap with global exit criteria; reopen or split Phase 0 in the README status list; confirm the revised Phase 0 passes its own new gates.
8. Resume Phase 1 under the operating loop.

## 11. What the evaluator sees

The decomposition path for an outside reviewer, using only committed material: `charter.md` states what the human set out to prove and how the framing evolved — including that the meta layer began emerging organically (`project_guide.md`) before it was formalized; `conventions.md` shows the standing rules the human imposed; `prompts.md` and `interventions.md` show the human steering in real time, including the inaugural example of the human overruling a defensible agent choice; `provenance.md` plus commit trailers show who produced each artifact, with honest joint attribution where that is the truth; and the git history is the ground truth behind all of it. The end product is not asked to look effortless — the harness and its records *are* the product, with the data science build as the demonstration payload.
