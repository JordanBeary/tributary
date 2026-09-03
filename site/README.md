# site

Quarto case-study site (Phase 7, D12): overview, identity, cost, dashboards, method, run-it. The author's profile and resume are published from the portfolio repository (`JordanBeary/JordanBeary.github.io`, D15), which links here; this site links back through "About the author".

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
- `resume.qmd` is a redirect stub only: it keeps the former `/resume.html`
  address alive and forwards it to the portfolio site. No page here names
  the author's employers.
