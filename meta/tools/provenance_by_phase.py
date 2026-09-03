#!/usr/bin/env python3
"""Provenance by phase: regenerate the contribution ledger from git commit trailers.

The charter (meta/charter.md Section 2) makes "commit trailers + the ledger in
meta/provenance.md" the provenance half of every phase gate. Commit trailers are
the ground truth; this script turns them into the human-readable ledger so the
ledger can never drift from git.

Outputs (all deterministic from `git log`):
  1. A per-commit table and a per-phase summary table, written into
     meta/provenance.md between the markers
     `<!-- provenance-by-phase:begin -->` and `<!-- provenance-by-phase:end -->`
     (the frozen backfill rows above the markers are left untouched).
  2. A static SVG bar chart, meta/provenance_by_phase.svg (no external
     services; the site pre-render hook copies it into the site tree).

Usage:
  .venv/bin/python meta/tools/provenance_by_phase.py            # print tables
  .venv/bin/python meta/tools/provenance_by_phase.py --write    # update files
  .venv/bin/python meta/tools/provenance_by_phase.py --check    # exit 1 if stale
"""

from __future__ import annotations

import argparse
import collections
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LEDGER_PATH = REPO_ROOT / "meta" / "provenance.md"
SVG_PATH = REPO_ROOT / "meta" / "provenance_by_phase.svg"
BEGIN = "<!-- provenance-by-phase:begin -->"
END = "<!-- provenance-by-phase:end -->"

LEVELS = ("H", "HD", "A")
PHASES = ("0", "0.5", "1", "2", "3", "4", "5", "6", "7", "unmapped")

# Git log record separators (ASCII unit / record separators; safe in subjects).
FIELD, RECORD = "\x1f", "\x1e"
LOG_FORMAT = (
    "%h" + FIELD + "%ad" + FIELD + "%s" + FIELD
    + "%(trailers:key=Provenance,valueonly,separator=;)" + FIELD
    + "%(trailers:key=Directs,valueonly,separator=;)" + RECORD
)


# ---------------------------------------------------------------------------
# Phase-mapping rule. Commits do not carry a phase trailer, so the phase is
# derived, in this order of precedence:
#   1. an explicit `Phase N` at the start of the subject wins;
#   2. hand-mapped exceptions (a meta commit that logs another phase's work);
#   3. subject keywords that identify the phase on days when two phases were
#      worked (2026-08-03, 2026-08-20, 2026-08-24);
#   4. the date window the phase was active in, from the handoff notes in
#      meta/logs/sessions/.
# Anything the rule cannot place is reported as "unmapped" rather than
# silently assigned, so a new commit that breaks the rule is visible.
# ---------------------------------------------------------------------------
EXCEPTIONS = {
    "7423c2d": "1",    # meta commit logging the Phase 1 sentinel intervention (INT-011)
    "9fbc7e0": "0.5",  # verbatim Phase 0 session log, committed during the migration
    "f875df9": "0.5",  # INT-010 (no AI co-author trailers) is a harness rule
    "a295198": "1",    # D4 dataset acquisition is Phase 1 work
    "1f0f4d2": "1",    # project guide: datasets acquired (Phase 1)
}
MIGRATION_KEYWORDS = ("meta:", "Reconcile local track", "Rename cloud resources",
                      "global-track scaffold")
PHASE3_KEYWORDS = ("D7 ", "D8", "C18", "ER exit", "D9 ", "Splink", "staging layer")
PHASE4_KEYWORDS_0824 = ("C19", "D10")
DATE_WINDOWS = (
    # (last date inclusive, phase) — evaluated in order.
    ("2026-07-31", "0"),
    ("2026-08-12", "1"),
    ("2026-08-14", "2"),
)


