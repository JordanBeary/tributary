# Decision packet — 2026-09-01 reframe

Every open decision from the reframe in one place, each in the INT-015 form: what was decided, the concrete question, what each answer entails, and a recommendation. Answering in one pass (a letter and an option per question) is enough; the Global unit records each disposition in the cited record and in `meta/logs/ledger.yaml`. Drafted by the Architect unit (plan Section 7), the C1 ask by the Local unit, and assembled by the Global unit; completed 2026-09-02 after the Round 2 handoffs. **Answered by the human 2026-09-02** — the `*Answer:*` line under each question is the human's own text; every disposition is recorded in the cited record, in `meta/logs/ledger.yaml`, and in `sessions/2026-09-01_reframe_session.md`.
Provenance: A (agent-drafted asks; the answers are H)

| Q | Record | Ask in one line | Answer |
| --- | --- | --- | --- |
| A | D11 | Phase 5 models 1-4: accept / amend / reject | **Accepted** 2026-09-02, with a direction attached: explain in detail the business problem each model solves. Phase 5 closes; recorded on D11 and as INT-018. |
| B | D14, INT-017 | Repositioning: accept / amend / reject; INT-017 class: ambiguity / misread | **Accepted** as recommended; INT-017 classified `ambiguity`. |
| C | D15 | Separation mechanics: path, PDF 404, private notes, harness scope | **Accepted** as recommended: the path stands, `resume.pdf` 404s behind the stub, private notes stay git-ignored in the parent, the parent is outside the harness with trailers only. |
| D | — | Outward steps: command file or GitHub UI | **Command file**, as recommended; it exists as the parent's tracked `NEXT_STEPS.md` (nothing executed). |
| E | C1 | Price-scale watch item: close / waive / act | **Closed** (option 1). The memo's price-scale caveat stands as the honest statement; no re-run. |
| F | D17 | Ledger clause: accept generated table / amend charter | **Option (1)**: the generated table satisfies the charter; no charter amendment. |
| G | P-013, conventions | Accept P-013?; amend conventions Section 3 with the INT-015 form and prompt-log bar? | **Both accepted**: P-013 recorded unconditionally; conventions Section 3 amended (v1.2), recorded under D14. |
| H | — | `project_summary.md` and the unit reports: commit / delete / summarize | **As recommended**: the fresh-eyes note committed as `sessions/2026-08-31_fresh_eyes_note.md`; the reports summarized in the session log; only the Architect plan committed, as `sessions/2026-09-01_architect_plan.md`. |
| I | D18 | Phase 6 method: pre-approve / review after the run | **Ratified**: the five-seed band is the Phase 6 exit measurement; the memo's pending tags come off. |
| J | D12, D14 | Publishing condition: flip to on-push after the reframe deploys / keep manual | **Flip to on-push** after the reframe deploys and the human has read the new site once. The workflow trigger is a separate commit made after that deploy (see the ordering constraints below); nothing changes in `.github/workflows/publish-site.yml` now. |
| K | D16 and ids | Confirm the record and graph commitments assumed by the plan | **Confirmed**: ids INT-017, D14–D18, the URL-preserving filenames, and the script-recomputed figures. |

---

## Q-A. D11 — Phase 5 models 1-4

1. *What was decided and why (agent, 2026-08-24; full record: `decisions.md` D11 and `sessions/2026-08-24_phase6_handoff.md`):* one auction-time feature contract with an explicit leakage list; an 8/2/2-month temporal split; model 2 as discrete-time survival with the Tobit kept as a documented specification test; model 3 as exact counterfactual replay with hot-deck imputation (+2.02% revenue per lead, CI +1.96 to +2.08); model 4 as a cross-fitted T-learner reporting ranking metrics because the pooled effect is underpowered.
2. *The question:* accept, amend, or reject.
3. *What each answer entails:* accept — the models page and model cards publish (commit plan item 9), the memo can cite the numbers, model nodes enter the graph. Amend — name the component; the affected model is rebuilt (about 25 minutes for all four) before publication. Reject — the models stay unpublished and the case study leads with findings and the experiment only.
4. *Recommendation:* accept; the handoff's watch items (C1 anchor, the 0.2x deep-tier bound, model 4 covariate exclusions) carry into the memo's risk register rather than blocking publication.

