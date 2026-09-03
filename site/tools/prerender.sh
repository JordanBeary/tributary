#!/bin/sh
# Quarto pre-render hook: copy static artifacts from their source-of-truth
# locations into the site tree. Copies are git-ignored; the originals in
# analysis/ and docs/ remain the only versioned copies (2026-08-20 directive:
# the site is a presentation layer over cached static artifacts).
set -eu

# Quarto runs pre-render with cwd = the project directory (site/).
SITE_DIR="$(pwd)"
REPO_ROOT="$(dirname "$SITE_DIR")"

# Phase 4 dashboards: self-contained static Plotly HTML (aggregates inlined at build).
mkdir -p "$SITE_DIR/tributary/embedded"
cp "$REPO_ROOT"/analysis/dashboards/out/*.html "$SITE_DIR/tributary/embedded/"

# Cost receipts: billing-console screenshots referenced by the cost page.
mkdir -p "$SITE_DIR/assets/img"
cp "$REPO_ROOT"/docs/img/aws-cost-2026-08-14.png \
   "$REPO_ROOT"/docs/img/gcp-cost-2026-08-14.png \
   "$SITE_DIR/assets/img/"

# Method page: provenance-by-phase chart, generated from commit trailers by
# meta/tools/provenance_by_phase.py --write (committed SVG; no runtime here).
cp "$REPO_ROOT"/meta/provenance_by_phase.svg "$SITE_DIR/assets/img/"

# Phase 5/6 model evaluation reports and the Phase 6 validation page: static
# Plotly HTML embedded by the models page (methodology D11, validation D18).
cp "$REPO_ROOT"/models/out/m*.html "$SITE_DIR/tributary/embedded/"

# Strategy memo: single-sourced from models/strategy_memo.md. The copy drops
# the file's H1 (the Quarto page supplies the title) and is underscore-
# prefixed so Quarto includes it without rendering it as a page.
MEMO="$REPO_ROOT/models/strategy_memo.md"
if [ -f "$MEMO" ]; then
  sed '1{/^# /d;}' "$MEMO" > "$SITE_DIR/tributary/embedded/_strategy_memo_body.md"
else
  # A checkout without the memo must still render: leave a one-line
  # placeholder so the include resolves.
  echo "*The strategy memo is not present in this checkout.*" \
    > "$SITE_DIR/tributary/embedded/_strategy_memo_body.md"
  echo "prerender: models/strategy_memo.md absent; placeholder written" >&2
fi
