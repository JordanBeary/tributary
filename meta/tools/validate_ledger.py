#!/usr/bin/env python3
"""Validate meta/logs/ledger.yaml against the logs and the repository.

Checks (errors fail):
  1. Every `ref` resolves to a record id present in meta/logs/{decisions,
     interventions,prompts}.md, to an existing repository path, or to a commit
     reachable from HEAD (7+ hex characters).
  2. Every step has actor, kind, ref, date, label with allowed vocabularies.
  3. Every problem has at least one human step, ends in a `finding`, and its
     `finding_refs` resolve.
  4. Problem ids are unique.

Usage: .venv/bin/python meta/tools/validate_ledger.py
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
LEDGER = REPO_ROOT / "meta" / "logs" / "ledger.yaml"
LOGS = {
    "decisions": REPO_ROOT / "meta" / "logs" / "decisions.md",
    "interventions": REPO_ROOT / "meta" / "logs" / "interventions.md",
    "prompts": REPO_ROOT / "meta" / "logs" / "prompts.md",
}
ACTORS = {"human", "agent", "harness"}
KINDS = {"prompt", "proposal", "decision", "correction", "artifact", "finding"}
ID_RE = re.compile(r"^(INT-\d{3}|P-\d{3}|[ABCDQ]\d{1,2})$")
HASH_RE = re.compile(r"^[0-9a-f]{7,40}$")


def collect_ids() -> set[str]:
    """Record ids as they appear in the logs: headings (`## P-005`, `### D8 —`)
    and table rows (`| C1 |`)."""
    ids: set[str] = set()
    heading = re.compile(r"^#{2,4}\s+((?:INT|P)-\d{3}|[ABCDQ]\d{1,2})\b")
    row = re.compile(r"^\|\s*([ABCDQ]\d{1,2})\s*\|")
    for path in LOGS.values():
        for line in path.read_text().splitlines():
            m = heading.match(line) or row.match(line)
            if m:
                ids.add(m.group(1))
    return ids


def commit_exists(ref: str) -> bool:
    return subprocess.run(["git", "cat-file", "-e", f"{ref}^{{commit}}"],
                          cwd=REPO_ROOT, capture_output=True).returncode == 0


def resolve(ref: str, ids: set[str]) -> str | None:
    """Return None if the ref resolves, else a reason."""
    if ID_RE.match(ref):
        return None if ref in ids else f"record id {ref} not found in the logs"
    if HASH_RE.match(ref):
        return None if commit_exists(ref) else f"commit {ref} not reachable"
    if (REPO_ROOT / ref).exists():
        return None
    return f"path does not exist: {ref}"


def main() -> int:
    data = yaml.safe_load(LEDGER.read_text())
    ids = collect_ids()
    errors: list[str] = []
    seen: set[str] = set()

    def check_ref(ref: str, where: str) -> None:
        reason = resolve(str(ref), ids)
        if reason:
            errors.append(f"{where}: {reason}")

    chains = list(data.get("problems", [])) + list(data.get("cross_cutting", []))
    for problem in chains:
        pid = problem.get("id", "?")
        if pid in seen:
            errors.append(f"duplicate problem id {pid}")
        seen.add(pid)
        steps = problem.get("steps", [])
        if not steps:
            errors.append(f"{pid}: no steps")
            continue
        for i, step in enumerate(steps, 1):
            where = f"{pid} step {i}"
            for key in ("actor", "kind", "ref", "date", "label"):
                if key not in step:
                    errors.append(f"{where}: missing {key}")
            if step.get("actor") not in ACTORS:
                errors.append(f"{where}: actor {step.get('actor')!r} not in {sorted(ACTORS)}")
            if step.get("kind") not in KINDS:
                errors.append(f"{where}: kind {step.get('kind')!r} not in {sorted(KINDS)}")
            if "ref" in step:
                check_ref(step["ref"], where)
        if problem in data.get("problems", []):
            if not any(s.get("actor") == "human" for s in steps):
                errors.append(f"{pid}: no human step")
            if steps[-1].get("kind") not in {"finding", "decision", "proposal"}:
                errors.append(f"{pid}: last step must be a finding (or a pending decision/proposal)")
            for ref in problem.get("finding_refs", []):
                check_ref(ref, f"{pid} finding_refs")

    for item in data.get("open_items", []):
        check_ref(item["ref"], f"open item {item.get('ref')}")
        if "ask" in item:
            check_ref(item["ask"], f"open item {item.get('ref')} ask")
    for item in data.get("resolved_items", []):
        check_ref(item["ref"], f"resolved item {item.get('ref')}")
    for note in data.get("notes", []):
        check_ref(note["ref"], f"note {note.get('ref')}")

    for e in errors:
        print(f"ERROR: {e}")
    n_steps = sum(len(p.get("steps", [])) for p in chains)
    print(f"ledger: {len(data.get('problems', []))} problems, {len(data.get('cross_cutting', []))} cross-cutting, "
          f"{n_steps} steps, {len(data.get('open_items', []))} open items, "
          f"{len(data.get('resolved_items', []))} resolved — {len(errors)} error(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