*Answer:* accept. But I want to push back and ask what the point of each model is - explain in detail the business problem attempting to solve.

## Q-B. D14 — repositioning; INT-017 — classification

1. *What was decided (agents, from the 2026-08-31 direction):* the thesis in D14(a); the spine Overview, Findings, Models and experiments, Strategy memo, Identity modeling, How this was built, Appendix, Run it yourself (filenames unchanged, so no published URL breaks); the method page rebuilt around rendered records; cost intact as an appendix. INT-017 records that the over-weighting of the silo problem persisted from the design body into the site.
2. *The questions:* (1) accept, amend, or reject D14; (2) classify INT-017 as `ambiguity` (the design body was never amended after INT-009 and the agent followed it) or `misread` (the standing objective was clear from instruction 9 and INT-009).
3. *What each answer entails:* accept D14 — commit plan items 5, 6, 7 proceed. Amend — name the page or order to change. Reject — the site keeps its current spine and only stale facts are fixed. The classification changes one line in INT-017 and nothing else.
4. *Recommendation:* accept D14; classify `ambiguity`, because the document the agent followed had not been corrected.
5. *Answer:* accept.

## Q-C. D15 — portfolio separation mechanics

1. *What was decided (Portfolio unit):* parent at `/Users/jordanbeary/JordanBeary.github.io` mirroring the GitHub user-site name, public, Quarto in `site/`, private material outside `site/` and git-ignored; Tributary keeps `/tributary/` URLs; `site/resume.qmd` becomes a redirect stub and `resume.pdf` is allowed to 404; the D13 rule moves to the parent's README; the parent sits outside the harness but carries `Provenance:` trailers.
2. *The questions:* (1) accept the path and repository name, or name another local folder (nothing else changes); (2) accept the `resume.pdf` 404 with the HTML stub, or keep a time-boxed PDF copy in Tributary (keeps the D13 exception alive; needs a removal date in D15); (3) private job-search notes as git-ignored folders in the public parent, or a separate private repository; (4) parent outside the harness (trailers only) or under it (would need `meta/` conventions extended).
3. *What each answer entails:* the path changes only D15(a) and the parent's location; keeping the PDF keeps conventions Section 2's exception and D13 alive with a date; a private repository adds one more repository to maintain but nothing private ever sits next to public content; bringing the parent under the harness means its commits carry records too.
4. *Recommendation:* accept the path; accept the 404 with the stub unless the PDF link has already been sent to someone; separate private repository if notes will be edited often, otherwise the ignored folders; outside the harness with trailers only.
5. *Answer:* accept.

## Q-D. Outward steps only the human can take

1. *Nothing is decided; these are actions:* create `JordanBeary/JordanBeary.github.io` (public), push the parent, enable Pages with source "GitHub Actions", run the workflow, verify the root and `/resume.html` serve; then commit Tributary per the commit plan, fast-forward `main`, push, dispatch `publish-site`, verify the eight-URL contract.
2. *The question:* should the agents prepare the exact `gh` commands in a file for the human to run, or will the human use the GitHub UI? Agents run none of them either way.
3. *What each answer entails:* the command file records the sequence verbatim in the session log; the UI route is recorded as a summary.
4. *Recommendation:* the command file.
5. *Answer:* accept recommendation - the command file.

## Q-E. C1 — the price-scale watch item

