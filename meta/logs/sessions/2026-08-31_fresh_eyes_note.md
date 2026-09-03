# Tributary — Fresh-Eyes Project Summary

Written 2026-08-31 from a full review of the repository (design doc, project guide, charter, `meta/` logs, pipeline code, and site), without directly quoting the current documentation.
Provenance: A — agent-drafted fresh-eyes review, human-reviewed. Committed 2026-09-02 (decision packet Q-H) because it is the input the human attached to P-013, the prompt that triggered the reframe; it is a working note of that date, not a maintained document, and its "where it stands" section is superseded by the records of 2026-09-01/02.

---

## What this project is

Tributary is a public portfolio project with an unusual inversion at its core: the data science build is not the real product. The repo runs two tracks at once, and the explicitly primary one is a demonstration of *working method* — that a human can direct AI agents to produce real, verifiable work while keeping an auditable record of who contributed what, where the agents went wrong, and how decisions actually got made. The end-to-end data build is deliberately framed as the payload that makes the method demonstrable. The intended audience is recruiters, interviewers, and technical evaluators, reached through a public repo and a Quarto site on GitHub Pages that doubles as a professional profile.

## The demonstration payload

The technical track simulates the data environment of a fictional (and pointedly unnamed) two-sided marketplace that auctions personal-loan leads to lenders through a six-tier waterfall. A seeded simulator — statistically calibrated against three public datasets (LendingClub for applicant features, iPinYou for auction price landscapes, Criteo for marketing uplift) plus two redacted industry tables — generates a coherent world of about 1.5M consumer records, 2.4M applications, and 26M auction events, then deliberately shatters it into three architecturally real cloud silos (S3 Parquet lake, Neon Postgres CRM, BigQuery marketing exports) with incompatible keys, mismatched grains, three timezones, ~8% duplicate identities, and ~5% orphaned records.

The signature move is evaluability: every consumer's true identity is stripped out and kept in a local, git-ignored crosswalk that never touches the cloud. That means the entity-resolution and warehousing work that reunifies the silos (Splink probabilistic matching plus deterministic SQL, a dbt layer, wide analytical marts) can be *scored*, not just claimed — and it was: roughly 0.87–0.88 F1 on the linkage tasks, with about 95% of auction revenue events becoming consumer-joinable versus 0% before. Notably, the difficulty was tuned *down* into a target band after the first attempt scored suspiciously near-perfect — realism was treated as something to engineer, not assume. On top of the unified layer sit six dashboards answering the questions the silos individually couldn't (true marketing ROI through to auction revenue, the dollar cost of duplicate consumers, funnel economics), and four trained models: calibrated sale propensity, a censored winning-price model, a counterfactual floor-price optimization showing a ~2% earnings-per-lead lift, and an uplift model that recovers the small injected treatment effect. Cost discipline is itself content: the whole thing runs on free tiers for pennies a month, with budget screenshots, bytes-scanned benchmarks, and free-tier fit engineering kept as deliverables.

## The main themes

1. **Method as exhibit.** The `meta/` directory is the thesis: a charter, twelve standing working agreements, a decision log (~55 records where agents propose and the human ratifies, amends, or rejects), an intervention log of 16 agent mistakes and corrections, a verbatim prompt log, and per-commit provenance trailers classifying work as human-authored, human-directed, or agent-executed. A phase is not "done" when code works — only when its records are current.
2. **Honesty as a design constraint.** Failures are preserved, not polished away: a calibration the project's own QA gate falsified is kept and superseded rather than rewritten; a deliberately failing model specification is documented as such; an underpowered experiment is reported as underpowered.
3. **Provability over narrative.** Every headline claim traces to a scored artifact — the hidden crosswalk turns "we unified the silos" into precision/recall numbers, and calibration parameters trace to fitted distributions or declared assumptions.
4. **Constraint engineering.** Free-tier economics, confidentiality (the employer is never named; no fictional company names either), reproducibility (one seeded command regenerates everything; 58 tests run from committed artifacts alone), and a static-only public site are all treated as first-class requirements.

## Where it stands

Phases 0–4 (setup, harness, simulation, silo deployment, unification, analytics) are complete and published; the four ML models are built but held off the site pending a human ratification decision (D11); the optimization/strategy phase (6) hasn't started; and the site shipped early under D12, first deployed 2026-08-28, with human review, on-push publishing, a domain, and peer review still outstanding before launch.

One small fresh-eyes finding: the README's phase checklist is stale — it still shows Phases 1–7 unchecked and cites the superseded F1 target, contradicting the project guide and decision log.
