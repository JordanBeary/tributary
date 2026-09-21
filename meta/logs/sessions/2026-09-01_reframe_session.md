# Session Log — The reframe: three-reader review (2026-08-31) and four-unit round (2026-09-01)

A record of the two sessions in which the human corrected the project's framing after reading the published site start to finish. This is a global-track record (honest process evidence). Session 1 is verbatim: the human prompt and the agent response are reproduced in full. Session 2 records the human's direction verbatim where the Global unit received it verbatim, the unit mandates, and a summary of each unit's report.
Provenance: HD (human prompts and direction are H content; assembly by the Global unit)
Log opened 2026-09-01; finalized 2026-09-02 after the Round 2 handoffs.

**Fidelity notes.** Session 1: human prompt and all user-visible agent prose reproduced verbatim from the session context; the agent's page fetches are recorded as a bracketed note; heading levels inside the reproduced text are demoted by one so the log's own headings stay on top; no words changed. Session 2: the human's 2026-09-01 direction is reproduced verbatim from the coordinating agent's record (`direction-2026-09-01-verbatim.md`); it names no employer. Under the prompt-log bar (D12 review) it is a decision-cited quotation, recorded here and in D14, not a P-entry.

**Redactions.** None required in Session 1 (the author is named; no employer, account id, or personal identifier appears). Session 2 summaries name no employer; the Portfolio unit's report line 149 carries the employer strings inside a grep command and must be redacted before that report is committed (decision packet Q-H).

**Records produced by these sessions.** INT-017 and INT-018; D14, D15, D16, D17, D18 (all ratified 2026-09-02, with D11's ratification and C1's closure recorded at the same time); P-012 tombstone; P-013 (accepted); INT-015 and INT-016 field fixes; `meta/logs/ledger.yaml` with its validator and renderer; `meta/tools/provenance_by_phase.py` and the regenerated provenance ledger; graph nodes for the paths the reframe concerns; the decision packet `2026-09-01_decision_requests.md`; the rebuilt method page.

---

## Session 1 — 2026-08-31 — three-reader site repositioning review

Context attached by the human: `README.md`, `docs/design.md`, `docs/calibration_spec.md`, and the untracked fresh-eyes note `project_summary.md` (written 2026-08-31 by an agent from a full repository review). Between the prompt and the response the agent fetched and read the live site: home, resume, case-study overview, silo-problem, cost, dashboards, and method pages.


### Human prompt (verbatim)

I have worked through most items in this project and have the contents hosted on a github webpage here: https://jordanbeary.github.io/tributary/tributary/ .

The markdown attached project_summary.md is an agent review of what this project is. The point being, there are foundational elements that are misleading or misguided. For example, I am not a data engineer, I am a data scientist and analytics manager. In my initial project frameworking I put too much emphasis on the data silo problem when what I really want is to show I have the ability to link disparate data sources, but then taking a business problem and turning it into something data science can solve is my primary skillset and what I want to showcase.

After reading through the home page and navigating the tributary case study start to finish, it is not clear to me that the project is to show the reader how I interact with an agent and the steps I took during initial project conception to manage the agent to ultimately explore the data and solve hypothetical business problems.

Send out three reader agents to critique and plan a new draft:
Strategic Planner - agent's primary objective is to synthesize what the other two readers report to create a plan to revise. This agent is the planner and strategic brain. All existing work is kept, but set priority levels for what should ultimately be presented.

Director of Data Science - agent's primary objective is to critique how the Tributary case study showcases Jordan Beary's (me - a data scientist) ability to explore real business problems and produce results with the use of data science. Constantly asking do the contents of Jordan's resume align with what is exhibited in the case study?

AI Implementation - agent's primary objective is to critique the presentation of the human-agent interaction. Consistently asking should I inject specific events or specific protocols or actions taken that produced this outcome?

The case study reads like I am a data engineer - the infrastructure building should be listed as a secondary-level skill  and de-prioritized. The remainder of the project will focus more on analytics, data science, machine learning.

