# Session Log — Phase 0 Build (2026-07-30 → 2026-08-03)

A verbatim record of the working session that executed Phase 0: repo scaffold, calibration spec, GitHub setup, CLI tooling, cloud provisioning, and the project guide. This is a global-track record (honest process evidence), written by the agent from the session context at the human's request (Turn 8).

**Scope and method.** Human prompts and all user-visible agent prose are reproduced verbatim, in order. Tool invocations and their outputs are NOT reproduced — they are condensed into bracketed italic notes like *[tool: ...]* — because several tool payloads contained live credentials. Formatting (headings, tables, code fences) inside agent responses is preserved as written.

**Redactions, marked in place** (conventions Section 2): one personal email address is rendered `[personal email redacted]`. No credentials appear anywhere in this log.

**Naming note (INT-001 / decisions D2, D3).** This session predates the fictional-name reversal of 2026-08-03. Historical resource identifiers derived from the retired fictional name (`clx-auction-lake-jb`, `clx_marketing`, `tributary-clx`) appear below exactly as they were used at the time; those resources were later renamed/recreated (`tributary-auction-lake-jb`, dataset `marketing`, project `tributary-jb`). The identifiers are kept verbatim here as historical fact, per the honesty-over-flash instruction; they are retired, not current.

---

## Turn 1 — 2026-07-30

*[Session opened with the local command `/model claude-fable-5[1m]`; stdout: "Set model to claude-fable-5".]*

**Human:**

> Read tributary_project_design.md completely and begin working on next steps.

**Agent:**

*[tool: Read — tributary_project_design.md, all 348 lines]*

I've read the design doc. Let me check the current state of the repo to see what exists already.

*[tool: Bash — ls + find: repo contained only tributary_project_design.md; not yet a git repo]*

The repo is empty except for the design doc, so I'm starting at Phase 0 / §12: stand up the repository (structure, devcontainer, git), write the calibration spec (§12.3), and create the infra setup scripts and dataset download helpers. Cloud account creation and the domain purchase are yours to do — I'll leave a checklist.

Let me scaffold the repo now.

*[tool: Bash — `git init -b main` failed (git 2.24 lacks -b); retried with `git init` + `git symbolic-ref`; created directory tree per design §11; moved design doc to docs/design.md]*

Now writing the core files — README, gitignore, env template, devcontainer, and Python packaging:

*[tool: Write — .gitignore, .env.example, README.md, .devcontainer/devcontainer.json, pyproject.toml]*

Now the calibration spec — §12 item 3, mapping each source dataset's distributions to simulator parameters:

*[tool: Write — docs/calibration_spec.md (fitting methods + QA gates for LendingClub / iPinYou / Criteo)]*

Now the simulation package skeleton with CLI, config, and staged pipeline:

*[tool: Write — simulation/__init__.py, config.py, __main__.py, pipeline.py, stages.py]*

Now the infra setup scripts (Phase 0 exit criteria: clouds reachable, budget alarms live) and the dataset download helper:

*[tool: Write — infra/aws/setup.sh, iam_policy.json, budget.json, budget-notifications.json; infra/gcp/setup.sh; scripts/download_datasets.sh]*

Finishing up: placeholder READMEs so empty phase directories track in git, then verify the package imports, and commit:

*[tool: Bash — chmod scripts, wrote per-directory READMEs, smoke-tested `python -m simulation --help` (parsed correctly)]*

**Human (mid-turn):**

> I have a github account I would like to store this project at here is the repository - https://github.com/JordanBeary/tributary.git

**Agent (continuing):**

The package imports and the CLI works. Now I'll commit and push to your GitHub repo as requested:

*[tool: Bash — root commit "Phase 0: repo scaffold, design doc, calibration spec, infra scripts" (25 files); added remote; push failed: no HTTPS credentials]*

HTTPS push needs credentials — let me try the `gh` CLI:

*[tool: Bash — gh not installed; SSH key present but rejected by GitHub (publickey)]*

