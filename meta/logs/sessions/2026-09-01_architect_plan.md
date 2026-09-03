# Architect plan: Round 2 of the Tributary reframe

Provenance: A — agent-drafted synthesis of the three unit reports, directed by the human's 2026-09-01 instruction (quoted in D14) and reviewed at the decision packet. Committed 2026-09-02 (decision packet Q-H); the three unit reports it synthesizes are summarized in `2026-09-01_reframe_session.md` and are not committed. The dispositions recorded 2026-09-02 supersede this plan's Section 7 open questions: see `2026-09-01_decision_requests.md`.

Prepared 2026-09-01 by the Project Architect/Manager unit from the three Round 1 reports (`local_ds_report.md`, `portfolio_report.md`, `global_records_report.md`) and the 2026-08-31 three-reader review. Repository state: `main` at f5ae88f (2026-08-28), 52 commits, one untracked file (`project_summary.md`). No repository edits were made by this unit. Every claim marked "verified" below was checked against the working tree or `git log` by this unit; "unverified" means taken from the unit's report.

Standing rules applied throughout: no emojis; the author's employer is never named in this plan or in any file it directs (the one committed occurrence is referenced by path and line only); no fictional names; provenance trailers only, never an AI co-author trailer; every human decision is phrased as an explicit ask (INT-015).

---

## 1. Synthesis

### 1.1 The repositioned thesis, one sentence

Tributary shows a data scientist and analytics manager turning a lead marketplace's business questions into decisions backed by identity modeling, calibrated models, and an honestly read experiment, and doing it by directing AI agents through a harness whose records are rendered on the page rather than linked; the three-silo cloud build is how the lab was made, not what the lab is for.

### 1.2 The findings that matter most

| # | Finding | Found by | Status |
| --- | --- | --- | --- |
| F1 | The data science content already exists and is mostly finished (nine answered questions, four trained models with cards and static reports, an experiment read as underpowered, an identity-resolution layer with a real operating-point argument), but none of it is stated as a decision (metric, counterfactual, recommendation, expected value, uncertainty, rollout), the four models are unpublished pending D11, and the strategy memo does not exist. | Local | Verified: `models/out/m1-m4_*.html` and `models/cards/*.md` exist; D11 ask sits in `meta/logs/sessions/2026-08-24_phase6_handoff.md` with no answer; no `strategy_memo.md` anywhere. |
| F2 | The case study's spine is inverted: `site/_quarto.yml` sidebar runs Overview, The silo problem, Cost engineering, Dashboards, How this was built, Run it yourself; the home tagline leads with "analytics infrastructure"; the sixty-second table has four engineering rows of seven. | Local (and the 08-31 review) | Verified in `site/_quarto.yml` lines 47-60 and `site/index.qmd`. |
| F3 | The portfolio material inside tributary is small and cleanly bounded (two pages, about ten lines of `_quarto.yml`, four lines of `site/README.md`) but its threads run through `project_guide.md`, `docs/design.md` Sections 1, 9, 10, `meta/conventions.md` and `CLAUDE.md` (D13 exception), and Q1; no parent repository exists anywhere. | Portfolio | Files verified; live-site 404/200 results and the GitHub API checks are the Portfolio unit's and were not re-run. |
| F4 | A standing redaction violation: `meta/logs/decisions.md` line 393 quotes the human naming the current employer; the D13 exception covers only `site/resume.qmd` and its PDF. | Portfolio | Verified: the only occurrence outside `site/resume.qmd` in the tracked tree. |
| F5 | The harness stopped recording on 2026-08-24: no intervention, session record, or decision covers Phase 7's nine commits, the 2026-08-31 review (the largest framing correction the project has received), or 2026-09-01; `meta/provenance.md` Section 3 is frozen at 2026-08-03 (14 rows, nothing after Phase 0.5), so the charter's global exit criterion, read literally, has not been met by any phase since 0.5. | Global | Verified: last INT is 016 (2026-08-24 area), last D is D13 (2026-08-28, a Phase 7 decision, so "no decision" is slightly overstated; "no intervention or session record" holds); provenance ledger status line reads "v1.0, 2026-08-03". Commit trailers are current: 29 HD, 19 A, 4 pre-harness, 21 Directs, zero Co-Authored-By. |
| F6 | Stale facts on the live site and in the governing documents: "about 8% duplicate consumers" (`site/tributary/silo-problem.qmd` line 18; `docs/design.md` line 50) despite the v1.4 changelog claiming Section 2.3 was amended; design header stamp "v1.1 ... spec v0.1" against v1.7 / v0.13; changelog rows v1.4-v1.7 in descending order; README phase checklist unchecked from Phase 1 with the superseded F1 >= 0.9 target; `project_guide.md` Section 3 headed "end of Phase 1 build". | Local, Global (independently) | All verified. |
| F7 | Two open items crossed boundaries silently: D11 has been pending since 2026-08-24 with a well-formed ask and no disposition; the C1 price-scale watch item carries "human decision before anything publishes" in four handoffs and the site published on 2026-08-28 citing the prices. | Global, Local | Verified in the Phase 6 handoff (lines 6-16, 30). |
| F8 | Phase 6 cannot start without an engine change: `simulation/__main__.py` has no floor-schedule flag and `simulation/auction.py` reads floors only from the landscape artifact; the strategy memo's uncertainty band depends on it. | Local | Verified: argparse exposes `--scale`, `--seed`, `--months`, `--out-dir` only. |
| F9 | The knowledge graph cannot answer "which records touched this artifact": no nodes for `site/tributary`, `analysis/profiling`, `simulation/params`, `silos/*`, `er/scorecard.json`, the models; the `model` and `decision` node types are unused. | Global | Path gaps verified (validator: 52 nodes, 89 edges, 0 errors, 1 warning for `project_summary.md`); node-type usage taken from the report. |
| F10 | Record-id collision between units: the Portfolio unit names the separation decision D14; the Global unit assigns D14 to the repositioning and D15 to the separation. | Architect | Resolved in Section 2.3: Global's numbering stands. |

---

## 2. Critique of the search and retrieval process

### 2.1 Per unit

**Local (Tributary Data Scientist Expert).** Read the widest DS surface: design and calibration docs, the dashboard builder and all seven aggregate JSONs, all model scripts except `tobit.py` and `report.py`, all cards and metrics, the ER README and scorecard, all marts, all site pages, D8-D13 and C19, INT-011 to INT-016, the Phase 6 handoff. Its strongest contribution is the business-problem-to-solution map (Section 2 of its report) and the catch that the v1.4 changelog claims an amendment the text never received. Gaps: it did not open the three EDA notebooks or any static HTML report (their content is inferred from the scripts); it did not trace the auction call path in `simulation/stages.py`; every figure it marks (d), including the ~6.1M-contact power estimate, is its own arithmetic on committed aggregates and must be recomputed in an artifact before it is cited anywhere; it took the resume-to-artifact mapping from the 08-31 review rather than reading the resume (correct for its scope, but it means the "resume-mapped" language in its report is second-hand). It did not fetch the live site.