---

### Agent response (verbatim)

I'll read the full published site first so the three reviews are grounded in what's actually published, not just the repo docs.

*[Agent fetched: case-study overview, home page, resume, silo-problem, method, dashboards, and cost pages.]*

I've read the full published site — home, resume, overview, the silo problem, cost engineering, dashboards, and method pages. Here are the three reader reports, with the two critiques first and the planner's synthesis built on top of them.

---

#### Reader 1 — Director of Data Science

**Core finding: the site currently exhibits a data engineer with taste, not a data scientist who drives decisions. The mismatch with the resume is structural, not cosmetic.**

The resume's verifiable throughline is business-problem-to-decision translation: department creation, A/B testing leadership, production propensity models, RL lead routing validated with off-policy evaluation, fraud identity graphs, RTB and auction mechanics ownership. The case study's spine is: silo architecture, entity resolution, cloud cost, dashboards, method. Of the seven rows in the "Results in sixty seconds" table, five are engineering metrics (joinability, F1, cloud bill, bytes scanned) and only two are business findings — and even those are framed as byproducts of unification rather than as findings a leader brought to an executive.

The most damaging gap: the actual data science is unpublished. The four trained models — calibrated propensity, censored price modeling, counterfactual floor optimization, uplift — are exactly the content that maps to the resume (propensity models, auction mechanics, experimentation, OPE), and none of it is on the site. A hiring manager evaluating an Analytics & Data Science Manager sees zero models, zero experiment reads on the headline pages, zero recommendations. The one experiment on the site — the uplift holdout, read honestly as underpowered — is the single best data-science artifact published, and it sits at position six of six on the dashboards page.

The material for the correct story already exists; it's the framing that's inverted. The 3.8x consumer overcount, the $12.0M paid for consumers already bought within 30 days, the ROAS ranking that inverts once revenue joins through the auction, repeat applicants clearing at 0.52–0.75x — these are exec-meeting numbers. The site presents them as "what unification exposed," which makes the plumbing the protagonist. Flip it: the business questions lead, the findings answer them, and the unification is one paragraph of "what had to be true for this to be computable."

Entity resolution itself deserves a specific reframe rather than demotion. It maps directly to the resume's fraud identity-graph work (union-find over hundreds of millions of records). Presented as identity modeling — precision/recall tradeoffs, the choice to cluster at the 0.9998-precision operating point because transitive closure amplifies false edges, deterministic SQL where a probabilistic model would obscure truth — it is data science. Presented as "the silo problem," it is ETL. Same work, different skill claim.

Finally, the homepage tagline literally leads with "analytics infrastructure," and proof point two is a one-cent cloud bill. Frugality receipts are charming supporting material and the wrong second impression for this role. The single highest-leverage missing artifact for the manager claim is the Phase 6 strategy memo — the exec-facing recommendation with expected lift, uncertainty, and a rollout plan is precisely the skill the resume asserts and the site never demonstrates.

---

#### Reader 2 — AI Implementation

**Core finding: the method is asserted, not shown. The page states the thesis — "the build is the payload; the method is the exhibit" — and then exhibits nothing on-page.**

The method page is a claims-and-links page. Every artifact that would make the interaction model legible lives behind a GitHub link: the charter, the twelve agreements, the decision log, the intervention log, the prompt log, the provenance spec. An evaluator skimming the site will not open eight repo files; they need concrete vignettes rendered where they're standing. Your own reaction after a start-to-finish read — that the human-agent interaction isn't visible — is the confirming evidence, and the information architecture agrees: method is fifth of six nav items, and the results table contains no method metrics at all.

Specific injections, all of which exist in the record and should be surfaced verbatim or near-verbatim:

One full intervention, end to end. Pick one of the sixteen where the correction changed the work product — the ER difficulty tuning is ideal: agent produced a suspiciously clean fracture, the human recognized a benchmark you can ace is not a benchmark, the dial was retuned into 0.8–0.9, and the falsified calibration was kept and superseded rather than rewritten. Show the error, the correction, and the diff it caused. One story like this teaches the interaction model better than any description of the logging schema.