def map_phase(short_hash: str, date: str, subject: str) -> str:
    m = re.match(r"Phase (\d(?:\.\d)?)[: ]", subject)
    if m:
        return m.group(1)
    if short_hash in EXCEPTIONS:
        return EXCEPTIONS[short_hash]
    if date == "2026-08-03" and any(k in subject for k in MIGRATION_KEYWORDS):
        return "0.5"
    if date == "2026-08-20":
        return "3" if any(k in subject for k in PHASE3_KEYWORDS) else "4"
    if date == "2026-08-24":
        return "4" if any(k in subject for k in PHASE4_KEYWORDS_0824) else "5"
    for last_date, phase in DATE_WINDOWS:
        if date <= last_date:
            return phase
    if date >= "2026-08-28":
        # Phase 7 (site) and the 2026-09-01 reframe that followed it; Phase 6
        # commits are identified by their explicit subject prefix (rule 1).
        return "7"
    return "unmapped"


# ---------------------------------------------------------------------------
# Data collection
# ---------------------------------------------------------------------------
def read_commits() -> list[dict]:
    out = subprocess.run(
        ["git", "log", "--reverse", "--date=short", "--format=" + LOG_FORMAT],
        capture_output=True, text=True, check=True, cwd=REPO_ROOT,
    ).stdout
    commits = []
    for rec in out.split(RECORD):
        if not rec.strip():
            continue
        h, d, s, prov, directs = (part.strip() for part in rec.strip("\n").split(FIELD))
        prov = prov.replace("\n", " ").strip() or "none"
        directs = ", ".join(p.strip() for p in directs.replace("\n", ";").split(";") if p.strip())
        commits.append({
            "hash": h, "date": d, "subject": s, "provenance": prov,
            "directs": directs, "phase": map_phase(h, d, s),
        })
    return commits


def summarize(commits: list[dict]) -> dict[str, collections.Counter]:
    table: dict[str, collections.Counter] = {p: collections.Counter() for p in PHASES}
    for c in commits:
        row = table[c["phase"]]
        row[c["provenance"] if c["provenance"] in LEVELS else "none"] += 1
        row["total"] += 1
        if c["directs"]:
            row["directs"] += 1
    return table


