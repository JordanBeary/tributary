# Intervention Log

Agent errors corrected, with the specific human guidance that corrected them (conventions, instruction 3). Schema per entry: id, date, phase, what the agent did or proposed, classification, the human guidance, resolution, and the resulting doc change.

Classification values:

- `misread` — the agent misread a clear document
- `ambiguity` — the document was ambiguous and got clarified
- `overrule` — the human overruled a defensible agent choice
- `en-route fix` — something off-topic found and fixed along the way (instruction 6)
- `omission` — the agent failed to run a check that available information already supported (added with INT-014)

Entries INT-001 through INT-008 were seeded during the 2026-08-03 reorganization migration (`meta/plan.md` Section 8); INT-009 was backfilled from the founding-session log when it was committed.

---

## INT-001 — Fictional company name reversed (the inaugural worked example)

- **Date:** 2026-08-03 (agent choice made Stage 1, 2026-07; overruled Stage 2)
- **Phase:** 0 / migration
- **What the agent did:** During the founding chat, the agent introduced a fictional company name for the simulated marketplace as a confidentiality device ("so nothing proprietary from your actual employer ends up on a public site"). The name then propagated into `design.md`, `calibration_spec.md`, `README.md`, `project_guide.md`, the simulation package docstrings, and three live cloud resources (the S3 bucket, the BigQuery project id, and the BigQuery dataset).
- **Classification:** overrule — the agent's rationale was defensible, but the human judged the device itself meaningless.
- **Human guidance:** "No fictional names for hypothetical entities. A fictional company name is meaningless; use descriptive terms or structured identifiers instead." (standing instruction 5)
- **Resolution:** Descriptive naming satisfies both concerns — the scenario stays fictionalized (confidentiality preserved) but unnamed. Prose now uses "the simulated marketplace" / "the exchange"; simulated buyers get structured identifiers (`buyer_t2_004`). Cloud resources were recreated under Tributary-derived names while the silos were still empty (decisions D2, D3): S3 bucket `tributary-auction-lake-jb`, GCP project `tributary-jb`, BigQuery dataset `marketing`. En-route fix folded in: the design doc's example S3 path had also omitted the real bucket's suffix.
- **Doc changes:** design.md v1.1 changelog; `project_guide.md` narrative-voice guidance amended from "fictional" to "descriptive"; `.env`, `.env.example`, `infra/` scripts, `pyproject.toml`, simulation docstrings updated.

## INT-002 — Sensitive identifiers committed to a public repo