One decision record where the human amended rather than ratified. The decision log's value is that agents propose and the human disposes; a record that ends in "amended" or "rejected" proves the human is load-bearing. Render it in full, with the D-number.

The provenance ledger as a picture. Per-commit H/HD/A trailers are the decomposition evidence — show the distribution by phase. A reader should be able to see at a glance where the human authored, directed, or delegated.

Three to five impactful prompts with one-line annotations of what each produced. The prompt log exists; nothing from it appears anywhere.

A "how a phase actually runs" walkthrough: session start loads the knowledge graph, agent proposes, trigger table fires the required records, ratification round, phase gate that includes "logs current, graph validates, provenance recorded." This is the harness as a reusable system — the transferable claim that you make agents more effective than out-of-the-box — and right now it's described in one bullet.

Two cautions. First, keep every injected vignette terminating in a work-product consequence ("this intervention is why the auction linkage is deterministic SQL") so the method content never drifts into self-referential meta. Second, don't quarantine the method on one page: small method-note callouts inside the technical pages — "agent proposed X here; intervention I-nn corrected to Y" — let a reader absorb the interaction model while reading the science, which is where it's most persuasive.

---

#### Reader 3 — Strategic Planner (synthesis and revision plan)

**Repositioned thesis, one sentence:** a data scientist and analytics manager translates business problems into decisions backed by models and experiments, and does it by directing AI agents through an auditable harness — with the infrastructure demoted to "how the lab was built."

All existing work is retained. Priorities:

**P0 — Unblock and re-spine (do first)**

1. Close the D11 ratification and publish the models-and-experiments page. This is the blocking dependency for the entire repositioning: the DS story cannot lead while the DS content is unpublished. Propensity, censored pricing, floor optimization, and uplift map one-to-one onto resume claims.
2. Rewrite the overview to open with business decisions, not architecture: which channels earn their spend, what a duplicate consumer costs, where floors should sit, who to message. Rebuild the sixty-second results table so at least five of seven rows are business findings or model results; move joinability and F1 into a "why you can trust these numbers" row.
3. Rewrite the home positioning statement and proof points. Lead with problem-to-decision translation. New proof points: (a) a decision finding ($12.0M duplicate spend, or the floor-policy lift once ratified), (b) measured identity modeling scored against hidden ground truth, (c) the auditable human-agent method. Cost engineering exits the top three.

**P1 — Make the method visible**

4. Rebuild the method page around rendered artifacts per Reader 2: one full intervention vignette, one amended decision record, the provenance distribution, three to five annotated prompts, the trigger table, and the phase-lifecycle walkthrough. Separate "the harness" (reusable system) from "the records" (its outputs).
5. Embed method-note callouts in the technical pages so the interaction model is encountered in context.

**P2 — Reframe existing pages**

6. "The silo problem" becomes an identity-analytics page: same content, modeling-first framing (operating-point selection, precision/recall reasoning, deterministic-vs-probabilistic judgment), explicitly connected to the identity-graph skill on the resume. The fracture pathology becomes one setup paragraph.
7. Reorder dashboards decision-first — identity and duplicate spend, attribution, uplift lead; funnel and auction economics follow as evidence — and give each section one line naming the decision it informs.
8. Prioritize the Phase 6 strategy memo over any further polish. It is the highest-leverage unbuilt artifact for the manager claim, and it becomes proof point (a) when done.

**P3 — Demote, keep, and clean up**

9. Cost engineering moves to a supporting or appendix position ("running the lab lean"), fully intact, one sentence of reference on the home page at most.
10. Housekeeping caught along the way: the README phase checklist is stale (Phases 1–4 still unchecked, superseded F1 target cited) and contradicts the decision log; the home tagline should stop leading with "analytics infrastructure."
11. Run the revision through the harness itself: a decision record for the repositioning (this conversation is the human direction), and log entries for anything agents get wrong executing it. The repositioning is itself method evidence — record it as such.

