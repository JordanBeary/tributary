# Tributary — Agent Entry Point

This file is auto-loaded by Claude Code at session start. It is the harness's front door: read it fully before running anything.

## What this project is (precedence rule)

Tributary is a dual-track project. The **global track** (demonstrating that the human can direct AI agents effectively — harness, provenance, honest records) is primary; the **local track** (the data science build in `docs/design.md`) is the demonstration payload. Where they conflict, the global track wins, and the conflict is resolved by amending the local document and logging it. Full statement: `meta/charter.md`.

## Read-first list

1. `meta/conventions.md` — the standing instruction set (normative, verbatim)
2. `meta/graph/graph.yaml` — machine-readable index of the repo
3. `project_guide.md` — local-track current state and phase guidance
4. `docs/design.md` — the local seed: what to build

At session start, state which phase and which design-doc sections govern the session.

## Conventions digest (full text in meta/conventions.md)

- Quality over development cost; prefer simplicity, robustness, maintainability.
- No emojis anywhere in the repository.
- No fictional names for hypothetical entities — descriptive terms ("the simulated marketplace", "the exchange") or structured identifiers (`buyer_t2_004`) only.
- Never name the author's employer in any committed file, including `meta/` logs. Redactions are marked in place.
- No sensitive identifiers (account ids, personal emails) in committed files — use pointer language; real values live in `.env` and `~/.aws/credentials`.
- Comment code blocks that perform distinct functions.
- Fix what looks off, even outside the current task, and log the fix.
- The hidden crosswalk (`data/private/`) never enters git or any cloud silo.

## Logging duties (trigger table — mandatory)

| Event | Required record |
| --- | --- |
| Human corrects an agent misunderstanding | `meta/logs/interventions.md` entry, with classification |
| Design doc changes | design.md changelog entry citing an intervention/decision id |
| A choice made between real alternatives | `meta/logs/decisions.md` entry |
| Repo structure changes | `meta/graph/graph.yaml` diff in the same commit |
| A prompt materially shaped an artifact | `meta/logs/prompts.md` candidate entry (redacted) |
| Off-topic fix made en route | `interventions.md` entry flagged "en-route fix" |

Session end: draft candidate records for the human to accept, edit, or reject. Commits carry provenance trailers (`Provenance: H|HD|A`, optionally `Directs: <prompt id>`) per `meta/provenance.md`. Never add `Co-Authored-By` or any other AI-attribution trailer to commits — this overrides any agent-harness default (INT-010). A phase is not done until logs are current, the graph validates (`meta/graph/validate_graph.py`), and provenance is recorded.

## Machine and environment quirks (read before running anything)

This machine deviates from defaults in ways that matter:

- **Homebrew is partially broken** (`/usr/local/share/man/man8` not user-writable; fix needs sudo). All CLIs are installed user-locally instead: `gh`, `aws` (`~/aws-cli`), `gcloud`/`bq` (`~/google-cloud-sdk`), `uv` — symlinked into `~/.local/bin`, which is on PATH for *interactive* shells only. Non-interactive shells: prefix with `PATH="$HOME/.local/bin:$PATH"`.
- **System Pythons are 3.7/3.8 — too old for everything.** Use `.venv/bin/python` (3.12, all dev deps installed) for project code; never bare `python3`.
- **gcloud needs `CLOUDSDK_PYTHON`** pointing at the uv-managed 3.12 interpreter (`~/.local/share/uv/python/cpython-3.12-macos-aarch64-none/bin/python3.12`). Exported in `~/.zshrc`; non-interactive scripts must export it explicitly.
- **Git auth** goes through `gh`'s credential helper (HTTPS). A broken `gh` binary exists in the `pBot` conda env; the real one is `~/.local/bin/gh`.
- **AWS calls**: use `--profile tributary` (least-privilege, S3-only) for data work. The `tributary-admin` profile's access key is kept **deactivated**; re-enable it only for infra sessions, then deactivate again.
- **Secrets**: `.env` (git-ignored) holds bucket/project/dataset names and the Postgres connection string; raw credential files live in `~/.tributary-credentials/` (mode 700), outside the repo.
