#!/usr/bin/env python3
"""Validate meta/graph/graph.yaml against the repository (runs in CI).

Checks (errors fail the build):
  1. Every node with a `path` points at an existing file or directory.
  2. Every edge is a [from, type, to] triple whose endpoints are known node ids
     and whose type is in the allowed edge vocabulary.
  3. Every `phase` node has at least one incoming `gates` edge.
  4. Node ids are unique.

Warnings (reported, non-fatal):
  5. Top-level repo entries not reachable from any node path — the graph should
     index everything an agent might need to find.

Usage: python meta/graph/validate_graph.py  (from the repo root or anywhere)
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
GRAPH_PATH = Path(__file__).resolve().parent / "graph.yaml"

NODE_TYPES = {"document", "directory", "phase", "dataset", "silo", "model", "decision", "log-entry"}
EDGE_TYPES = {"implements", "calibrates", "gates", "depends-on", "documents", "corrected-by"}

# Top-level entries that legitimately live outside the graph (tooling, local state).
UNINDEXED_OK = {
    ".git", ".venv", ".gitignore", ".env", ".env.example", ".DS_Store",
    "tributary.egg-info", "pyproject.toml", "data", ".pytest_cache",
}


def main() -> int:
    graph = yaml.safe_load(GRAPH_PATH.read_text())
    errors: list[str] = []
    warnings: list[str] = []

    # -- Check 4: unique ids; collect the id set for edge validation
    nodes = graph.get("nodes", [])
    ids: set[str] = set()
    for node in nodes:
        node_id = node.get("id")
        if node_id in ids:
            errors.append(f"duplicate node id: {node_id}")
        ids.add(node_id)
        if node.get("type") not in NODE_TYPES:
            errors.append(f"node {node_id}: unknown type {node.get('type')!r}")

    # -- Check 1: paths exist
    for node in nodes:
        path = node.get("path")
        if path and not (REPO_ROOT / path).exists():
            errors.append(f"node {node['id']}: path does not exist: {path}")

    # -- Check 2: edges well-formed
    gated: set[str] = set()
    for edge in graph.get("edges", []):
        if not (isinstance(edge, list) and len(edge) == 3):
            errors.append(f"malformed edge (need [from, type, to]): {edge}")
            continue
        src, etype, dst = edge
        if src not in ids:
            errors.append(f"edge {edge}: unknown source node {src!r}")
        if dst not in ids:
            errors.append(f"edge {edge}: unknown target node {dst!r}")
        if etype not in EDGE_TYPES:
            errors.append(f"edge {edge}: unknown edge type {etype!r}")
        if etype == "gates":
            gated.add(dst)

    # -- Check 3: every phase is gated
    for node in nodes:
        if node.get("type") == "phase" and node["id"] not in gated:
            errors.append(f"phase {node['id']} has no incoming 'gates' edge")

    # -- Check 5 (warning): top-level entries unreachable from any node path
    indexed_roots = {Path(n["path"]).parts[0] for n in nodes if n.get("path")}
    for entry in sorted(REPO_ROOT.iterdir()):
        if entry.name in UNINDEXED_OK or entry.name in indexed_roots:
            continue
        warnings.append(f"top-level entry not indexed by any node: {entry.name}")

    for message in warnings:
        print(f"WARNING: {message}")
    for message in errors:
        print(f"ERROR: {message}")
    print(f"graph: {len(nodes)} nodes, {len(graph.get('edges', []))} edges — "
          f"{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