Suggested new case-study navigation: Overview (problem and decisions) → Findings (dashboards, reframed) → Models and experiments (new) → Identity resolution (reframed) → How this was built (expanded method) → Appendix: infrastructure and cost → Run it yourself.

Sequencing note: each step above is a shippable increment, consistent with the standing rule to publish incrementally — D11 first because everything downstream cites it.

---

## Session 2 — 2026-09-01 (direction and wave A) and 2026-09-02 (wave B, dispositions) — four-unit reframe round

**Human direction (verbatim, 2026-09-01; attached to the message: `prompt-2026-08-31-site-repositioning-three-readers.md`, the Session 1 record above):**

> Read all repositories and the attached markdown file thoroughly. We need to do another significant reframe. Create subagents to take ownership over the investigation and correction of these various project units. The subagents should have a narrow-focus - only investigating their assigned project unit.
>
> Project Architect/Manager subagent:
> - Synthesize the information reported by the subagents.
> - Critique the search and retrieval process
> - Group the information or entire reports by:
>   - Job Search / Resume / Portfolio: anything related to creating and publishing a data science portfolio for the purpose of career networking or job searching.
>   - Local: Tributary case study: the data science project
>   - Global: Human-Agent interaction
> - Job Search / Resume / Portfolio: move all of those elements outside of the tributary case study+global track infrastructure.
>
> Tributary Data Scientist Expert (Local):
> - Report your findings to the Project Architect/Manager
> - You work with me on the data science elements and solve hypothetical business problems using data science, machine learning, analytics, business intelligence.
>
> Job Search / Resume / Portfolio subagent:
> - Report to the Project Manager with all findings
> - Your objective is to extract existing content related to job searching, resume building, portfolio page, and related threads and move them into a parent repository with logic subfolders.
>
> Human-Agent record keeper (Global):
> - Report your findings to the Project Architect/Manager
> - Your job is to record the interactions on the way to solving business problems using data science.
> - Explore visual representations or structures.

Later in the same session (2026-09-02, after the Local unit was cut off by an API rate limit), the human's next message was: "continue". Each unit was told to stay narrow and report to the Architect; Round 1 was investigation only.

**Structure of the round.** An Architect/Manager unit briefed three units, synthesized their Round 1 reports into a plan (`architect_plan.md`, in the session scratchpad; committed only if Q-H says so), and ran Round 2 in two waves on the local branch `reframe-2026-09-01` with nothing committed, pushed, or deployed by agents. Fact of the session: the Local unit's Round 2 session was cut off by a rate limit on 2026-09-01 and resumed on 2026-09-02; its handoff to this unit is dated 2026-09-01 and its wave B work (sidebar, callout placement, prerender hook) ran on 2026-09-02 concurrently with this unit's.

**Unit mandates (as briefed).**

- *Local — Tributary Data Scientist Expert:* critique how the case study shows the author turning business problems into data-science results; own the case-study pages, the models page, the strategy memo, and the Phase 6 validation run.
- *Global — Human-Agent Record Keeper:* record the interactions on the way to solving business problems; audit the harness; explore visual representations and structures; own `meta/`, the method page, the README, and the changelog rows.
- *Portfolio — Job Search / Resume / Portfolio:* inventory the portfolio material inside Tributary and build the parent user-site repository it moves to.

**Round 1 findings, summarized (full reports in the session scratchpad; disposition per Q-H).**