Phase 0 is scaffolded, committed, and smoke-tested — but the push to GitHub is blocked on authentication, which only you can provide. Here's where things stand.

## What I built (25 files, committed on `main`)

**Docs** — Your design doc moved to [docs/design.md](docs/design.md) as §12 specifies, plus a new [docs/calibration_spec.md](docs/calibration_spec.md) (§12 item 3): a parameter-by-parameter mapping from the three source datasets to simulator parameters — LendingClub copula → consumer features and quality score, iPinYou → lognormal valuation landscape and censoring dynamics, Criteo → uplift size and heterogeneity — each with fitting methods and quantitative QA gates. A key design decision baked in: profiling notebooks fit distributions once and write JSON artifacts to `simulation/params/`, so the simulator never needs the multi-GB raw downloads.

**Simulation package** — A runnable skeleton with the five-stage pipeline from §3.2: seeded [SimConfig](simulation/config.py) with the `--scale` dial and pathology dials, a CLI (`python -m simulation --scale 0.01`), and [stages.py](simulation/stages.py) with fixed contracts (inputs, outputs, formats) so downstream phases can build against them. Stage bodies are Phase 1 work. CLI verified working.

**Infra** — [infra/aws/setup.sh](infra/aws/setup.sh) creates the bucket, blocks public access, and sets the $10 budget with 50/80/100% email alerts; [infra/gcp/setup.sh](infra/gcp/setup.sh) creates the BigQuery dataset and prints the budget-alert command; least-privilege IAM policy JSON included. Also: devcontainer, `pyproject.toml`, [scripts/download_datasets.sh](scripts/download_datasets.sh), and a `.gitignore` that keeps secrets, raw data, and the private crosswalk out of git.

## Blocked: pushing to GitHub

The remote `https://github.com/JordanBeary/tributary.git` is configured, but there are no stored GitHub credentials on this machine — HTTPS has no credential helper, `gh` isn't installed, and your `~/.ssh/id_rsa` key isn't registered with GitHub (permission denied). Fastest fix, either:

- `brew install gh && gh auth login` — then tell me and I'll push, or
- Add `~/.ssh/id_rsa.pub` to GitHub (Settings → SSH keys), then I'll switch the remote to SSH and push.

## Your remaining Phase 0 items

1. Authenticate GitHub (above) so I can push.
2. Create AWS + GCP accounts, then run the two `infra/` setup scripts — that completes the Phase 0 exit criteria (budget alarms live, clouds reachable).
3. Buy the domain (only recurring cost, ~$12/yr).
4. Kaggle API token, then `scripts/download_datasets.sh` to start Phase 1 (iPinYou is a manual download; the script prints instructions).

Once the datasets land, the next build step is the three profiling notebooks in `analysis/profiling/` per the calibration spec's checklist.

---

## Turn 2 — 2026-07-30

**Human:**

> brew install gh && gh auth login - finished this

**Agent:**

*[tool: Bash — `gh` still not found in this shell; searched /opt/homebrew and /usr/local: no binary; brew reported no keg; mdfind located a gh inside the pBot conda env]*

Found a `gh` binary (in your anaconda env — the brew one isn't on this shell's PATH, but auth state is shared via `~/.config/gh`). Trying the push:

*[tool: Bash — conda-env gh failed: "exec format error" (wrong architecture)]*

That binary is broken. Let me check whether your `gh auth login` stored a token I can use directly:

*[tool: Bash — no ~/.config/gh directory exists; login-shell PATH also has no gh]*

`gh` isn't actually on this machine — brew has no keg for it, there's no binary anywhere (except a broken one in a conda env), and no auth config was written. The install may have failed silently or happened in a different environment. Let me just install it myself and see how far I get:

*[tool: Bash — `brew install gh` produced ownership warnings; gh still absent]*

The install didn't complete. Let me see the full output:

*[tool: Bash — `brew install gh` errors: /usr/local/share/man/man8 not writable by user; fix requires sudo]*

Homebrew is failing on a permissions issue (`/usr/local/share/man/man8` isn't writable — fixing that needs `sudo`, which I can't run). I'll skip brew and install the official `gh` binary directly to a user-writable location:

*[tool: Bash — downloaded gh 2.96.0 macOS arm64 release zip to scratchpad, installed binary to ~/.local/bin/gh]*

`gh` 2.96.0 is now installed at `~/.local/bin/gh` (the direct-download route worked; brew is broken by a permissions issue on `/usr/local/share/man/man8` — unrelated to us, fixable later with `sudo chown -R jordanbeary /usr/local/share/man/man8` if you ever want brew to install it properly).

The one step I can't do for you is the login itself — it's an interactive browser flow. Please run this in your terminal:

```bash
~/.local/bin/gh auth login
```

Pick **GitHub.com → HTTPS → Login with a web browser**, and complete the code prompt in your browser. Tell me when it's done and I'll push the Phase 0 commit to `https://github.com/JordanBeary/tributary.git`.

Worth noting: your earlier `brew install gh && gh auth login` evidently didn't take — brew had no `gh` keg, no `gh` was on any PATH, and there's no auth config on disk, so the login most likely errored out right after the failed install.

One optional cleanup so `gh` works in your own shell too: add `export PATH="$HOME/.local/bin:$PATH"` to your `~/.zshrc` (say the word and I'll add it).

---

## Turn 3 — 2026-07-30

**Human:**

> github should be set up now - clean up what you can regarding gh

**Agent:**

*[tool: Bash — gh auth status: logged in to github.com as JordanBeary (keyring), HTTPS protocol]*

Authenticated as JordanBeary. Now wiring git to use it and pushing:

*[tool: Bash — `gh auth setup-git`; `git push -u origin main` succeeded: new branch main]*

Pushed — `main` is live on GitHub. Now the cleanup:

*[tool: Bash — checked ~/.zshrc (no .local/bin entry) and scratchpad leftovers; appended PATH export to ~/.zshrc; removed gh.zip + extracted folder; login-shell test failed (zsh -lc does not read .zshrc)]*

`.zshrc` is only read by interactive shells, so let me verify with the right shell type:

*[tool: Bash — interactive-shell check: gh resolves at ~/.local/bin/gh v2.96.0; scratchpad empty; credential helpers for github.com point at gh]*

Everything is pushed and cleaned up. Summary:

**Pushed:** the Phase 0 commit is live at [github.com/JordanBeary/tributary](https://github.com/JordanBeary/tributary), with `main` tracking `origin/main`.

**gh cleanup, done:**
- Git is now wired to authenticate through `gh` (`gh auth setup-git`), so all future pushes/pulls to GitHub just work — verified by the successful push.
- Added `export PATH="$HOME/.local/bin:$PATH"` to your `~/.zshrc`, so `gh` resolves in your terminal (verified: `which gh` → `~/.local/bin/gh`, v2.96.0). Open a new terminal or `source ~/.zshrc` to pick it up in existing sessions.
- Removed the downloaded zip and extracted folder from the scratchpad.

**Two things I couldn't clean, for your awareness:**
- Homebrew still can't install anything that writes a man8 page until you run `sudo chown -R jordanbeary /usr/local/share/man/man8`. Not needed for this project — the direct-install `gh` is fully functional.
- There's a broken `gh` binary inside your `pBot` conda env (`~/opt/anaconda3/envs/pBot/bin/gh` — wrong architecture). I left it alone since it's inside an env I didn't create, but if you're ever in that env and `gh` errors with "exec format error", that's why — delete that file and the working one will take over.

With GitHub done, your remaining Phase 0 items are the cloud accounts (then run the two `infra/` setup scripts), the domain, and the Kaggle token for `scripts/download_datasets.sh`.

---

## Turn 4 — 2026-07-30

**Human:**

> walk me through setting up cloud accounts

**Agent:**

Let me first check what CLI tooling you already have, so the walkthrough matches your machine:

*[tool: Bash — aws, gcloud, bq, psql: none installed]*

None of the cloud CLIs are installed yet — I'll fold that into the plan. Here's the walkthrough, ordered so each account ends in a working, verified connection. The split: **browser signups and auth logins are yours** (interactive), **installs, scripts, and verification are mine** — just tell me after each auth step and I'll take it from there.

## 1. AWS — the S3 auction lake (~20 min)

**You, in the browser:**
1. Sign up at [aws.amazon.com](https://aws.amazon.com) → personal account. Needs email, credit card, phone verification. New accounts get **$200 in credits for 6 months**, so this project is effectively free on AWS during the whole build.
2. Immediately secure the root account: Console → IAM → enable **MFA on root**. Then don't use root again.
3. Create your working identity: IAM → Users → **Create user** `tributary-admin` → attach `AdministratorAccess` → after creation, open the user → Security credentials → **Create access key** (choose "CLI"). Copy the key ID + secret — you'll paste them to me or into `aws configure` yourself.

**Me, once you have the key:**
- Install the AWS CLI (brew, with a fallback if the man-page permission issue bites).
- `aws configure --profile tributary-admin` with your key.
- Run [infra/aws/setup.sh](infra/aws/setup.sh) — creates the bucket with public access blocked, plus the **$10/month budget with 50/80/100% email alerts** (Phase 0 exit criterion; screenshot the budget page afterward for the write-up).
- Create the least-privilege `tributary` IAM user scoped to just the bucket ([infra/aws/iam_policy.json](infra/aws/iam_policy.json)) — that's the profile daily work uses; the admin key goes in a drawer.

One decision for you: the bucket name must be globally unique — something like `clx-auction-lake-jb` works.

## 2. GCP — the BigQuery marketing silo (~15 min)

**You, in the browser:**
1. Go to [console.cloud.google.com](https://console.cloud.google.com), sign in with any Google account, accept terms. Add a billing account (card required) — but note BigQuery's free tier (**10 GiB storage + 1 TiB queries/month**) covers this project entirely; expected spend $0.
2. Create a project, e.g. `tributary-clx` (note the project ID it assigns).
3. Set the budget alert (this one's easier in the console than CLI): Billing → **Budgets & alerts** → Create budget → $10/month, thresholds 50/80/100%. Screenshot it.

**You in the terminal (interactive browser auth), after I install the SDK:**
- `gcloud auth login` and `gcloud auth application-default login` — each pops a browser window.

**Me, after that:**
- Run [infra/gcp/setup.sh](infra/gcp/setup.sh) — enables the BigQuery API and creates the `clx_marketing` dataset, then I'll verify with a test query from Python.

## 3. Neon — the Postgres CRM silo (~5 min, easiest)

**You, in the browser:**
1. Sign up at [neon.tech](https://neon.tech) — GitHub SSO works, and you just set that up. Free tier (0.5 GB) is why the design trims the CRM silo to fit.
2. Create a project, e.g. `clx-crm` (pick a US region to match the others).
3. From the dashboard, copy the **connection string** (`postgresql://...@....neon.tech/neondb`).

**Me:** drop it into `.env` (git-ignored, per [.env.example](.env.example)) and verify the connection from Python — no `psql` install needed.

## 4. Final verification (me)

Once all three are authed, I'll run one check per silo from this machine — an S3 write/read, a BigQuery query, a Postgres `SELECT 1` — which closes Phase 0's exit criteria: *all clouds reachable from VS Code, budget alerts live*.

A note on secrets handling: the admin access key and the Neon connection string are sensitive. Pasting them in chat here works (they land in `.env`/`~/.aws/credentials`, both git-ignored, never committed), but if you prefer, run the two `aws configure` / `.env` paste steps yourself and I'll just verify.

Suggested order: start the AWS signup first (its phone/card verification is the slowest), then GCP, then Neon. Tell me when you've finished any step and I'll pick up my side.

---

## Turn 5 — 2026-07-30

**Human:**

> All 3 accounts are made just need you to do your side

**Agent:**

On it. First the CLI installs (AWS CLI + Google Cloud SDK), then I'll check what auth material exists and tell you exactly what's still needed from your side.

*[tool: Bash — `brew install awscli` failed on the same man8 permission error]*

Brew hits the same permissions wall for `awscli`. No problem — AWS documents a user-local install of the official pkg that needs no sudo:

*[tool: Bash — downloaded AWSCLIV2.pkg, installed with `installer -target CurrentUserHomeDirectory` + choices.xml to ~/aws-cli, symlinked into ~/.local/bin; aws-cli 2.36.12 verified]*

AWS CLI 2.36.12 installed. Now the Google Cloud SDK via the official tarball (also sudo-free):

*[tool: Bash — google-cloud-cli-darwin-arm.tar.gz extracted to ~/google-cloud-sdk; install.sh failed with a Python SyntaxError]*

The SDK installer choked on an old Python. Let me find a modern interpreter and point the installer at it:

*[tool: Bash — inventory: anaconda python 3.7.16 (default python3), system 3.8.2 — nothing newer]*

Both Pythons on this machine are too old (3.7/3.8) — for gcloud *and* for this project itself (`pyproject.toml` requires ≥3.11). I'll install `uv`, use it to get a standalone modern Python (no sudo, no brew), then retry the SDK install:

*[tool: Bash — installed uv; `uv python install 3.12` → cpython 3.12.13 arm64; reran gcloud install.sh with CLOUDSDK_PYTHON set → Google Cloud SDK 578.0.0, bq 2.1.36; symlinked gcloud/bq into ~/.local/bin]*

Both CLIs are in. Now persisting the Python config, setting up the project venv, and checking auth state:

*[tool: Bash — appended CLOUDSDK_PYTHON export to ~/.zshrc; created .venv (Python 3.12) and installed `.[dev]`; verified imports of boto3, bigquery, psycopg2, duckdb, splink; auth check: no AWS credentials, no gcloud account, no .env]*

All tooling is now in place. I pre-filled `.env` with what I know, and here's the state of play:

*[tool: Write — .env with bucket/dataset defaults; GCP project and Neon connection left blank]*

My side is done — all tooling installed and verified. Here's what happened and the three small things only you can provide.

## Installed (all sudo-free, since Homebrew is half-broken on this machine)

- **AWS CLI 2.36.12** — official pkg, user-local install, symlinked to `~/.local/bin/aws`.
- **Google Cloud SDK 578.0.0** (`gcloud` + `bq`) — official tarball. It refused to run on this machine's Pythons (3.7/3.8), so I also installed **uv + a standalone Python 3.12**, and pointed gcloud at it (`CLOUDSDK_PYTHON` is set in your `~/.zshrc` — open a new terminal before using `gcloud` yourself).
- **Project venv** — `.venv/` on Python 3.12 with all dev deps (boto3, BigQuery client, psycopg2, DuckDB, Splink, dbt) installed and import-verified. This machine had no project-capable Python before; now `source .venv/bin/activate` and you're set.
- **`.env` created** (git-ignored), pre-filled with bucket name `clx-auction-lake-jb` and dataset `clx_marketing`.

## Blocked on you — three items, all quick

1. **AWS access key** — in the AWS console: IAM → Users → `tributary-admin` (create it with `AdministratorAccess` if you haven't) → Security credentials → Create access key (type: CLI). Then either paste the key ID + secret here, or run in your terminal:
   ```bash
   aws configure --profile tributary-admin
   ```
2. **GCP browser auth** — in a new terminal, run these two (each opens a browser):
   ```bash
   gcloud auth login
   gcloud auth application-default login
   ```
   Also tell me the **project ID** GCP assigned (visible in the console's project picker).
3. **Neon connection string** — from your Neon project dashboard, the `postgresql://...neon.tech/...` string. Paste it here or drop it into `.env` yourself under `CRM_DATABASE_URL`.

Once those land, I'll run `infra/aws/setup.sh` (bucket + $10 budget alerts to [personal email redacted] — say if you want a different alert address), create the least-privilege IAM user, run `infra/gcp/setup.sh`, and then do the three-silo reachability check that closes out Phase 0.

---

## Turn 6 — 2026-07-30

**Human:**

> aws access key is here - tributary-admin_accessKeys.csv
>
> GCP project ID is tributary-clx
>
> neon connection is here - neon_connection.txt

**Agent:**

*[tool: Bash — located both files inside the repo working directory]*

Both files are sitting inside the git repo directory — I'll use them, then move them out (they're not covered by `.gitignore`, and secrets shouldn't live in a repo). Reading them now:

*[tool: Read — both credential files (access key pair; Postgres connection string). Contents not reproduced here.]*

Configuring AWS and the `.env`, then running the AWS setup:

*[tool: Bash — configured profile tributary-admin (key + us-east-1); verified identity via STS. tool: Edit — filled GCP project id and Neon connection string into .env. tool: Bash — ran infra/aws/setup.sh: bucket clx-auction-lake-jb created, public access blocked, $10 budget with 50/80/100% alerts created]*

Bucket and budget are live. Now the least-privilege daily-work user:

*[tool: Bash — filled real bucket name into iam_policy.json; created IAM user `tributary` with the inline S3-only policy; created its access key and configured profile `tributary`; immediate STS check failed with InvalidClientTokenId]*

The key was created and configured — the identity check just hit IAM's propagation delay for brand-new keys. Retrying:

*[tool: Bash — retry loop: identity confirmed as user/tributary; S3 write → read → delete round-trip succeeded on the bucket]*

AWS silo verified end-to-end with the least-privilege user. Now Neon and GCP:

*[tool: Bash — psycopg2 connect via .env: "Neon OK: PostgreSQL 18.4"; gcloud auth list shows an authenticated account]*

GCP is authed. Running the GCP setup steps (skipping the interactive ADC step for now):

*[tool: Bash — set project tributary-clx; enabled BigQuery API; created dataset clx_marketing; found ADC credentials already present]*

ADC is already in place (you ran both auth commands — nice). Final verification from Python, then I'll secure the credential files:

*[tool: Bash — BigQuery Python client: test query returned 1; dataset listed]*

*[tool: Bash — moved both credential files to ~/.tributary-credentials/ (mode 700); git status showed iam_policy.json modified + an untracked GCP-budget-thresholds.png]*

The credential files are now in `~/.tributary-credentials/` (mode 700), outside the repo. I also spotted a `GCP-budget-thresholds.png` you dropped in the repo — let me look at it before deciding where it goes:

*[tool: Read — screenshot: GCP budget alert thresholds 50%/80%/100% at $5/$8/$10, trigger on Actual]*

That's your GCP $10 budget with 50/80/100% thresholds — exactly the cost-governance artifact the design doc says to keep for the write-up. I'll file it under `docs/img/` and commit everything:

*[tool: Bash — moved screenshot to docs/img/; commit "Phase 0 complete: cloud silos provisioned and verified"; pushed. tool: Edit — README Phase 0 checklist line updated; markdownlint warnings fixed (fence language, table pipes); commit "README: Phase 0 status + markdownlint fixes"; pushed]*

Small lint cleanup flagged by the IDE — adding a language to the diagram fence and spacing the table separator:

Phase 0 is complete and pushed. Let me save the key session facts to memory so future sessions pick up where this left off:

*[tool: Write — agent memory files (cloud resources; machine quirks) outside the repo]*

**Phase 0 is complete — all three silos are provisioned, verified, and the repo is pushed.** Verification results:

| Silo | Resource | Verified by |
| --- | --- | --- |
| S3 auction lake | `clx-auction-lake-jb` (us-east-1, public access blocked) | write → read → delete as the least-privilege user |
| Neon Postgres CRM | Postgres 18.4, connection in `.env` | `SELECT version()` from the project venv |
| BigQuery marketing | `tributary-clx:clx_marketing` | test query + dataset listing via Python client |

Cost governance is live on both clouds: AWS $10/month budget with 50/80/100% email alerts (created by the script), and your GCP budget — whose screenshot I filed at [docs/img/gcp-budget-thresholds.png](../../../docs/img/gcp-budget-thresholds.png) as the first write-up exhibit.

Security housekeeping: both credential files were moved out of the repo to `~/.tributary-credentials/` (they weren't gitignored and would have been committed). Daily work uses the least-privilege `tributary` AWS profile (S3-only, single bucket); `tributary-admin` should now sit unused — consider deactivating its key in the IAM console once you're confident everything works, and regenerate it if ever needed.

One thing worth knowing about your machine: both system Pythons are too old for modern tooling (3.7/3.8), so the project now runs on a uv-managed Python 3.12 in `.venv/` — always `source .venv/bin/activate` (or use `.venv/bin/python`) for project work.

**Next up is Phase 1** (simulation engine). Your side: the Kaggle API token (kaggle.com → Settings → Create New Token → save to `~/.kaggle/kaggle.json`), the manual iPinYou download, and the domain purchase whenever you like. Once the datasets are on disk I can start building the profiling notebooks against the calibration spec.

---

## Turn 7 — 2026-07-31

**Human:**

> Create a .md file that contains all of the project instructions, description, objective, and guidance from your perspective and include any assumptions that you have made along the way

**Agent:**

*[tool: Write — docs/project_guide.md (v1: objectives ranked, constraints, current state, decision log A/B/C series, guidance, machine quirks, open questions). tool: Bash — commit "docs: project guide & decision log"; pushed]*

Done — [docs/project_guide.md](../../../project_guide.md) is written, committed, and pushed. It's structured as the working companion to the design doc, from my perspective as your collaborator on the build:

1. **What the project is** — the one-paragraph arc from simulator to published case study.
2. **Objectives, ranked** — career artifact first, provability (the hidden crosswalk) second, cost-as-content third, reproducibility fourth. Ranking them matters when they conflict.
3. **Non-negotiables** — fictionalization, secrets hygiene, the crosswalk never entering the cloud, free-tier fit.
4. **Current state** — Phase 0 closed, with the exact resource names, profiles, and what's still pending on your side.
5. **Assumptions & decisions log** — the part you specifically asked for, split into: architecture/workflow decisions (A1–A6, e.g. the simulator reads only fitted JSON params, never raw datasets), naming/config values (B1–B5), **quantitative calibration assumptions** (C1–C8 — things like the invented $2–$120 tier price scale, the ~60% sell-through target, the message funnel rates, the duplicate-corruption mix), and my interpretations of ambiguous design points (e.g. CRM mutability means the silos will legitimately disagree — by design).
6. **Guidance ahead** — gate on exit criteria, publish incrementally, Phase 1 build order, and the key realism check: if entity resolution scores F1 ≈ 1.0, the pathologies are too clean.
7. **Machine quirks** — broken brew, old Pythons, where all the CLIs actually live, so nothing here surprises us later.
8. **Open questions** — parked, non-blocking items like the domain choice and the iPinYou sampling strategy.

Worth a skim from you in particular: the **C-series assumptions** (§5) are numbers I invented where the design doc was silent — the tier price scale (C1) and message funnel rates (C5) are the two most worth a gut-check from your industry knowledge before they get baked into the simulator in Phase 1.

*(Note added at log time: the file this turn produced was later reorganized — its content now lives at the repo root as `project_guide.md` v2.0, amended during the 2026-08-03 migration per INT-001.)*

---

## Turn 8 — 2026-08-03

**Human:**

> write a verbatim log of this session - prompts and responses

**Agent:** produced this file (`meta/logs/sessions/2026-07-30_phase0_session.md`), with the redactions and naming notes described in the header, and registered it in `meta/graph/graph.yaml`. The response to this turn is the session's closing summary and is not self-quoted here.

---

*End of log. Between Turn 7 and Turn 8, outside this session, the repository underwent the reorganization migration (charter, conventions, provenance, meta/ structure, fictional-name reversal, history rewrite) — see `meta/plan.md` Section 8 and `meta/logs/interventions.md` INT-001 through INT-008.*
