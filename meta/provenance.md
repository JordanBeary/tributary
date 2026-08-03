# Tributary — Provenance: Contribution Transparency

Status: v1.0, 2026-08-03
Provenance: HD — spec drafted by the agent from `meta/plan.md` Section 5.3; backfill entries reflect the retrieved founding-chat history

The purpose of this file: make it simple for an evaluator to decompose the human's contributions from an AI taking a seed and running with it (conventions, instruction 2). Git commit trailers are the ground truth; the ledger below is the evaluator-convenience view.

---

## 1. Taxonomy

Applied to every committed artifact:

| Level | Meaning |
| --- | --- |
| `H` | Human-authored. |
| `HD` | Human-directed: agent drafted from specific human instructions; human edited and approved. The directing prompt is a candidate for `logs/prompts.md`. |
| `A` | Agent-drafted, human-reviewed only. |

## 2. Commit trailer spec

Every commit carries:

```text
Provenance: H | HD | A
Directs: <prompt-log id>        (optional — the prompt that directed this work)
```

Design documents additionally carry a provenance line in their front matter.

Commits carry **no AI co-author trailers** (`Co-Authored-By: Claude ...` or similar) — the human's standing decision (INT-010). Contribution attribution is expressed solely through the `Provenance:`/`Directs:` trailers and this ledger, which say something precise; a boilerplate signature says nothing.

## 3. Ledger

Backfilled entries (Stage 0–1.5, pre-harness) reflect what actually happened, per the retrieved founding chat; they are marked `[backfill]`.

| Artifact | Provenance | Notes |
| --- | --- | --- |
| `docs/design.md` | HD `[backfill]` | Author's full design brief (P-002); agent drafted v1.0. The silo-simulation-with-hidden-crosswalk concept is **jointly attributable**: the author seeded "impose unifying keys on simulated data"; the agent elaborated the hidden-crosswalk scoring mechanism. The fictional company name was the agent's addition (since reversed, INT-001). |
| `docs/calibration_spec.md` | A `[backfill]` | Agent-proposed quantitative assumptions (C1–C8) beyond the design doc's letter; human-reviewed. |
| `project_guide.md` | A `[backfill]` | Written from the agent's perspective during Phase 0; the human reviewed. A proto-meta layer that emerged organically before the harness existed. |
| `simulation/` package skeleton | A `[backfill]` | Stage contracts frozen by the agent per A2; human-reviewed. |
| `infra/` scripts | A `[backfill]` | Agent-drafted Phase 0 setup scripts; human ran and verified them. |
| `README.md` | A `[backfill]` | Agent-drafted; rewritten 2026-08-03 as the two-track router (HD, per plan Section 8 item 9). |
| `meta/plan.md` | HD | Agent-drafted from the human instruction set and retrieved session history; human-adopted with three explicit decisions (D1–D3). |
| `meta/charter.md`, `meta/conventions.md` | HD | Extractions of the plan; the instruction set inside conventions is `H` verbatim. |
| `meta/provenance.md` (this file) | HD | Spec from plan Section 5.3. |
| `meta/logs/interventions.md` | HD | Schema from plan Section 5.4; entries record human guidance verbatim where available. |
| `meta/logs/prompts.md` | HD | Entries are the human's prompts (H content) in an agent-assembled log. |
| `meta/logs/decisions.md` | HD | Seeded from `project_guide.md` A/B/C tables (A `[backfill]`) plus adoption decisions D1–D3 (H decisions, agent-recorded). |
| `meta/graph/graph.yaml`, `validate_graph.py` | A | Agent-built index and validator per plan Section 5.5. |
| `CLAUDE.md` | HD | Digest of human conventions plus environment knowledge; structure per plan Section 4. |