- *Local:* the data-science content exists (nine answered questions, four trained models with cards and static reports, an experiment read as underpowered, an identity layer with an operating-point argument) but nothing is stated as a decision; the models are unpublished pending D11; the strategy memo does not exist; the case-study spine is inverted; Phase 6 needs an engine floor override; the "about 8% duplicate consumers" text is stale since C18; three consumer counts are in circulation (636,164 clusters, 635,580 in D10, 635,579 in `dim_consumer`).
- *Portfolio:* the portfolio material inside Tributary is small and bounded (two pages, ten lines of `_quarto.yml`, four lines of `site/README.md`) but threads run through the project guide, the design doc, the conventions (D13) and Q1; no parent repository exists; one standing redaction violation at `meta/logs/decisions.md` line 393.
- *Global:* the harness records well at four grains, with fourteen of sixteen interventions terminating in a committed artifact and nine records where the human amended or overruled; provenance from git is 29 HD / 19 A / 0 H / 4 pre-harness across 52 commits; the record stopped on 2026-08-24 (no intervention, session record, or provenance-ledger row for Phase 7, the 08-31 review, or 09-01); the ledger was frozen at 2026-08-03; the 2026-08-20 presentation-layer directive had no id; five interaction chains were reconstructed (identity and attribution complete, funnel complete except the price level, floors and uplift broken at the pending D11).

**Architect resolutions that bind this log.** Ids: INT-017; D14 repositioning; D15 separation; D16 the 2026-08-20 directive; D17 the ledger clause; D18 the Phase 6 method. P-014 is not created (scope directive; quoted verbatim in D14 and here). P-013 is conditional on Q-G. The identity chain cites 635,579. The INT-015 form and the prompt-log bar are drafted as a conventions Section 3 amendment but not applied until Q-G.

**Round 2 outcomes by unit (working tree, uncommitted).**

- *Global, wave A (2026-09-01):* line 393 redacted; `meta/tools/provenance_by_phase.py` and the regenerated `meta/provenance.md` Section 3.1 with `meta/provenance_by_phase.svg`; `meta/logs/ledger.yaml` with `validate_ledger.py` and `render_ledger.py` (rendered `ledger.md` and the `site/tributary/_includes/` chain and record includes); 15 graph nodes for existing paths; `Disposition:` lines on every C and D record; `site/tributary/method.qmd` rebuilt; callout texts handed to Local; drafts of INT-017, D14–D18, P-012, P-013, this log and the decision packet. *Wave B (2026-09-02):* every slot filled from the two handoffs; conventions Section 2 and `CLAUDE.md` amended (G4); README refreshed (G8); design v1.8 and guide v2.13 landed (G10); graph nodes for the new artifacts and `model`-type nodes for models 1–4 (G7); decision packet completed (G12).
- *Local:* identity page and findings page reframed with footnotes (L1, L3, L4); overview rewritten with the problem-framing table and rebuilt results table, `docs/problem_framing.md` (L2); appendix (L5); sidebar order (L6); model cards, docstring and mart-comment fixes (L7); `site/tributary/models.qmd` and the prerender copy of model reports (L8); `docs/experiment_readout.md` with `models/experiment_power.py` (L9); engine floor override, `models/validate_floors.py`, five-seed run — lift +2.98% (range +2.88% to +3.15%) against the replay's +2.02%, break-even bid shading about 0.19 (L10, recorded as D18); interim `models/strategy_memo.md` and `strategy-memo.qmd` (L11); design and guide body wording (L12); the C1 ask (L13, in the decision packet Q-E); the callouts placed in the four reserved slots. *Wave B (2026-09-02, after the rate-limit resumption):* sidebar order applied (only the `contents:` block of `site/_quarto.yml`); overview callout option A chosen (the reframe itself, INT-017 / D14) over the calibration-judgment vignette; the `_includes/` chain diagrams left on the method page rather than embedded on the technical pages; the prerender memo copy made tolerant (a one-line placeholder include when the memo is absent); bit-identity of the default engine path re-verified against `main` in a temporary worktree; 154 page figures cross-checked by script against their JSON sources, all matching; `quarto render site` exit 0 with ten pages and four callouts rendered.
- *Portfolio:* baseline render and the eight-URL sitemap saved; the parent repository built at `/Users/jordanbeary/JordanBeary.github.io` (staged, no commit, no remote); profile and resume copied there and removed from Tributary; Tributary landing, redirect stub, navbar, footer and `site/README.md` edits; both sites render (exit 0); its Round 1 report redacted (P7). Decisions it made between real alternatives, recorded here: navbar-left text "Case study"; the resume stub as a 0-second meta refresh plus canonical, with `resume.pdf` allowed to 404 (Q-C); private folders in the parent keep one tracked README each via negation rules; the parent publish workflow triggers on push to `main` and on dispatch; the parent home paragraph reordered to open "I am a data scientist and analytics manager" — the original was the author's own copy (3144109), so this needs the human's read; the reserve-price proof point says "follows once its validation closes" without citing D11 or Phase 6 by id; `writing/` not created; the parent README cites D13 and D15 by id; `COMMIT_MSG.txt` kept untracked and ignored; `styles.css` copied minus the dashboard-frame rule, `custom.scss` unchanged. *Wave B addendum (2026-09-02):* the parent text that cites D11/D18 numbers (the reserve-floor proof point and the model rows of `projects/tributary.qmd`) is held out of the parent until those records ratify, with the swap-in text kept in the handoff. Three further Portfolio decisions are recorded in D15(d): figures withheld from the claims-table rows too; a harness row added mapping `meta/` to the resume's "AI agent guardrails and knowledge base" bullet; identity modeling mapped to both the "Fraud detection at scale" and "Closed-loop funding feedback pipeline" bullets and the price landscape to both the Experimentation and RL lead-routing bullets. Facts: the parent now contains a tracked `NEXT_STEPS.md` with the human's outward sequence and exact `gh` commands, none executed; the parent's project page states seven resume bullets as unmapped by any case-study artifact (department creation, revenue impact in part, fraud detection with unsupervised ML, alerting, competitor intelligence, risk modeling and visualization, data mining).