# ---------------------------------------------------------------------------
# Renderers
# ---------------------------------------------------------------------------
def render_markdown(commits: list[dict]) -> str:
    table = summarize(commits)
    lines = [
        BEGIN,
        "",
        f"*Generated by `meta/tools/provenance_by_phase.py` from `git log` "
        f"({len(commits)} commits through `{commits[-1]['hash']}`, {commits[-1]['date']}). "
        "Do not edit by hand; rerun the script with `--write`. The phase-mapping rule is in the script.*",
        "",
        "**By phase**",
        "",
        "| Phase | H | HD | A | no trailer | total | with `Directs` |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    total = collections.Counter()
    for p in PHASES:
        row = table[p]
        if row["total"] == 0:
            continue
        total.update(row)
        lines.append(f"| {p} | {row['H']} | {row['HD']} | {row['A']} | {row['none']} | {row['total']} | {row['directs']} |")
    lines.append(f"| **all** | **{total['H']}** | **{total['HD']}** | **{total['A']}** | **{total['none']}** | **{total['total']}** | **{total['directs']}** |")
    lines += [
        "",
        "Reading the table: no commit is `H`. The human's authored contribution enters through "
        "`HD` commits — the prompts, domain data, and ratification text that directed them — rather "
        "than through commits of the human's own; the four commits without a trailer predate the "
        "harness and are covered by the backfill rows above.",
        "",
        "**By commit**",
        "",
        "| Commit | Date | Phase | Provenance | Directs | Subject |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for c in commits:
        subject = c["subject"].replace("|", "\\|")
        lines.append(f"| `{c['hash']}` | {c['date']} | {c['phase']} | {c['provenance']} | {c['directs'] or '-'} | {subject} |")
    lines += ["", END]
    return "\n".join(lines)


def render_svg(commits: list[dict]) -> str:
    """Horizontal stacked bars per phase: HD, A, and untrailed commits. Neutral palette."""
    table = summarize(commits)
    phases = [p for p in PHASES if table[p]["total"] > 0]
    max_total = max(table[p]["total"] for p in phases)
    colours = {"HD": "#3b5b8c", "A": "#a9b7c9", "none": "#e2e6ec"}
    labels = {"HD": "human-directed (HD)", "A": "agent-drafted (A)", "none": "pre-harness, no trailer"}
    left, top, bar_h, gap, unit = 150, 56, 22, 12, 22  # px; unit = px per commit
    width = left + max_total * unit + 60
    height = top + len(phases) * (bar_h + gap) + 40
    font = "font-family='-apple-system, Segoe UI, Helvetica, Arial, sans-serif'"
    parts = [
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' "
        f"viewBox='0 0 {width} {height}' role='img' aria-label='Commits per phase by provenance level'>",
        f"<title>Commits per phase by provenance level</title>",
        f"<rect width='{width}' height='{height}' fill='#ffffff'/>",
        f"<text x='{left}' y='22' {font} font-size='14' font-weight='600' fill='#1f2933'>Commits per phase by provenance level</text>",
    ]
    # Legend
    x = left
    for key in ("HD", "A", "none"):
        parts.append(f"<rect x='{x}' y='32' width='12' height='12' fill='{colours[key]}' stroke='#7b8794' stroke-width='0.5'/>")
        parts.append(f"<text x='{x + 17}' y='42' {font} font-size='11' fill='#3e4c59'>{labels[key]}</text>")
        x += 17 + 8 * len(labels[key]) + 14
    y = top
    for p in phases:
        row = table[p]
        parts.append(f"<text x='{left - 10}' y='{y + bar_h - 6}' {font} font-size='12' fill='#1f2933' text-anchor='end'>Phase {p}</text>")
        x = left
        for key in ("HD", "A", "none"):
            n = row[key]
            if n == 0:
                continue
            w = n * unit
            parts.append(f"<rect x='{x}' y='{y}' width='{w}' height='{bar_h}' fill='{colours[key]}' stroke='#ffffff' stroke-width='1'/>")
            if w >= 16:
                fill = "#ffffff" if key == "HD" else "#1f2933"
                parts.append(f"<text x='{x + w / 2}' y='{y + bar_h - 7}' {font} font-size='11' fill='{fill}' text-anchor='middle'>{n}</text>")
            x += w
        parts.append(f"<text x='{x + 6}' y='{y + bar_h - 6}' {font} font-size='11' fill='#52606d'>{row['total']}</text>")
        y += bar_h + gap
    parts.append(f"<text x='{left}' y='{height - 12}' {font} font-size='10' fill='#7b8794'>Source: git commit trailers (Provenance: H | HD | A). No commit is H; the human's authored input arrives inside HD commits.</text>")
    parts.append("</svg>")
    return "\n".join(parts)


def splice(ledger_text: str, block: str) -> str:
    if BEGIN in ledger_text and END in ledger_text:
        head = ledger_text[: ledger_text.index(BEGIN)]
        tail = ledger_text[ledger_text.index(END) + len(END):]
        return head + block + tail
    return ledger_text.rstrip("\n") + "\n\n### 3.1 Ledger generated from commit trailers\n\n" + block + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true", help="update meta/provenance.md and the SVG")
    ap.add_argument("--check", action="store_true", help="exit 1 if the committed ledger is stale")
    args = ap.parse_args()

    commits = read_commits()
    unmapped = [c for c in commits if c["phase"] == "unmapped"]
    block = render_markdown(commits)
    svg = render_svg(commits)

    if args.write:
        LEDGER_PATH.write_text(splice(LEDGER_PATH.read_text(), block))
        SVG_PATH.write_text(svg + "\n")
        print(f"wrote {LEDGER_PATH.relative_to(REPO_ROOT)} and {SVG_PATH.relative_to(REPO_ROOT)}")
    elif args.check:
        current = LEDGER_PATH.read_text()
        stale = BEGIN not in current or splice(current, block) != current
        print("provenance ledger is", "STALE" if stale else "current")
        return 1 if stale or unmapped else 0
    else:
        print(block)

    if unmapped:
        print(f"WARNING: {len(unmapped)} commit(s) could not be mapped to a phase:", file=sys.stderr)
        for c in unmapped:
            print(f"  {c['hash']} {c['date']} {c['subject']}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
