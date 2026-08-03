# Tributary — Charter

Status: v1.0, extracted 2026-08-03 from `meta/plan.md` (v0.3, adopted) Sections 1–3
Provenance: HD — agent-drafted from the human instruction set; human-adopted with the plan

---

## 1. What this project is — read this first

**Tributary is not only an end-to-end data science project.** It is a dual-track project, and the data science build is the subordinate track.

- **The global track (primary).** The objective is to demonstrate that the human author can direct AI agents to get real work done: designing the harness that makes agents more effective than out-of-the-box, maintaining transparent decomposition of human contribution from agent contribution, and keeping an honest record of corrections, guidance, and decisions. The standing instruction set in `meta/conventions.md` *is* the global objective — it is not commentary on the project; it defines the project.
- **The local track (the workload).** The end-to-end data science build specified in `docs/design.md` and operationalized in `project_guide.md`: simulation of a fractured lead-marketplace data environment, silo deployment, entity resolution, analytics, and ML optimization. It is a genuine deliverable, but it is the demonstration payload, not the thesis.

**Precedence rule.** Where the global instruction set conflicts with the local documents, the global instruction set wins. Every such conflict is resolved by amending the local document and logging the amendment (`meta/logs/interventions.md`).

Any agent joining this project must internalize this ordering before touching the local work. Optimizing the data science output while neglecting the records, provenance, and harness duties is a failure of the project's primary objective, even if the code is excellent.

## 2. Global exit criterion (applies to every local phase)

A local-track phase is **not complete** until, in addition to its own exit criteria in `docs/design.md` Section 9:

1. `meta/logs/` is current — interventions, decisions, and prompt candidates for the phase are recorded;
2. `meta/graph/graph.yaml` validates (`validate_graph.py` passes) and reflects any structural changes;
3. provenance is recorded for every artifact the phase produced (commit trailers + `meta/provenance.md` ledger).

## 3. How the project got here (firsthand history)

Grounded in the retrieved founding chat transcript plus `project_guide.md`. One deliberate omission: the founding chat identifies the author's employer by name; per the confidentiality constraint, the employer is never named in any committed document, including this history.

- **Stage 0 — dataset scouting (chat: "Finding similar project datasets online").** The opening prompt asked for public datasets similar to the data the author works with professionally (lead-generation marketplace auctions). The agent surveyed candidates — iPinYou RTB, Criteo (click, conversion, and uplift datasets), LendingClub accepted/rejected loans, YOYI, Home Credit — and recommended combining iPinYou (auction mechanics), LendingClub (loan-vertical features), and Criteo Uplift (marketing treatment structure), noting that no public dataset mirrors a lead-gen waterfall directly.
- **Stage 1 — the design brief and design doc (same session).** The author's second prompt set the full brief: a portfolio project resembling the day job, covering data organization and storage, analytics, and ML optimization strategy; an explicit request to showcase the data silo problem via simulated data with imposed unifying keys; cloud storage/read/write cost analysis; a VS Code-to-cloud workflow explanation; a PM-voice roadmap; and a public site doubling as a professional profile. The agent drafted `design.md` v1.0 in response. Two provenance facts worth preserving: the silo-simulation-with-hidden-crosswalk concept was seeded by the author's "impose unifying keys on simulated data" idea and elaborated by the agent; and the fictional company name was introduced *by the agent* as a confidentiality device. Both founding prompts are the first entries in `meta/logs/prompts.md`.
- **Stage 1.5 — execution in Claude Code.** Phase 0 was completed against the v1.0 design: repo scaffold, devcontainer, simulation package skeleton with frozen stage contracts, and provisioned cloud silos with budget alarms on both clouds. The Claude Code agent wrote `project_guide.md` — a proto-meta layer that emerged organically because the work needed it, before any instruction demanded it — but written entirely in the Stage-1 frame (fictional company name throughout, "career artifact" as the primary objective, no harness or provenance apparatus).
- **Stage 2 — the reframing.** The standing instruction set arrived and changed what the project is about: the working method became the primary exhibit. It retroactively put the Stage-1 artifacts out of compliance — the fictional name (then baked into live cloud resource names), an emoji in the design doc, no provenance records, no logs, no knowledge graph, no global deliverables in the roadmap.
- **Stage 3 — formalization and transfer.** `meta/plan.md` made the shift structural: a global/local split, the instruction set promoted to a normative charter, `project_guide.md` reconciled into the split, a migration executed 2026-08-03 to bring Stage-1 artifacts into compliance (see decisions D1–D3 and interventions INT-001 through INT-008), and execution continuing in Claude Code under the operating loop.

**Operational consequence:** `docs/design.md` is authoritative for *what the local workload is*; `project_guide.md` for *the local workload's current state and working guidance*; `meta/plan.md` and its extractions for *what the project is and how it is run*.