**Decisions the Global unit made (agent choices, open to amendment).**

1. Node titles in `graph.yaml` no longer carry document version numbers (they had drifted six versions); the version lives in each document's header.
2. `Disposition:` lines use a six-word vocabulary (proposed / ratified-as-proposed / amended / rejected / superseded / pending) with a parenthetical; table-row records C1–C10 get a compact list rather than a new column so no record wording changed.
3. The provenance ledger's 14 hand-written rows stay above generated-block markers; the script never touches them.
4. The 2026-08-31 verbatim is reproduced with headings demoted one level; nothing else changed.
5. Extracted records on the method page (D8 and four prompts) are generated verbatim from the logs by `render_ledger.py --extract`, so the page cannot paraphrase them.
6. Where the Local and Portfolio wordings covered the same line (design Section 1 item 6, Section 9 Phase 7 row, Section 10.2, guide objective 2 and line 48), the data-science clause is Local's and the portfolio clause is Portfolio's, merged into one sentence; the optional "recruiter"/"interviewer" rewordings in design Sections 5 and 6 were applied under D15.
7. `provenance_by_phase.py --check` is not added to CI in this round: it needs a full-depth checkout as well as a step, so the change is proposed in D17 rather than made.
8. The `git init -b` quirk reported by the Portfolio unit is added to the `CLAUDE.md` machine-quirks list (one line; the Phase 0 session log already records the git 2.24 failure).

**Off-unit observations recorded for the commit plan.**

- `site/tools/prerender.sh` now copies `meta/provenance_by_phase.svg` under `set -eu` (Global's hunk) and `models/out/m*.html` (Local's hunk); the memo copy tolerates a missing `models/strategy_memo.md` as of wave B. A render fails if the SVG or the model reports are absent, so the SVG must be committed with or before the prerender hunk (commit 2 before any site commit) and the model reports before or with commit 9's prerender hunk; the human's `git add -p` on `prerender.sh` should keep each hunk with its artifacts.
- `models/out/m3_validation.*`, `models/out/experiment_power.json` and `analysis/dashboards/data/derived_figures.json` are new committed-artifact candidates (not git-ignored); `data/tmp/floor_validation/` is under the ignored `data/`.
- This machine's git (2.24) lacks `git init -b`; `git symbolic-ref HEAD refs/heads/main` was used for the parent.
- `project_summary.md` remains untracked pending Q-H.

