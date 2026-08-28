# site

Quarto site (Phase 7, D12): profile, resume, case study, embedded dashboards.

- Render locally: `quarto render site` from the repo root (`quarto` is
  symlinked in `~/.local/bin`; non-interactive shells need
  `PATH="$HOME/.local/bin:$PATH"`). Preview with `quarto preview site`.
- `tools/prerender.sh` copies the static artifacts (Phase 4 dashboard HTML,
  billing screenshots) from their source-of-truth locations into git-ignored
  spots in the site tree; nothing under `tributary/embedded/` or
  `assets/img/` is versioned here.
- Publishing: `.github/workflows/publish-site.yml` renders and deploys to
  GitHub Pages (manual `workflow_dispatch` until launch; flip to on-push
  after the human review pass).
- First-release scope (D12): Phases 0–4 content only. ML and strategy pages
  are added after D11 ratifies and Phase 6 closes.
- The resume page renders HTML and the downloadable PDF from one source
  (`resume.qmd`, html + typst formats). Per D13 it names employers but
  carries no performance KPIs and no personal contact identifiers; the
  full-KPI resume stays off-repo.