1. *What was decided and why (agent, Phase 0, backfill; ask drafted by the Local unit):* C1 declared the simulated price scale — iPinYou supplies price shapes, absolute lead prices were invented with a tier-1 clearing anchor of about $120 and a tier-6 floor of about $2 — with a standing caveat to sanity-check against public lead-pricing anecdotes before publishing. Under C11's elasticity the full-scale tier-1 mean rose to about $255 (C16 watch item); C19 eased the overall mean sold price from about $198 to about $177 but left tier 1 near $255. Model 3 now recommends raising the tier-1 floor from $187.11 to $224.53, further from the anchor, and the site published the prices on 2026-08-28 without a disposition, although four handoffs said "human decision before anything publishes".
2. *The question:* (1) **Close** C1: the current scale is acceptable for a simulated marketplace whose statistics are shapes from public data and declared levels; (2) **Waive** for publication: keep the item open but publish with a one-sentence caveat on the findings page, the models page, and the memo; (3) **Act**: supply a target tier-1 mean (or a per-tier schedule), re-fit the landscape levels, regenerate the world, redeploy the silos, re-run ER, marts, dashboards, and all four models.
3. *What each answer entails:* close — one record line; the memo already states the anchor and the drift plainly (its "price-scale caveat" subsection). Waive — three caveat sentences, no re-run; the item stays on the open list. Act — a C-series record, about 2.5 minutes of regeneration plus a full redeploy (S3 re-upload of about 1.3 GB, Neon reload, BigQuery untouched if marketing outputs are unchanged), ER re-run, dbt, dashboards, and about 25 minutes of model retraining; every headline dollar figure on the site changes; D11 and D18 numbers would have to be re-presented.
4. *Recommendation:* close (option 1). The scale's role is to carry realistic shapes and censoring structure, not to match any market; the memo names the anchor and the drift so a reader can discount the dollar levels, and the relative claims (level right, shape wrong; break-even shading 0.19; ROAS ordering) do not depend on the level.
5. *Answer:* accept recommendation

## Q-F. D17 — the charter's "ledger" clause

1. *What was decided (Global unit):* `meta/provenance.md` Section 3.1 is regenerated from commit trailers by `meta/tools/provenance_by_phase.py`, keeping the 14 backfill rows as history; `--check` fails when stale.
2. *The question:* (1) accept that the generated table satisfies charter Section 2's "commit trailers + ledger" exit criterion, or (2) amend the charter so commit trailers are the sole ledger and the table is a view.
3. *What each answer entails:* accept — no charter change; the criterion is met retroactively for Phases 1-7 now that the table exists. Amend — one charter edit plus a changelog line.
4. *Recommendation:* (1); it keeps the human-readable artifact the charter intended without manual upkeep.
5. *Answer:* accept recommendation - (1)

## Q-G. Prompt log and conventions

1. *What was decided (Architect, applying the 2026-08-28 P-012 rejection):* the 2026-09-01 direction is a scope directive and is quoted verbatim in D14, D15 and the session log, not logged as a prompt; the 2026-08-31 prompt is drafted as P-013 because it contains positioning content that shaped the copy.
2. *The questions:* (1) accept P-013, or reject it and keep the verbatim in INT-017 and the session log only; (2) allow the Global unit to add the INT-015 explicit-ask form and the prompt-log bar to `meta/conventions.md` Section 3 as decision-cited amendments (draft text in the session working notes), so they are not held only in agent memory and INT records.
3. *What each answer entails:* rejecting P-013 turns it into a tombstone like P-012; the Section 3 amendment is one conventions edit recorded under D14's consequences (conventions.md says any amendment to it is itself a logged decision).
4. *Recommendation:* accept P-013; yes to the Section 3 amendment.
5. *Answer:* accept recommendation.

## Q-H. Loose files

1. *Nothing decided yet.* (1) `project_summary.md` (untracked; the fresh-eyes note attached on 2026-08-31, currently the graph validator's one warning). (2) The three unit reports and the Architect plan (scratchpad; the Portfolio report's line 149 must be redacted before any commit).
2. *The questions:* (1) commit the note under `meta/logs/sessions/2026-08-31_fresh_eyes_note.md` with a provenance line, or delete it; (2) commit the reports under `meta/logs/sessions/2026-09-01_reports/`, or summarize them in the session log only (already done) and commit only the plan.
3. *What each answer entails:* committing the note clears the graph warning and gives P-013 its cited input; committing the reports adds long, partly superseded text to the record.
4. *Recommendation:* commit the note; summarize the reports and commit only the plan.
5. *Answer:* accept recommendation - commit the note; summarize the reports and commit only the plan.