**Portfolio (Job Search / Resume / Portfolio).** The most complete file-level inventory of the three, with a classification per path, a repository-wide grep, live-site and GitHub API checks, and an honest listing of off-repo material without opening it. Gaps: it read `docs/design.md` only at grep-located lines, so any portfolio thread phrased without its keyword list would be missed (I found none, but Section 2.4's "single most impressive artifact" framing, which is a positioning claim, sits outside its keyword net and was caught by the Local unit instead); it did not verify the GitHub custom-domain propagation behavior it relies on for Q1; it numbered the separation record D14 without checking the Global unit's allocation. One thing to act on before anything from this round is committed: line 149 of `portfolio_report.md` contains the two employer strings verbatim inside a suggested grep command. The scratchpad is outside the repository, but if the unit reports are committed under `meta/logs/sessions/` (Open question Q-H) that line must be redacted first, and the Global unit's session log must not paste it.

**Global (Human-Agent Record Keeper).** Read all of `meta/` in full, ran the validator, and tallied every commit trailer; its four audits (intervention-to-consequence, dispositions, prompts-to-artifacts, gaps) and the five interaction chains are the substance the method page has been missing. Its provenance-by-phase table matches my recount exactly (29 HD, 19 A, 4 without, 21 Directs, 0 co-author). Gaps: it did not fetch the live site or read `models/`, so its chain 2.1 uses the D10 consumer count (635,580) where the published figure is 635,579; it left placeholders that depend on the other units; and its proposal to log the 2026-08-31 and 2026-09-01 prompts as P-013 and P-014 does not apply the prompt-log bar the human set on 2026-08-28 (P-012 rejected: domain-content prompts only, scope and sequencing directives go through `decisions.md`). That bar is recorded only in the D12 note and in the agent's memory file, not in `meta/conventions.md`, which is itself a harness gap (Section 2.4).

### 2.2 Overlaps and contradictions

| Topic | What the units said | Architect's resolution |
| --- | --- | --- |
| Consumer count | Local: three numbers in circulation, 636,164 (scorecard clusters), 635,580 (D10 text), 635,579 (`dim_consumer`, entities with an auctioned lead); the identity page shows two without explanation. Global chain 2.1 uses 635,580. | Publish 635,579 everywhere on the site with one footnote explaining the scorecard's 636,164; the ledger and the method page cite 635,579; D10's 635,580 stands as history. Owner: Local (site), Global (ledger). |
| Duplicate rate | Local: "~8%" is stale since C18; design v1.4 claims Section 2.3 amended. Global: flagged the header and changelog staleness, not the 8%. | Verified. Both fixes ship in Round 2 (Local: site line 18; Local wording plus Global changelog row for design.md). |
| Funded-rate denominators | Local: 12.7% / 13.3% / 13.4% across pages, all correct. | One footnote on the findings page; no number changes. Owner: Local. |
| Record ids | Portfolio: separation = D14. Global: INT-017; D14 = repositioning; D15 = separation; P-012 tombstone; P-013, P-014. | Global's allocation stands (the repositioning direction of 08-31 predates the separation direction of 09-01). Every "D14" in the Portfolio report reads D15. Further allocations by this plan: D16 = retroactive record of the 2026-08-20 "site is a presentation layer" directive; D17 = the charter ledger clause; D18 = Phase 6 floor-validation method (drafted only when the Local unit runs it). P-013 is drafted but conditional (Q-G); P-014 is not created; the 09-01 direction is quoted verbatim in D14, D15 and the session log instead. |
| Who owns the method page and callouts | Local: "other unit's page", proposes one callout per technical page. Global: rewrites the page, callouts "in coordination". | Global writes the method page and the text of every callout; Local places the callouts in the case-study pages it owns. |
| The site landing page | Portfolio: new short `site/index.qmd` case-study landing. Local: home proof points should be (a) a decision finding, (b) identity modeling, (c) the method. The 08-31 plan said the same for the profile home. | The profile home moves to the parent, so Local's proof-point recommendation applies to the parent's `site/index.qmd` (Portfolio executes with Local's supplied text) and, in one paragraph, to the tributary landing (Portfolio writes, Local reviews the DS framing). |
| Cost page | Local: merge into an appendix page with the architecture block. 08-31: appendix position, intact. Portfolio: STAYS. | `cost.qmd` keeps its filename (URL contract) and becomes "Appendix: how the lab was built", absorbing the architecture block from the overview and the systems table from the identity page. Owner: Local. |
| Phase 6 hook | Local proposes the hook and a validation script and says it "requires a decision record". Global lists no such record. | Local builds; Local hands Global a one-paragraph method description; Global drafts D18 as pending. |
| C1 watch item | Global: record gap (publish precondition crossed). Local: pending decision gating the memo headline. Neither drafted the ask. | Local drafts the C1 explicit ask (Section 7, Q-E); Global records the disposition. |
| README | All three flagged the stale checklist; none owned it. | Global owns all README edits (checklist refresh, repo-map row, author line), using wording supplied by Portfolio for the last two. |
| `site/_quarto.yml` | Touched by all three plans (title/navbar: Portfolio; sidebar: Local; prerender hook: Global). | Edit order inside Round 2: Portfolio first (title, description, navbar, footer), Local second (sidebar order and new pages), Global third (prerender hook only if the provenance chart is copied at render time). The human stages hunks per commit with `git add -p` (Section 6). |

### 2.3 Blind spots caused by the narrow-focus design

- No unit re-ran the Director-of-Data-Science question (does each resume claim have an artifact?). Local was told the resume was out of scope; Portfolio read the resume as a file to move, not as a claims list. The parent's `projects/tributary.qmd` needs exactly that mapping. Round 2 assignment: Local supplies an artifact-to-skill table; Portfolio maps it to resume bullets in the parent.
- No unit owned the shared files (`_quarto.yml`, `README.md`, `project_guide.md`, `docs/design.md`). Resolved by the ownership table in Section 5.4.
- No unit opened the rendered dashboards or the static model reports, so the decision-first reorder of the findings page is planned from the builder script, not from what a reader sees. Acceptable for Round 2 because the embeds are unchanged; the Local unit should open each rendered page once while writing its decision line.
- No unit asked whether the Phase 7 publishing condition ("manual until the human review pass") has been met. The 08-31 read was that pass, and it triggered a reframe; the condition should be restated (Q-J).

### 2.4 The harness itself: what session-start retrieval should have loaded and did not

The read-first list (`CLAUDE.md`, `meta/conventions.md`, `meta/graph/graph.yaml`, `project_guide.md`, `docs/design.md`) would have given a fresh agent on 2026-09-01:

1. A project guide whose Section 3 heading says "end of Phase 1 build" while its status line says Phase 7 (verified). The protocol's first step, "state which phase governs the session", reads contradictory inputs.
2. A graph with no node for the case-study pages, the models, or the EDA notebooks, so the graph does not surface the artifacts this reframe is about (verified).
3. No record at all of the 2026-08-31 session; the verbatim exists only in this session's scratchpad. The single most important recent human direction was not retrievable from the repository.
4. A provenance ledger that stops at Phase 0.5, so "provenance recorded" at a phase gate is checked by trailers alone, which the charter does not yet say is sufficient (D17 resolves this).
5. Two standing protocols that live only in agent memory files and INT records, not in `meta/conventions.md`: the INT-015 explicit-ask form and the 2026-08-28 prompt-log bar. A fresh agent without the memory directory would not know either. Conventions Section 3 is the right home; amending it is a human decision (Q-G).
6. No single place listing open decisions and watch items (D11, C1). They live in the last handoff note, which the read-first list does not point to. The generated ledger view (Section 5.3, item G6) should carry an "open items" table so the next session-start reads it.

---

## 3. Grouping

Every finding and proposed correction from the three reports appears exactly once below. Straddling items are split and both halves are listed. Source codes: L = Local report, P = Portfolio report, G = Global report, R = 08-31 review.

### 3.1 Group (a): Job Search / Resume / Portfolio

Items that leave the tributary repository entirely, with destination. Parent path as recommended by the Portfolio unit: `/Users/jordanbeary/JordanBeary.github.io` (GitHub `JordanBeary/JordanBeary.github.io`, user site at the root). The path is subject to Q-C; the Portfolio unit hands the final path to the Global unit so D15 carries no placeholder.

| Item | Source | Destination | Notes |
| --- | --- | --- | --- |
| `site/index.qmd` (profile, positioning statement, proof points, LinkedIn/GitHub) | P | parent `site/index.qmd` | Copied, not moved; proof points rewritten in the parent to Local's three (Section 5.2 item P7); relative links become absolute case-study URLs. |
| `site/resume.qmd` and the rendered `resume.html` / `resume.pdf` | P | parent `site/resume.qmd` | Unchanged content; single source for both outputs; typst config travels in its front matter. |
| `site/_quarto.yml` title "Jordan Beary", description "Data science portfolio...", navbar Home and Resume | P | parent `site/_quarto.yml` | Tributary keeps everything else. |
| `site/README.md` line 3 wording and lines 17-20 (resume outputs, D13 note) | P | parent `README.md` | Tributary's site README reworded per P Section 2 item 9. |
| D13 house rule (employers may be named on the resume only; KPIs scrubbed; no contact identifiers) | P | parent `README.md` rules section | Inside tributary the unqualified rule is restored (conventions line 27; `CLAUDE.md` line 23). D13 stays as a superseded record. |
| Q1 domain purchase and registrar | P | parent README site plan; Q1 status in tributary becomes "transferred (D15)" | A user-site custom domain propagates to project sites per GitHub docs; verify at setup. |
| Design Section 10.2 profile tree (`/`, `/resume`, `/writing`, `yourname.com`) and the 10.1 custom-domain bullet | P | parent README site plan | Tributary's 10.2 keeps only the `/tributary` subtree (Local wording, Global changelog row). |
| "Career artifact" objective wording and "recruiters and interviewers" audience language (`project_guide.md` lines 16, 19, 48, 57; design lines 139, 213, 215) | P | parent README (why the portfolio exists) | Tributary rewording per P Section 2 items 1 and 5. |
| Resume masters and tailored variants in `~/Downloads` | P | parent `resume/private/` (git-ignored) or a private repository | The two other people's resumes in `~/Downloads` enter nothing. |
| Job-search notes, trackers, outreach templates | P | parent `job-search/` and `templates/` (git-ignored) or a private repository | Portfolio recommends the private repository if edited often (Q-C). |
| Project index of older public repositories | P | parent `site/projects/index.qmd` | Private repositories are the human's call; not inspected. |
| `.github/workflows/publish-site.yml`, `custom.scss`, `styles.css` (minus `.dashboard-frame`), `tools/postrender.sh`, `site/.gitignore` | P | parent (copies) | Tributary's originals stay; drift accepted. |
| Tributary-side replacements: new case-study landing `site/index.qmd`, optional `site/resume.qmd` redirect stub, navbar "About the author" link, footer link, README author line | P | stays in tributary | Portfolio owns; these are the only portfolio-group edits inside tributary. |
| Resume claims to case-study artifacts mapping for `projects/tributary.qmd` | R, Architect | parent | Local supplies the artifact-to-skill table; Portfolio writes the page. |

### 3.2 Group (b): Local: Tributary case study

| Item | Source | Round 2 owner |
| --- | --- | --- |
| Decision framing missing everywhere; nothing is decision-grade | L | Local (problem-framing table, decision lines, memo) |
| Models unpublished pending D11; models-and-experiments page missing | L, R | Human (D11); Local (page) |
| Strategy memo missing (Phase 6 exit) | L, R | Local (interim draft now, final after validation) |
| Phase 6 floor re-run needs an engine override hook and a validation runner | L | Local (build and run); Global (D18 record) |
| Case-study spine inverted (sidebar order, overview, sixty-second table) | L, R | Local |
| Findings page ordered by build sequence; no decision lines | L, R | Local |
| Silo page should be identity modeling (retitle, reorder; filename kept) | L, R | Local |
| Cost page demoted to appendix, intact, absorbing the architecture block | L, R | Local |
| Stale "~8%" on the identity page and in design Section 2.3 | L | Local (both texts); Global (changelog row) |
| Three consumer counts; funded-rate denominators | L | Local (footnotes) |
| Mart comment "24.5M rows" (`fct_auction_events.sql` line 4) | L | Local |
| Model 4 docstring says random 50/50; code cross-fits | L | Local |
| Model cards lack "decision this informs" and "what we would do next" | L | Local |
| Experiment read-out with power arithmetic and follow-up design | L | Local (recompute in a script) |
| Maturity-adjusted ROAS; segment-level reserves; EDA and calibration-judgment page; models 5 and 6 notes | L | Local (P3, deferred) |
| C1 price-scale watch item disposition | G, L | Local drafts the ask; human decides; Global records |
| Design doc subtitle, Section 1 lifecycle order, Section 8 replay note, Sections 7 and 10.2 wording | L, G | Local (wording); Global (v1.8 row, header, changelog order) |
| `project_guide.md` objective 2 order, Section 3 heading, lines 48 and 57, status bump | L, P | Local (objectives, Section 3); Portfolio supplies portfolio-thread wording; Global lands the file edit with the records commit |
| Method-note callouts on technical pages | L, R, G | Global (text); Local (placement) |

### 3.3 Group (c): Global: Human-Agent interaction

| Item | Source | Round 2 owner |
| --- | --- | --- |
| Employer name in `meta/logs/decisions.md` line 393 | P | Global (redact in place, first commit) |
| No records for Phase 7 session, 08-31 review, 09-01 round | G | Global (INT-017, D14, D15, session log) |
| Provenance ledger frozen at 2026-08-03; charter exit criterion unmet as written | G, P | Global (generated table; D17 ask) |
| 2026-08-20 presentation-layer directive has no id | G | Global (D16, retroactive record; prompt-log bar routes it to decisions) |
| `Directs: P-012` on d3144f1 resolves to nothing; `Directs: P-004` on 342701e is a mis-trailer | G | Global (P-012 tombstone; note the mis-trailer in the ledger, no history rewrite) |
| INT-015 "Doc changes: none" should cite the four handoffs; INT-016 has `Flag:` not `Classification:` | G | Global |
| Graph coverage gaps; stale version strings in node titles; `site` node title | G, P | Global |
| Interaction ledger (`meta/logs/ledger.yaml`) and renderers for V1, V3, V4; V2/V5 later | G, R | Global |
| Method page rewrite around rendered artifacts | G, R | Global |
| `disposition:` line on each D and C record | G | Global (P2) |
| README status checklist stale; README repo-map row and author line | G, P, L | Global (all README edits) |
| Conventions: D13 exception sentence removed; `CLAUDE.md` digest line | P | Global (in the separation commit) |
| Conventions Section 3 does not carry the INT-015 form or the prompt-log bar | Architect | Human (Q-G); Global drafts |
| `project_summary.md` untracked; graph warning | G, P | Human (Q-H); Global executes |
| Whether unit reports are committed under `meta/logs/sessions/` | G | Human (Q-H); if yes, Portfolio redacts its line 149 first |
| Publishing condition ("manual until the human review pass") restated | P | Human (Q-J); Global records in D14 |
| Parent repository inside or outside the harness | G | Human (Q-C); Global records in D15(c) |

---

## 4. Priorities

All existing work is kept. Priorities order what is presented and what is built next.

| Priority | Item | Owner | Depends on |
| --- | --- | --- | --- |
| P0 | Redact decisions.md line 393 | Global | none |
| P0 | Records: INT-017, D14, D15 (drafts pending ratification), P-012 tombstone, session log for 08-31 and 09-01 | Global | Portfolio path handoff; Local decisions handoff |
| P0 | D11 explicit ask presented to the human | Local drafts (already in the handoff; re-present) | none |
| P0 | Parent repository built locally in full and rendered | Portfolio | none |
| P0 | Tributary landing, navbar, site README, conventions exception removal prepared on the working tree | Portfolio, Global | parent built |
| P0 | Stale-fact sweep visible on the live site: identity page line 18, consumer-count footnote | Local | none |
| P1 | Overview rewrite with problem-framing table and rebuilt sixty-second table; findings page reorder with decision lines; identity page retitle; cost page to appendix; sidebar order | Local | D14 ratification before commit (edits may be prepared now) |
| P1 | Models and experiments page; model-card decision blocks | Local | D11 ratification before commit |
| P1 | Method page rebuilt around V1 (provenance by phase), V3 (identity chain), V4 (lifecycle), D8 in full, four annotated prompts, trigger table; `meta/tools/provenance_by_phase.py`; `meta/logs/ledger.yaml` seeded with five chains; validator and renderer | Global | D14 ratification before commit |
| P1 | Design v1.8 and project guide v2.13 (wording plus changelog row, header stamp, changelog order) | Local, Global | D14, D15 ratification |
| P1 | README router refresh | Global | none |
| P1 | D17 charter ledger clause ask; regenerated provenance table | Global | none |
| P2 | Engine floor override, `models/validate_floors.py`, 5-seed run at scale 0.2 with a bid-shading parameter; D18 record | Local, Global | none for the build; D18 ratification before numbers publish |
| P2 | Strategy memo (interim with bootstrap CI, final with the seed band) and `strategy-memo.qmd` | Local | D11; P2 validation for the final |
| P2 | Experiment read-out with recomputed power arithmetic | Local | none |
| P2 | C1 disposition ask and record | Local, Global | none |
| P2 | Method-note callouts placed on technical pages | Global text, Local placement | method page |
| P2 | Graph nodes for uncovered paths, model nodes, version strings; `disposition:` lines | Global | D11 for model nodes |
| P2 | Parent proof points rewritten to decision-first; `projects/tributary.qmd` claims mapping | Portfolio with Local's table | parent built |
| P3 | Maturity-adjusted ROAS panel; segment-level reserves; EDA and calibration-judgment page; models 5 and 6 as logging-design notes | Local | P2 validation for reserves |
| P3 | V2 timeline, V5 disposition chart, V6 graph render, V8 heatmap | Global | ledger |
| P3 | Lighthouse re-run on both sites; URL-flattening question; domain (Q1, transferred) | Portfolio | parent live |

---

## 5. Round 2 assignments

### 5.1 Sequencing decision

GitHub creation, pushes, deploys, and deletions from the live site need the human. Round 2 therefore builds everything locally and stops at the outward boundary:

1. Agents create a local branch in tributary, `reframe-2026-09-01`, from `main`, and leave all tributary edits uncommitted on it. `main` stays at f5ae88f, the deployed state, so the human can diff and can keep deploying the old site until the parent is live.
2. The parent is built in full at the sibling path with `git init`, `.gitignore` written first, files staged (`git add`) but not committed; the initial commit message is drafted in the parent's `README.md` tail or a `COMMIT_MSG.txt` that is deleted after use. No remote is configured.
3. Both sites must render locally at the end of Round 2 (`PATH="$HOME/.local/bin:$PATH" quarto render site` in each). Nothing is pushed, dispatched, or deleted from the live site.
4. The human's outward sequence, after review: create the GitHub user-site repository, push the parent, enable Pages (Actions), run the workflow, verify the root serves; then commit tributary per Section 6, fast-forward `main`, push, and dispatch `publish-site`. In that order the "About the author" link never dangles and the resume is never unreachable.

Work order inside Round 2 to avoid file conflicts: Portfolio touches `site/_quarto.yml`, `site/index.qmd`, `site/README.md` first; Local then edits the sidebar block and the `site/tributary/*` pages; Global edits `meta/`, `README.md`, `CLAUDE.md`, the design changelog and header, and `site/tributary/method.qmd` last. Handoffs (Section 5.5) happen before Global writes the final records.

### 5.2 Portfolio unit

Agent-executable now:

| # | Correction | Target path(s) | Acceptance check | Handoff |
| --- | --- | --- | --- | --- |
| P1 | Baseline render of tributary as-is; save the eight-URL sitemap as the URL contract | `site/_site/sitemap.xml` (read only) | Render exits 0; sitemap saved to the scratchpad | none |
| P2 | Create the parent: `git init`, `.gitignore` first (`job-search/`, `resume/private/`, `templates/`, `site/_site/`, `site/.quarto/`, `*.docx`, `*.bak`), `README.md` with public/private rules, the D13 house rule, the site plan from design 10.2, and links to the case study; layout per the Portfolio report Section 3 | `/Users/jordanbeary/JordanBeary.github.io/` | `git status` shows the layout; `.gitignore` predates any private file; README names no KPIs and no contact identifiers | Final absolute path and intended URLs to Global (for D15) |
| P3 | Copy and adapt: `site/index.qmd`, `site/resume.qmd` (unchanged), `custom.scss`, `styles.css` minus `.dashboard-frame`, `tools/postrender.sh`, `site/.gitignore`, `.github/workflows/publish-site.yml`; write parent `site/_quarto.yml` (title "Jordan Beary", root `site-url`, navbar Home / Resume / Projects, GitHub and LinkedIn text links, no prerender hook); new initials favicon; `site/projects/index.qmd`; `site/projects/tributary.qmd`; `resume/README.md` | parent `site/`, `resume/` | `quarto render site` in the parent exits 0; `_site/index.html`, `_site/resume.html`, `_site/resume.pdf` exist; `grep -rn "tributary/" site/*.qmd` shows only absolute URLs | Source commits 3144109 and 6981f23 (verified) cited in the drafted first-commit message |
| P4 | Tributary working tree: `git rm site/index.qmd site/resume.qmd`; new `site/index.qmd` case-study landing (title "Tributary", one paragraph, links to the overview and to the parent, `sidebar: false`); `site/resume.qmd` redirect stub with meta refresh (recommended; Q-C); `site/_quarto.yml` title "Tributary", case-study description without the word "portfolio", navbar left keeps only the case-study entry (renamed "Overview" or kept), navbar right adds the text link "About the author", footer gains the same link; `site/README.md` line 3 reworded and lines 17-20 removed | `site/index.qmd`, `site/resume.qmd`, `site/_quarto.yml`, `site/README.md` | Render exits 0; `ls site/_site` has no `resume.pdf`; `grep -rn -i "resume\|linkedin" site/ --exclude-dir=_site --exclude-dir=.quarto` returns only the stub; the six case-study URLs and embedded dashboards are unchanged | Navbar edit done before Local touches the sidebar |
| P5 | Rewrite the parent home's three proof points decision-first using Local's supplied text: (a) the $12.0M same-buyer duplicate-spend finding (interim; floor-policy lift after D11 and Phase 6), (b) identity modeling scored against hidden truth (F1 0.879 / 0.873, purity 0.9998), (c) the auditable method; cost engineering exits the top three | parent `site/index.qmd` | No proof point leads with infrastructure or the cloud bill | Needs Local's proof-point text and artifact-to-skill table (5.5) |
| P6 | Supply exact replacement wording for `project_guide.md` lines 16, 19, 48, 57; `README.md` repo-map row and author line; design Sections 1 item 6, 9 Phase 7 row, 10.1 bullet, 10.2 tree | handed as text, not edited by this unit | Global and Local confirm receipt | To Global (guide, README, changelog) and Local (design section wording) |
| P7 | Redact the two employer strings on line 149 of its own report before any report is committed | scratchpad `portfolio_report.md` | `grep -c` of both strings in the report returns 0 | Tell Global the report is safe to reference |

Requires the human (drafted asks in Section 7): create `JordanBeary/JordanBeary.github.io` and enable Pages (Q-D); accept the `resume.pdf` 404 and the stub (Q-C); choose the private-notes location (Q-C); commit and push both repositories (Section 6); dispatch tributary's workflow after the parent is live (Q-D); domain purchase (transferred with Q1, no action now).

### 5.3 Local unit

Agent-executable now:

| # | Correction | Target path(s) | Acceptance check | Handoff |
| --- | --- | --- | --- | --- |
| L1 | Replace "about 8% duplicate consumers" with the C18 facts (heavy-tailed repeats, mean 3.8 applications per person, about 51% of leads on drifted identity variants); add one footnote reconciling 636,164 clusters with 635,579 consumers; add one footnote on the 12.7 / 13.3 / 13.4 funded-rate denominators | `site/tributary/silo-problem.qmd`, `site/tributary/dashboards.qmd` | `grep -n "8%" site/tributary/silo-problem.qmd` returns only line 83; both consumer counts appear once each with the footnote | none |
| L2 | Rewrite the overview: open with the four decisions (channel spend, duplicate cost, floor policy, nurture targeting); problem-framing table (problem, decision, metric, counterfactual, data, method, artifact, status); rebuilt sixty-second table with at least five business or model rows and one "why you can trust these numbers" row (joinability, F1); the architecture block moves to `cost.qmd`; subtitle no longer "Problem, architecture, and results" | `site/tributary/index.qmd`, `docs/problem_framing.md` | Table row count as specified; no architecture diagram above the first finding | One method-note callout slot reserved for Global |
| L3 | Reorder the findings page 04, 05, 06, 03, 02, 01 with one decision line opening each section; open each rendered dashboard once while writing the line | `site/tributary/dashboards.qmd` | Section order matches; six decision lines present; embeds unchanged | Callout slot for the C19 / P-011 chain |
| L4 | Retitle and reorder the identity page (filename kept): "How the unification works" first, scorecard second, "the trick" third, the three-silo table reduced to a setup paragraph (systems table moves to `cost.qmd`), the payoff section becomes links to findings, models, memo; title "Identity modeling" or similar | `site/tributary/silo-problem.qmd` | Heading order matches; `site-url`/filename unchanged | Callout slot for the D8 / P-010 chain |
| L5 | `cost.qmd` becomes "Appendix: how the lab was built": architecture block and diagram, silo systems table, cost engineering intact, 100x-scale note | `site/tributary/cost.qmd` | Page title changed; no content removed | none |
| L6 | Sidebar order in `_quarto.yml` (after Portfolio's navbar edit): Overview, Findings, Models and experiments, Strategy memo, Identity modeling, How this was built, Appendix, Run it yourself; the models and memo entries are added only to the working tree and belong to the D11-gated commit | `site/_quarto.yml` sidebar block | Render exits 0 with the two new pages present; order matches | Tell Global the final page list for D14(b) and the design 10.2 wording |
| L7 | Model cards: add "Decision this informs" and "What we would do next" blocks to all four; fix the `train_uplift.py` docstring (line 18) to describe 2-fold cross-fitting; fix the mart comment to 26.4M rows | `models/cards/model_1..4*.md`, `models/train_uplift.py`, `warehouse/models/marts/fct_auction_events.sql` | `tests/test_models.py` still passes if run; grep confirms the strings | none |
| L8 | Draft `site/tributary/models.qmd` per the Local report outline 4.1 and extend `site/tools/prerender.sh` to copy `models/out/m*.html` into `site/tributary/embedded/` | `site/tributary/models.qmd`, `site/tools/prerender.sh` | Render exits 0; four embeds resolve; every number traces to `models/out/m*_metrics.json` | Commit gated on D11 |
| L9 | Experiment read-out: recompute the power arithmetic in a small script (do not cite the report's ~6.1M figure), decision rule, follow-up test sized for +0.5pp in segment 5 | `docs/experiment_readout.md`, `analysis/` script or `models/` script that emits the numbers | Script output matches the document; cited in `models.qmd` section 4 | none |
| L10 | Engine floor override: `AuctionLandscape.floors` override via a config or `--floors` option in `simulation/__main__.py` / `simulation/config.py`; `models/validate_floors.py` running deployed vs recommended schedules across 5 seeds at scale 0.2 with an optional bid-shading parameter (s = 0, 5, 10, 20 percent), writing `models/out/m3_validation.json` and a static page; trace the `stages.py` call path to confirm recency dials do not interact | `simulation/`, `models/validate_floors.py`, `models/out/` | Default run is bit-identical to today's output at the same seed (no override); validation JSON written; existing simulation tests pass | One-paragraph method description and the seed band to Global for D18; graph node for the new script |
| L11 | Strategy memo, interim version with the bootstrap CI and clearly marked [P6] placeholders, per outline 4.2; `site/tributary/strategy-memo.qmd` rendering it | `models/strategy_memo.md`, `site/tributary/strategy-memo.qmd` | Every number in the memo traces to a committed JSON; C1 caveat present; interim status stated in the first line | Commit gated on D11 and the D18 disposition |
| L12 | Design doc section wording for v1.8: subtitle, Section 1 lifecycle order, Section 2.3 duplicate text, Section 7 decision-first order, Section 8 replay note and segment-level follow-on, Section 9 Phase 7 exit row, Section 10.2 case-study subtree (with Portfolio's lines); `project_guide.md` objective 2 reorder, Section 3 heading, line 48 | `docs/design.md` body, `project_guide.md` | Handed as diffs; Global lands the changelog row, header stamp and changelog reorder in the same commit | To Global |
| L13 | Draft the C1 price-scale explicit ask (Q-E) with the three options and a recommendation | text to Global | Ask follows the INT-015 form | To Global for the records commit |
| L14 | Supply Portfolio the three decision-first proof points and an artifact-to-skill table (artifact, business decision, skill demonstrated, page) | text to Portfolio | Portfolio confirms receipt | To Portfolio |
| L15 | Hand Global the list of decisions this unit made in Round 2 (findings order, consumer-count convention, denominator footnote, Phase 6 method, memo interim status, models page outline) | text to Global | Each appears in D14, D18 or the session log | To Global |

Requires the human: D11 ratification (Q-A); C1 disposition (Q-E); D18 ratification after the validation run (Q-I); committing the D11-gated pages.

### 5.4 Global unit

Agent-executable now:

| # | Correction | Target path(s) | Acceptance check | Handoff |
| --- | --- | --- | --- | --- |
| G1 | Redact the employer name in the D13 human quote in place with `[REDACTED: employer]` | `meta/logs/decisions.md` line 393 | `git grep -i` for both employer strings returns only `site/resume.qmd` (and nothing once that file is removed) | none; first commit |
| G2 | Write INT-017 (both classification options, recommendation "ambiguity"), D14 (thesis from Section 1.1; spine from L6; method plan), D15 (parent path and moved-file list from P2/P3; D13 supersession; Q1 transfer; harness scope per Q-C), D16 (retroactive record of the 2026-08-20 presentation-layer directive with its three citing records and the d5465e6 trailer), D17 (charter ledger clause, pending), P-012 tombstone, P-013 drafted and marked conditional on Q-G, INT-015 doc-changes amendment, INT-016 `Classification:` field | `meta/logs/interventions.md`, `meta/logs/decisions.md`, `meta/logs/prompts.md` | No placeholders remain; every id cited exists or is created in the same commit; no employer name; ids INT-017, D14-D17 unique | Needs P2/P6, L6/L12/L13/L15 handoffs first |
| G3 | Session log for 08-31 and 09-01: move the scratchpad verbatim of 08-31 in nearly unchanged; add the 09-01 direction verbatim, the unit mandates, and a summary of each unit's report (full reports committed only if Q-H says so, after P7) | `meta/logs/sessions/2026-09-01_reframe_session.md` | Fidelity notes present; redaction check passes; graph node added | none |
| G4 | Conventions exception removal and `CLAUDE.md` digest line; these ship in the separation commit | `meta/conventions.md` line 27, `CLAUDE.md` line 23 | The rule reads unqualified; D13 annotated "superseded by D15" | Portfolio confirms the resume file is removed on the branch |
| G5 | `meta/tools/provenance_by_phase.py` emitting a Markdown table and a static chart from `git log` trailers with the phase-mapping rule in code; regenerate `meta/provenance.md` Section 3 as a generated table appended below the frozen backfill rows (keep the 14 rows as history); wire the chart copy into `site/tools/prerender.sh` | `meta/tools/`, `meta/provenance.md`, `site/tools/prerender.sh` | Script output matches the Section 1.5 counts (29 HD, 19 A, 4 none, 21 Directs); ledger status line updated | D17 ask cites it |
| G6 | `meta/logs/ledger.yaml` seeded with the five chains; `meta/tools/validate_ledger.py` (every ref resolves to an id or path); `meta/tools/render_ledger.py` emitting Mermaid per chain, `meta/logs/ledger.md`, and an "open items" table (D11, C1, D14-D18) | `meta/logs/ledger.yaml`, `meta/logs/ledger.md`, `meta/tools/` | Validator exits 0; the identity chain uses 635,579; the `Directs: P-004` mis-trailer is noted in the ledger | Chain diagrams to Local for callouts |
| G7 | Graph: nodes for `analysis/profiling`, `simulation/params`, `silos/s3_lake`, `silos/crm_postgres`, `silos/marketing_bq`, `warehouse/models/staging`, `warehouse/models/intermediate`, `er/scorecard.json`, `site/tributary`, `meta/tools`, `meta/logs/ledger.yaml`, the session log, new docs from L2/L9/L11, new scripts from L10; version strings corrected; `site` node title; model nodes after D11 | `meta/graph/graph.yaml` | `.venv/bin/python meta/graph/validate_graph.py` exits 0 with 0 warnings (after Q-H resolves `project_summary.md`) | Graph diffs land in the same commit as each structural change (Section 6) |
| G8 | README: status checklist refreshed (Phases 0-4 complete, 5 built pending D11, 6 in progress, 7 first release live; band 0.8-0.9); repo-map row for `site/`; author line (Portfolio wording); quickstart line | `README.md` | Router voice kept; no pitch language | Wording from Portfolio |
| G9 | Method page rebuilt: the harness section (V4 lifecycle, trigger table, INT-015 form) separated from the records section (V1 chart, V3 identity chain, D8 rendered in full, P-005, P-008, P-010, P-011 annotated, the provenance statement that no commit is H and why); every vignette terminates in a work-product consequence; callout texts written for the identity page (D8 / P-010), findings page (C19 / P-011), models page (D11), overview (C9 / INT-013 / INT-014 or the reframe itself) | `site/tributary/method.qmd`, callout text to Local | Render exits 0; no bare link list remains; Mermaid renders | Callout text to Local |
| G10 | Design changelog v1.8 row, header stamp (v1.8 / spec v0.13), changelog rows reordered ascending, with Local's body wording; `project_guide.md` v2.13 status line and lines 57 wording | `docs/design.md`, `project_guide.md` | Row cites INT-017, D14, D15 and the en-route fixes; header matches | Body wording from Local and Portfolio |
| G11 | `disposition:` line on each D and C record (proposed / ratified-as-proposed / amended / rejected / superseded / pending); no other wording changes | `meta/logs/decisions.md` | Count of lines equals count of records | P2 |
| G12 | Draft the human's decision packet (Section 7) as a single file for one-pass answering | `meta/logs/sessions/2026-09-01_decision_requests.md` or the session log | Every open item in Section 7 appears in INT-015 form | none |

Requires the human: INT-017 classification and D14, D15, D16, D17 ratification (Q-B, Q-C, Q-F); P-013 and the conventions Section 3 amendment (Q-G); `project_summary.md` and unit-report disposition (Q-H); publishing condition (Q-J).

### 5.5 Ownership and handoff table

| Artifact | Owner | Contributor | Handoff |
| --- | --- | --- | --- |
| `site/tributary/index.qmd` (overview) | Local | Global (one callout) | Global supplies callout text after G6 |
| `site/tributary/method.qmd` | Global | Local (reviews callout placement) | none |
| New `site/index.qmd` (case-study landing) | Portfolio | Local (reviews the paragraph) | none |
| `site/tributary/models.qmd`, `strategy-memo.qmd` | Local | Global (D11 callout) | commit gated on D11 |
| `site/tributary/dashboards.qmd` reorder | Local | Global (C19 callout) | none |
| `site/tributary/silo-problem.qmd`, `cost.qmd` | Local | Global (D8 callout) | none |
| `site/_quarto.yml` | Portfolio (title, description, navbar, footer), then Local (sidebar), then Global (prerender-related only) | | edit order enforced |
| `README.md` | Global | Portfolio (row and author-line wording) | P6 to G8 |
| `project_guide.md` | Global lands; Local (objectives, Section 3), Portfolio (lines 16, 19, 48, 57 wording) | | L12, P6 to G10 |
| `docs/design.md` | Local (body), Global (changelog, header) | Portfolio (Sections 1, 9, 10 lines) | L12, P6 to G10 |
| `meta/*` | Global | | P2 (path), L13 (C1 ask), L15 (decisions), L10 (D18 method) to G2 |
| Parent repository | Portfolio | Local (proof points, claims table) | L14 to P5 |

---

## 6. Commit plan

Agents commit nothing and push nothing. All tributary edits sit on the local branch `reframe-2026-09-01`; the human commits in the order below, using `git add -p` where one file carries hunks for two commits (`site/_quarto.yml`, `README.md`, `project_guide.md`). Each subject line is a suggestion. Trailers: `Provenance: H | HD | A` and optionally `Directs: <id>`; never a co-author trailer. Repo-structure changes carry their `graph.yaml` diff in the same commit.

| # | Content | Provenance | Directs | Gate |
| --- | --- | --- | --- | --- |
| 0 | `meta: redact employer name in the D13 quote (en-route fix)` — `decisions.md` line 393 only | A | none | none; commit first |
| 1 | `Records: INT-017, D14-D17 drafted, P-012 tombstone, session log for 2026-08-31 and 2026-09-01; INT-015/016 field fixes` — `meta/logs/*`, graph node for the session log, decision packet | HD | P-013 if Q-G accepts, else none | none (records may be committed as "pending ratification") |
| 2 | `Provenance ledger regenerated from commit trailers; ledger.yaml and tools; graph coverage` — `meta/tools/*`, `meta/provenance.md`, `meta/logs/ledger.*`, `graph.yaml` nodes and version strings, `site/tools/prerender.sh` hook | A | none | none |
| 3 | `Portfolio separation (D15): profile and resume moved to the author's user-site repository; case-study landing; navbar; conventions exception retired` — `git rm` of the two pages, new `site/index.qmd`, stub, `_quarto.yml` navbar/title/description/footer hunks, `site/README.md`, `meta/conventions.md`, `CLAUDE.md`, `README.md` (all edits), `project_guide.md` portfolio-thread lines, `graph.yaml` site node | HD | none | D15 ratified; parent live before this is deployed |
| 4 | `Stale facts: C18 duplicate text, consumer-count and denominator footnotes, mart row count, uplift docstring, model-card decision blocks` — `site/tributary/silo-problem.qmd` line 18 only, `dashboards.qmd` footnote, `fct_auction_events.sql`, `train_uplift.py`, `models/cards/*` | A | none | none |
| 5 | `Case study re-spined (D14): overview leads with decisions; findings decision-first; identity modeling; infrastructure to appendix` — `site/tributary/index.qmd`, `dashboards.qmd`, `silo-problem.qmd`, `cost.qmd`, `_quarto.yml` sidebar hunk (without the two gated entries), `docs/problem_framing.md`, `docs/experiment_readout.md` and its script, graph nodes | HD | none | D14 ratified |
| 6 | `Design v1.8 and guide v2.13: body aligned to the tagline; site map rewritten; header and changelog order fixed` — `docs/design.md`, `project_guide.md` remaining hunks | HD | none | D14 and D15 ratified |
| 7 | `Method rendered (D14c): provenance by phase, identity chain, lifecycle, D8 in full, annotated prompts; callouts on technical pages` — `site/tributary/method.qmd`, callout hunks in the case-study pages | HD | none | D14 ratified; after commit 5 |
| 8 | `Phase 6: engine floor override, validation runner, seed band; D18 recorded` — `simulation/*`, `models/validate_floors.py`, `models/out/m3_validation.*`, D18 record, graph nodes | A | none | none for the code; D18 disposition noted in the record |
| 9 | `Models and experiments page and interim strategy memo (D11 ratified)` — `models.qmd`, `strategy-memo.qmd`, `models/strategy_memo.md`, the two sidebar entries, `prerender.sh` model-embed hunk | HD | none | D11 ratified; commit 8 for the band if final |

Parent repository: one initial commit, `Portfolio site: profile and resume moved from tributary (3144109, 6981f23); project index; publish workflow`, `Provenance: HD`, made by the human after reviewing `git status` in the parent. Whether the parent carries trailers thereafter is Q-C.

After the human's outward steps, the Global unit (next session) records the deployment in the session log and closes the loop on INT-017's "Resolution" line.

---

## 7. Open questions for the human

Each item states what was decided, the concrete question, what each answer entails, and a recommendation. Answering in one pass (a letter per question) is enough.

**Q-A. D11: Phase 5 models 1-4.** Decided (agent, 2026-08-24, full record in `decisions.md` D11 and the Phase 6 handoff): one auction-time feature contract with an explicit leakage list; an 8/2/2-month temporal split; model 2 as discrete-time survival with the Tobit kept as a documented specification test; model 3 as exact counterfactual replay with hot-deck imputation (+2.02% revenue per lead, CI +1.96 to +2.08); model 4 as a cross-fitted T-learner reporting ranking metrics because the pooled effect is underpowered. Question: accept, amend, or reject. Accept: the models page and model cards publish (commit 9), the memo can cite the numbers, model nodes enter the graph. Amend: name the component; the affected model is rebuilt (about 25 minutes total for all four) before publication. Reject: the models stay unpublished and the case study leads with findings and the experiment only. Recommendation: accept; the handoff's watch items (C1 anchor, the 0.2x deep-tier bound, model 4 covariate exclusions) are carried into the memo's risk register rather than blocking publication.

**Q-B. D14: repositioning, and INT-017's classification.** Decided (agents, from your 2026-08-31 direction): the thesis in Section 1.1; the spine Overview, Findings, Models and experiments, Strategy memo, Identity modeling, How this was built, Appendix, Run it yourself (filenames unchanged, so no published URL breaks); the method page rebuilt around rendered records; cost intact as an appendix. INT-017 records that the over-weighting of the silo problem persisted from the design body into the site. Questions: (1) accept, amend, or reject D14; (2) classify INT-017 as `ambiguity` (the design body was never amended after INT-009 and the agent followed it) or `misread` (the standing objective was clear from P-003 instruction 9 and INT-009). Accept D14: commits 5, 6, 7 proceed. Amend: name the page or order to change. Reject: the site keeps its current spine and only stale facts are fixed. Recommendation: accept D14; classify `ambiguity`, because the document the agent followed had not been corrected.

**Q-C. D15: portfolio separation mechanics.** Decided (Portfolio unit): parent at `/Users/jordanbeary/JordanBeary.github.io` mirroring the GitHub user-site name, public, Quarto in `site/`, private material outside `site/` and git-ignored; tributary keeps `/tributary/` URLs; `site/resume.qmd` becomes a redirect stub and `resume.pdf` is allowed to 404; the D13 rule moves to the parent's README; the parent sits outside the harness but carries `Provenance:` trailers. Questions: (1) accept the path and repository name, or name another local folder (nothing else changes); (2) accept the `resume.pdf` 404 with the HTML stub, or keep a time-boxed PDF copy in tributary (keeps the D13 exception alive; needs a removal date in D15); (3) private job-search notes as git-ignored folders in the public parent, or a separate private repository; (4) parent outside the harness (trailers only) or under it (would need `meta/` conventions extended). Recommendation: accept the path; accept the 404 with the stub unless the PDF link has already been sent to someone; separate private repository if notes will be edited often, otherwise the ignored folders; outside the harness with trailers only.

**Q-D. Outward steps only you can take.** Nothing is decided; these are actions. Sequence: create `JordanBeary/JordanBeary.github.io` (public), push the parent, enable Pages with source "GitHub Actions", run the workflow, verify the root and `/resume.html` serve; then commit tributary per Section 6, fast-forward `main`, push, dispatch `publish-site`, verify the eight-URL contract. Question: do you want the agents to prepare the exact `gh` commands in a file for you to run, or will you do it in the GitHub UI? Either way agents run none of them. Recommendation: the command file, so the sequence is recorded verbatim in the session log.

**Q-E. C1: the price-scale watch item.** Decided (agent, Phase 0, backfill): the invented price scale, anchored at a $120 tier-1 mean, with a standing request for your industry gut-check that never entered the log; C19 eased the tier-1 mean to about $255 and model 3 recommends a floor of $224.53, further from the anchor; the site published the prices on 2026-08-28. Question: (1) close the item (the current scale is acceptable as a simulated marketplace), (2) waive it for publication with a caveat line on the findings and memo pages, or (3) act on it (supply a target scale; the engine is re-run and every headline number changes). Close: one record line, no other change. Waive: one caveat sentence in three places. Act: a C-series record, a full re-run, model retraining, dashboard and site regeneration. Recommendation: close, with the memo stating the anchor and the drift plainly; the Local unit will draft the record either way.

**Q-F. D17: the charter's "ledger" clause.** Decided (Global unit): `meta/provenance.md` Section 3 is regenerated from commit trailers by `meta/tools/provenance_by_phase.py`, keeping the 14 backfill rows as history. Question: (1) accept that the generated table satisfies the charter's "commit trailers + ledger" exit criterion, or (2) amend the charter so commit trailers are the sole ledger and the table is a view. Accept: no charter change; the criterion is met retroactively for Phases 1-7 once the table exists. Amend: one charter edit plus a changelog line. Recommendation: (1), because it keeps the human-readable artifact the charter intended without manual upkeep.

**Q-G. Prompt log and conventions.** Decided (Architect, applying your 2026-08-28 P-012 rejection): the 2026-09-01 direction is a scope directive and is quoted verbatim in D14, D15 and the session log, not logged as a prompt; the 2026-08-31 prompt is drafted as P-013 because it contains positioning content ("I am a data scientist and analytics manager ... my primary skillset") that shaped the copy. Questions: (1) accept P-013, or reject it and keep the verbatim in INT-017 and the session log only; (2) allow the Global unit to add the INT-015 explicit-ask form and the prompt-log bar to `meta/conventions.md` Section 3 as decision-cited amendments, so they are not held only in agent memory. Recommendation: accept P-013; yes to the Section 3 amendment, recorded under D14's consequences.

**Q-H. Loose files.** Decided (nothing yet). (1) `project_summary.md` (untracked, the fresh-eyes note you attached on 08-31): commit it under `meta/logs/sessions/2026-08-31_fresh_eyes_note.md` with a provenance line, or delete it. (2) The three unit reports and this plan: commit them under `meta/logs/sessions/2026-09-01_reports/` (after the Portfolio unit redacts its line 149), or summarize them in the session log only. Recommendation: commit the note (it is the input P-013 cites); summarize the reports in the session log and commit only this plan, since the reports are long and partly superseded by it.

**Q-I. D18: Phase 6 validation method.** Decided (Local unit, to be built in Round 2): an engine floor override, five seeds at scale 0.2 for deployed versus recommended schedules, an optional bid-shading parameter at 0, 5, 10, 20 percent, realized revenue per lead and sell-through with a seed band. Question: pre-approve the method so the run and record proceed in Round 2, or review the record after the run. Pre-approve: the memo's final numbers land in this round if time allows. Review after: the memo stays interim. Recommendation: pre-approve; the default path is bit-identical to today's engine at the same seed, so nothing published changes until you ratify the numbers.

**Q-J. Publishing condition.** Decided (D12): tributary publishes by manual dispatch "until the human review pass". Your 2026-08-31 read was that pass and produced this reframe. Question: keep manual dispatch through the reframe and flip to publish-on-push after D14's commits deploy, or keep manual indefinitely. Recommendation: flip after the reframe deploys and you have read the new site once; recorded in D14's consequences.

**Q-K. Record and graph commitments already assumed by this plan, for confirmation.** Ids INT-017, D14 (repositioning), D15 (separation), D16 (retroactive 2026-08-20 directive), D17 (ledger clause), D18 (Phase 6 method); filenames of existing case-study pages unchanged to preserve URLs; the identity page retitled but not renamed; the Local unit's (d) figures recomputed by script before any appears on a page. Question: accept or amend any of these. Recommendation: accept.