- **Date:** 2026-08-03 (introduced 2026-07-31)
- **Phase:** 0 / migration
- **What the agent did:** Wrote the AWS account id and two personal email addresses into `project_guide.md` Section 4 while the repo was public — in tension with the guide's own secrets-hygiene constraint. Not credentials, but identifiers that do not belong in public.
- **Classification:** en-route fix (agent error caught in the plan's review pass, not by a runtime human correction)
- **Human guidance:** Adoption decision D1 — the human chose to keep the repo public and rewrite git history to scrub the identifiers, rather than the plan's recommended private-until-milestone route.
- **Resolution:** Identifiers scrubbed from all committed files (pointer language instead); git history rewritten with replace-text filters and force-pushed so old commits no longer expose them. The git author email remains visible in commit metadata by the human's acceptance (it is their public git identity).
- **Doc changes:** `project_guide.md` Section 4 rewritten with pointers; redaction rule codified in `meta/conventions.md` Section 2.

## INT-003 — Emoji in the design doc

- **Date:** 2026-08-03 (introduced Stage 1)
- **Phase:** 0 / migration
- **What the agent did:** Prefixed the design doc's confidentiality note with a warning-symbol emoji.
- **Classification:** en-route fix (violates standing instruction 4, which postdates the artifact)
- **Human guidance:** "No emojis. Anywhere in the repository." (standing instruction 4)
- **Resolution:** Replaced with the words "Confidentiality note:". Repo-wide sweep confirmed no other emojis in committed text.
- **Doc changes:** design.md v1.1 changelog.

## INT-004 — Placeholder author line

- **Date:** 2026-08-03 (introduced Stage 1)
- **Phase:** 0 / migration
- **What the agent did:** Left `Author: [Your Name]` in the design doc header.
- **Classification:** en-route fix
- **Human guidance:** Plan Section 8 item 6 ("resolve or remove"), human-adopted.
- **Resolution:** Resolved to the author's name.
- **Doc changes:** design.md v1.1 header.

## INT-005 — Stale admin credential left active

- **Date:** 2026-08-03
- **Phase:** 0 / migration
- **What the agent did:** Flagged the admin IAM user's access key as "consider deactivating" in `project_guide.md` but left it active after Phase 0 setup ended.
- **Classification:** en-route fix
- **Human guidance:** "If something clearly looks wrong ... get it fixed along the way." (standing instruction 6; plan Section 8 item 4: "do it")
- **Resolution:** Key deactivated at the end of the migration's infra work. Standing practice recorded in `CLAUDE.md`: re-enable only for infra sessions, deactivate after.
- **Doc changes:** `CLAUDE.md` machine-quirks section; `project_guide.md` Section 4.

## INT-006 — Migration-order defect in the plan itself

- **Date:** 2026-08-03
- **Phase:** migration
- **What the agent did/found:** The adopted plan sequenced admin-key deactivation in migration step 3, before step 4's bucket/dataset recreation — which requires admin credentials. Executing as written would have blocked the infra work (or forced an immediate re-enable).
- **Classification:** en-route fix (defect in the plan document, found during execution review)
- **Human guidance:** Surfaced at adoption; human raised no objection to the proposed swap.
- **Resolution:** Deactivation moved to after the infra work. Amendment noted in `meta/plan.md` Sections 8 and 10.
- **Doc changes:** `meta/plan.md` execution amendments.

## INT-007 — Version inconsistency across companion documents

- **Date:** 2026-08-03 (introduced Stage 1–1.5)
- **Phase:** 0 / migration
- **What the agent did:** Stamped design.md "v1.0" while its authoritative quantitative companion, the calibration spec, sat at "Draft v0.1" with no cross-reference discipline.
- **Classification:** en-route fix
- **Human guidance:** Plan Section 8 item 8, human-adopted.
- **Resolution:** Per-document versioning adopted (plan Section 7): versions advance independently; cross-references state the companion version they were written against; every change cites its trigger id in a changelog.
- **Doc changes:** design.md v1.1 front matter and changelog; calibration_spec.md front matter.

## INT-008 — Roadmap had no global deliverables

- **Date:** 2026-08-03
- **Phase:** 0 / migration
- **What the agent did:** Built the Phase 0–7 roadmap and marked Phase 0 complete with purely local exit criteria — while the harness (the project's primary exhibit) did not exist.
- **Classification:** en-route fix (consequence of the Stage-2 reframing, not an original error)
- **Human guidance:** Standing instructions 9 and 12; plan Section 8 item 7, human-adopted.
- **Resolution:** Global exit criterion added to every phase (logs current, graph validates, provenance recorded — `meta/charter.md` Section 2). The harness build recorded as Phase 0.5 in the README status list, completed by this migration.
- **Doc changes:** design.md v1.1 roadmap; README status list.

## INT-009 — Design-doc tagline overweighted the silo problem `[backfill]`

- **Date:** 2026-07 (founding chat, Turns 3–4; backfilled 2026-08-03 from `sessions/2026-07_founding_design_session.md`)
- **Phase:** design (pre-Phase 0)
- **What the agent did:** Led the freshly drafted design doc with the tagline "A unified lead-marketplace analytics & ML optimization platform, built to showcase the data silo problem end-to-end" — elevating one showcase element to the project's stated objective.
- **Classification:** misread — the brief (P-002) named organize/store, analyze, and ML-strategy as the objective, with the silo problem as something to showcase "in some way".
- **Human guidance:** "The objective is not to 'showcase the data silo problem end-to-end' - that is just one element I would like to showcase. The highest level objective is showcase my work." (Turn 3, verbatim)
- **Resolution:** Agent reframed and offered three variants; the human selected the recruiter-facing one (Turn 4): "An end-to-end data science build: engineering fractured marketplace data into unified analytics and ML-driven auction optimization." — now the standing one-liner in the design doc and README.
- **Doc changes:** design doc tagline (pre-repo; visible in the session log).

## INT-010 — AI co-author trailer on commits rejected

- **Date:** 2026-08-03
- **Phase:** 1 (dataset acquisition)
- **What the agent did:** Appended its harness's default `Co-Authored-By: Claude ...` trailer to every commit it authored (six commits by the time of correction).
- **Classification:** overrule — the agent followed a tool default; the human rejected it as noise given the project's explicit provenance system.
- **Human guidance:** "I do not want the Co-Authored by Claude Fable 5 signature on any work ever." (verbatim)
- **Resolution:** Trailer stripped from all existing commit messages via a message-only history rewrite (second force-push; commit contents untouched). Rule codified so it binds future sessions and any agent harness: `meta/provenance.md` Section 2 and `CLAUDE.md`. Attribution continues exclusively through `Provenance:`/`Directs:` trailers and the ledger.
- **Doc changes:** `meta/provenance.md`; `CLAUDE.md`.

## INT-011 — Sentinel values winsorized into a shipped marginal; data mutations were invisible

- **Date:** 2026-08-03
- **Phase:** 1 (LendingClub profiling)
- **What the agent did:** Shipped `lendingclub_marginals.json` with accepted-file `dti = 999` sentinel records (135 rows at the exact cap value) winsorized *into* the DTI marginal rather than excluded, and with all data-altering operations (drops, NaN-coercion, clipping, imputation) performed without a visible accounting. The agent had caught the rejected file's negative-DTI sentinel on its own but missed the accepted file's 999 twin.
- **Classification:** ambiguity — the calibration spec prescribed 1%/99% winsorization but was silent on sentinel policy and on mutation transparency; the human's review of `describe()` output (max DTI 999, max income $110M) forced an explicit policy.
- **Human guidance:** "This looks suspicious - is this valid data or a sentinel record? In the data cleaning and QA pipeline can you take extra measures to highlight any processes that changes the data itself (row deletion for sentinel values or too many NA/null values, imputing values, etc). Are those rows included in computing the marginals?" (verbatim, P-005)
- **Resolution:** Empirical triage of each extreme (loan cap and FICO cap valid; dti 999 a hard sentinel, set NaN; $110M income implausible but structureless, winsorized with counts reported). A **data-mutation ledger** added to the notebook: every altering operation recorded with row counts, disposition, and rationale, printed in the executed notebook and embedded in the params JSON metadata. The ledger immediately revealed the negative-DTI sentinel covers 180k sampled rows (~4.3%) — previously clipped to the winsor floor. Convention codified in `docs/calibration_spec.md` v0.2 for all profiling notebooks.
- **Doc changes:** `docs/calibration_spec.md` v0.2 (Section 0 ledger convention + changelog); notebook and params regenerated (commit `a2f4329`).

## INT-012 — Fitting without narrated understanding; EDA made a standing deliverable

- **Date:** 2026-08-04
- **Phase:** 1 (iPinYou profiling)
- **What the agent did:** Built and shipped the fitting notebooks straight to parameter extraction. The foundational understanding — what the dataset *is* (one DSP's diary, not the market), the bidding mechanics, the data dictionary, structural collinearity (city→region, creative→advertiser nesting), the fixed-bid caveat, the one-advertiser-per-auction fact — existed implicitly in the fitting choices but was never surfaced as a narrated, committed analysis. The human had to ask for it in chat.
- **Classification:** ambiguity — the spec's deliverables checklist defined fitting notebooks and QA gates but was silent on exploratory analysis as a first-class artifact; the human's review established that understanding must be demonstrated, not just embodied.
- **Human guidance:** "This information should always be surfaced - let's proceed with your plan. Keep both of the existing notebooks but add an addtional notebook (*_eda.ipynb) that investigates these foundational truths and narrates throughout. Log this to meet our global objectives." (verbatim, P-006)
- **Resolution:** EDA-companion convention codified (spec v0.4, Section 0): every source dataset gets a read-only, narrated `*_eda.ipynb` — provenance and mechanics, sample rows, data dictionary (type/distinct/nulls/definition), descriptive statistics with semantics, collinearity and nesting structure, known data quirks, declared assumptions, and business implications for the project. `02a_ipinyou_eda.ipynb` built as the first instance; `01a_lendingclub_eda` and `03a_criteo_eda` added to the checklist.
- **Doc changes:** `docs/calibration_spec.md` v0.4 (Section 0 convention, Section 5 checklist, changelog).

## INT-013 — Agent mischaracterized a valid out-of-domain estimate as "wrong-sign"

- **Date:** 2026-08-07 (drafted by the human in a review session without repo access; merged into this log with ids mapped — the draft's `AE-001`/`D-007` are this entry and C9)
- **Phase:** 1 (calibration) · **Severity:** low (documentation framing; no code or parameter values affected)
- **What the agent did:** When drafting the decision-log entry for the iPinYou elasticity finding, framed the fitted −0.149 slope as a "wrong-sign estimate" and the resolution as correcting an artifact. This misattributes the problem to the fit. The regression is statistically sound and accurately describes its source market; the issue is **external validity** — the estimate measures a structurally different price-quality mechanism than the target market's and therefore does not transfer.
- **Classification:** misread — the agent mislabeled the epistemics of its own finding.
- **Human guidance:** "It isn't technically wrong — it just isn't suitable for the purpose of modeling downstream." Directed reframing from "wrong estimate, overridden" to "valid estimate, out-of-domain for the target, declared override with the empirical value preserved."
- **Why the distinction matters:** (1) It changes what the record demonstrates — overriding a bad estimate is unremarkable; recognizing that a *good* estimate fails transferability is the calibration-judgment story the design doc's risk register anticipates ("simulation realism questioned in interviews"). (2) It keeps the profiling notebook honest: the empirical value is archived as correct, not flagged as anomalous — a stronger form of transparency.
- **Agent counter-contribution accepted:** The human's initial characterization of the resolution as a "gentle intervention" was flagged by the agent as understating magnitude — the override discards both sign and level of the fitted slope. Adopted phrasing: "declared override with the empirical value preserved."
- **Resolution:** C9 rewritten under the transferability framing (expanded record in `decisions.md`); notebook rationale text reframed to "correct in-domain, non-transferable"; a follow-on QA gate added so the declared elasticity is verified end-to-end rather than trusted (Spearman of `q` vs realized clearing price on sold leads > 0.3).
- **Doc changes:** `meta/logs/decisions.md` C9 (ratified with reframing); `docs/calibration_spec.md` v0.5 (Section 2 row and gate); gate implemented in the `02_ipinyou` builder.
- **Follow-up (same day):** the newly implemented gate **falsified the current parameterization** — Spearman(q, price) on sold leads is ~0.00 against the >0.3 threshold, because tier assignment is dominated by q-independent participation and 93% of prices sit at tier floors. Elasticity magnitude alone cannot pass it (EL=5 reaches only 0.265); q-dependent participation alone is also insufficient (0.09 at strong settings). The Section 5 checklist item for `02_ipinyou` is reopened; resolution options are before the human (see C9 expanded record, follow-up note).

## INT-014 — Agent ratified a parameter and its verification gate without a feasibility check

- **Date:** 2026-08-07 (human-drafted as `AE-002`; merged with ids mapped)
- **Phase:** 1 (calibration) · **Severity:** moderate (process failure; caught before any downstream consumer of the parameter)
- **What the agent did:** Proposed and wired in, in the same breath, the declared elasticity of +1.0 and the Spearman(q, price) > 0.3 verification gate — without checking whether the pair was jointly satisfiable. The incompatibility was **computable at ratification time**: sd(q) ≈ 0.164 was knowable from the fitted score being squashed into 0.6–1.0, and σ ≈ 0.912 was already sitting in the iPinYou artifact. The signal-to-noise ratio of 0.18 was one line of arithmetic that was never run.
- **Classification:** omission — no new computation was required, only the application of numbers already in committed artifacts.
- **Human guidance:** "This incompatibility was computable at ratification time. ... That's [an agent error]: agent ratified a parameter and its verification gate without a feasibility check that required no new computation. Your harness caught in one run what should have been caught on paper." (verbatim, condensed)
- **Resolution:** The falsification stands as part of the record (C9 superseded by C11, not edited in place). Standing practice going forward: a declared parameter proposed together with its verification gate must ship with the back-of-envelope feasibility arithmetic in the proposal itself.
- **Doc changes:** `meta/logs/decisions.md` C9 supersession line + C11; this entry.

## INT-015 — Vague decision requests; explicit-ask protocol adopted

- **Date:** 2026-08-12
- **Phase:** 1 (wrap) · **Severity:** low (communication; no artifacts affected)
- **What the agent did:** Ended a session summary with "Pending your ratification: C10, C15, C16, C17" — a bare list of decision ids with no statement of what each decision was, what ratifying would mean, what to examine before deciding, or what would happen on rejection. The human had to ask what was actually being requested.
- **Classification:** omission — the harness's propose-then-ratify loop (conventions Section 3 session protocol) presumes the human can act on a proposal, and a proposal whose ask is implicit is not actionable.
- **Human guidance:** "Make a note to be very clear and direct about what decisions you want me to make. For example, what specifically do you mean by saying 'Pending your ratification'?" (verbatim, P-009)
- **Resolution:** Standing protocol for decision requests, effective immediately: each open decision is presented as (1) a one-sentence statement of what was decided and why, (2) the concrete question — usually accept / amend / reject, (3) what each answer entails downstream, and (4) the agent's recommendation. Bare id lists are not decision requests. Applied in the same session to the still-open C10 and C15.
- **Doc changes:** none (process only); this entry.