## Q-I. D18 — Phase 6 validation method

1. *What was decided (Local unit, built and run 2026-09-01; full record D18):* an engine floor override (`SimConfig.floor_multipliers`, `--floor-multipliers`) applied to the frozen landscape before the waterfall, verified to leave the default path content-identical at the same seed; `models/validate_floors.py` running deployed versus recommended schedules across five seeds at scale 0.2 with common random numbers and the C19 recency dials; a bid-shading stress test at s = 0, 0.05, 0.10, 0.20 plus 0.35, 0.50, 1.00 to bracket the zero crossing. Result: realized lift +2.98% (range +2.88% to +3.15%) against the replay's +2.02%; sell-through 49.2% to 76.5%; break-even shading about 0.19. Test suite 58 passed.
2. *The question:* pre-approve the method so the run and record proceed in Round 2, or review the record after the run.
3. *What each answer entails:* pre-approve (or ratify now, since the run is done) — the memo's engine-re-run figures lose their "pending D18" tags and the seed band becomes the Phase 6 exit measurement; model 3's card gains the result. Review after / amend — name the component (seed count, scale, shading definition, grid); the run takes under a minute to repeat. Reject — the memo stays interim on the bootstrap CI.
4. *Recommendation:* pre-approve; the default engine path is bit-identical at the same seed, so nothing published changes until the numbers are ratified.
5. *Answer:* accept recommendation.

## Q-J. Publishing condition

1. *What was decided (D12):* Tributary publishes by manual dispatch "until the human review pass". The 2026-08-31 read was that pass and produced this reframe.
2. *The question:* keep manual dispatch through the reframe and flip to publish-on-push after D14's commits deploy, or keep manual indefinitely.
3. *What each answer entails:* flipping adds a push trigger to `.github/workflows/publish-site.yml` in the commit after the reframe deploys; keeping manual leaves every deploy a deliberate act.
4. *Recommendation:* flip after the reframe deploys and the human has read the new site once; recorded in D14's consequences.

## Q-K. Commitments already assumed by the plan, for confirmation

1. *Assumed:* ids INT-017, D14 (repositioning), D15 (separation), D16 (retroactive 2026-08-20 directive), D17 (ledger clause), D18 (Phase 6 method); filenames of existing case-study pages unchanged to preserve URLs; the identity page retitled but not renamed; the Local unit's derived figures recomputed by script before any appears on a page; graph node titles no longer carry document version numbers.
2. *The question:* accept or amend any of these.
3. *What each answer entails:* an amendment renumbers or renames in one place each; the ledger validator will catch any dangling reference.
4. *Recommendation:* accept.
5. *Answer:* accept recommendation.

---

## Commit-ordering constraints (for the `git add -p` plan; from the units' off-unit notes)

1. `meta/provenance_by_phase.svg` must be committed with or before the `site/tools/prerender.sh` hunk that copies it (commit plan item 2 before any site commit); the hook runs under `set -eu`, so a missing file fails every render.
2. Likewise `models/out/m*.html` must be committed with or before the prerender hunk that copies them (the D11/D18-gated commit 9); the memo copy tolerates a missing `models/strategy_memo.md` (placeholder include), so only the model reports gate a render.
3. `site/tools/prerender.sh` therefore carries hunks for two commits; stage them with their artifacts.
4. `meta/logs/decisions.md`, `README.md`, `project_guide.md` and `site/_quarto.yml` carry hunks for more than one commit (records, separation, re-spine); the plan's Section 6 mapping applies.
5. **An eleventh commit, after the deploy.** The Q-J answer (flip publishing to on-push) is executed only once the reframed site has deployed and the human has read it: a commit containing nothing but the `push` trigger on `main` in `.github/workflows/publish-site.yml`. It is deliberately last — before it, every deploy is a deliberate `workflow_dispatch` — and it must not be folded into any earlier commit.
