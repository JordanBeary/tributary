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
