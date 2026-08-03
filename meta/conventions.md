# Tributary — Working Agreements (Conventions)

Status: v1.0, 2026-08-03. Mirrors the standing instruction set from `meta/plan.md` Section 2 verbatim, plus the redaction rule and the operating-loop trigger table. Any future amendment to this file is itself a logged decision in `meta/logs/decisions.md`.
Provenance: H (instructions 1–12 are the human's standing instruction set, restated verbatim); assembly HD

---

## 1. The standing instruction set (normative, verbatim)

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

## 2. Redaction rule

The confidentiality constraint extends explicitly to `meta/`:

- The author's **employer is never named** in any committed file — including prompt-log entries, history narratives, and intervention quotes. Where source material names the employer, the committed version redacts it and marks the redaction in place: `[REDACTED: employer]`.
- **Sensitive identifiers** (cloud account ids, personal email addresses) are never committed. Committed documents use pointer language ("the account id in the AWS console"); real values live in `.env`, `~/.aws/credentials`, and other git-ignored locations.
- Prompt-log entries are recorded **verbatim minus marked redactions** — this is the reconciliation of instruction 9 (verbatim prompts) with the confidentiality constraint.
- Fictionalization of the scenario itself is preserved (the simulated marketplace is not the author's employer), but per instruction 5 the scenario goes **unnamed**: descriptive terms ("the simulated marketplace", "the exchange") or structured identifiers (`buyer_t2_004`), never invented company names.

## 3. Trigger table (mandatory records during any work session)

| Event during local work | Required global record |
| --- | --- |
| Human corrects an agent misunderstanding of the design doc | `meta/logs/interventions.md` entry, with classification |
| Design doc changes for any reason | design.md changelog entry citing an intervention or decision id |
| A choice is made between real alternatives | `meta/logs/decisions.md` entry |
| Repo structure changes | `meta/graph/graph.yaml` diff in the same commit |
| A prompt materially shaped an artifact | `meta/logs/prompts.md` candidate entry (redacted per Section 2) |
| Something off-topic is found and fixed | `interventions.md` entry flagged "en-route fix" |

**Session protocol:** at start, read this file and `meta/graph/graph.yaml`, then state which phase and design-doc sections govern the session. At end, draft candidate records for human review — agents propose records, humans ratify them. **Cadence:** graph validation runs on every push; a short weekly pass confirms the design doc still matches implementation reality, and drift found in that pass is itself logged.