## Dispositions — 2026-09-02

The human answered the decision packet (`2026-09-01_decision_requests.md`) in one pass; the `*Answer:*` line under each question is their own text. Every disposition is recorded on its record, in the packet's answer table, and in `meta/logs/ledger.yaml`.

| Question | Record | Disposition |
| --- | --- | --- |
| Q-A | D11 | Ratified as recorded — Phase 5 closes, the models page and cards publish. A direction was attached: "explain in detail the business problem attempting to solve", recorded as INT-018 |
| Q-B | D14, INT-017 | D14 ratified; INT-017 classified `ambiguity` |
| Q-C | D15 | Ratified: the parent path, the `resume.pdf` 404 behind the stub, git-ignored private notes, the parent outside the harness with trailers only |
| Q-D | — | The command file, which exists as the parent's tracked `NEXT_STEPS.md` |
| Q-E | C1 | Closed: the declared price scale stands; the memo's price-scale caveat is the honest statement of the drift |
| Q-F | D17 | Option 1: the generated table satisfies the charter's ledger clause; no charter amendment |
| Q-G | P-013, conventions | P-013 accepted; conventions Section 3 amended (v1.2) with the explicit-ask form and the prompt-log bar, recorded under D14 |
| Q-H | — | The fresh-eyes note committed as `2026-08-31_fresh_eyes_note.md`; the Architect plan committed as `2026-09-01_architect_plan.md`; the three unit reports summarized above and not committed |
| Q-I | D18 | Ratified: the five-seed band (+2.98%, range +2.88% to +3.15%) is the Phase 6 exit measurement |
| Q-J | D12, D14 | Publishing flips to on-push after the reframed site deploys and the human has read it once; the workflow trigger is a separate, final commit and the workflow is unchanged for now |
| Q-K | D16 and the id allocation | Confirmed |

**The one correction the dispositions produced.** Ratifying D11 the human asked what the point of each model is. The model cards carried design Section 8's one-line business question and, after wave B, a "Decision this informs" block, but not the problem stated in detail — method before purpose, the same family as INT-017, one layer down in the artifacts the reframe had not reached. Recorded as INT-018 (classification `ambiguity`, open to amendment); the Local unit is writing the framing into the four cards and the models page.

**Two records that changed status without a question of their own.** D12's manual-dispatch condition ("until the human review pass") is satisfied by the 2026-08-31 read and superseded on that point by D14 (Q-J). Q1 (domain) is transferred to the portfolio repository with D15's ratification.

**Committing this round.** The human directed that the ten planned commits be made locally on `reframe-2026-09-01` and the push and deploy prepared without anything running against GitHub. Provenance follows `meta/provenance.md`: the record, reframe, separation, design, method and models commits are `HD` (agent-drafted from the human's 2026-09-01 direction and the ratified packet, human-approved), the en-route fix, tooling and Phase 6 build commits are `A` (agent-drafted, human-reviewed); no commit is `H`, and none carries an AI co-author trailer (INT-010). Commits whose directing prompt is P-013 carry `Directs: P-013`. An eleventh commit, after the deploy, carries only the publish-on-push trigger.

**Found while committing (2026-09-03).** The ten commits were made locally on `reframe-2026-09-01` (f7245ca..a7fffb4). Running `provenance_by_phase.py --check` against them exposed a defect in the tool this session wrote: the check could never pass, because the table lists every commit's hash and so cannot contain the commit that writes it. Fixed by excluding trailing table-only commits from the comparison, logged as INT-019, and D17 carries a line qualifying the disposition the human had just ratified. The table was then regenerated over all 62 commits (36 HD, 22 A, 4 pre-harness, 26 with `Directs`).

---

*End of log. Outward steps (repository creation, pushes, deploys) are the human's; the next Global session records them here, closes INT-017's resolution line, and records the publish-on-push commit.*
