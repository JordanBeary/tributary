"""Deploy the auction silo: sync partitioned Parquet to the S3 lake.

Usage:
    .venv/bin/python silos/s3_lake/load.py [--dry-run]

Reads AWS_PROFILE and TRIBUTARY_S3_BUCKET from .env. Uses `aws s3 sync`
(idempotent; re-runs upload only changed files) under the least-privilege
`tributary` profile. S3 writes cost ~12x reads (design.md Section 5), so the
layout is uploaded once and never iterated remotely.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

from simulation.config import SimConfig

REPO_ROOT = Path(__file__).resolve().parents[2]


def find_aws_cli() -> str:
    # Non-interactive shells on this machine lack ~/.local/bin on PATH
    # (CLAUDE.md machine quirks), so fall back to the known install location.
    return shutil.which("aws") or str(Path.home() / ".local/bin/aws")


def assert_no_private_data(source: Path, private_dir: Path) -> None:
    # The crosswalk never enters any silo (design.md Section 2.4). Refuse to
    # run if the upload source sits inside the private dir or contains any
    # crosswalk artifact.
    if private_dir.resolve() in source.resolve().parents or source.resolve() == private_dir.resolve():
        sys.exit(f"refusing to upload: {source} is inside the private dir {private_dir}")
    leaked = list(source.rglob("crosswalk*"))
    if leaked:
        sys.exit(f"refusing to upload: crosswalk artifact(s) found under source: {leaked}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="pass --dryrun to aws s3 sync")
    args = parser.parse_args()

    load_dotenv(REPO_ROOT / ".env")
    bucket = os.environ["TRIBUTARY_S3_BUCKET"]
    profile = os.environ.get("AWS_PROFILE", "tributary")

    cfg = SimConfig()
    source = REPO_ROOT / cfg.out_dir / "auction"
    if not source.is_dir():
        sys.exit(f"auction output not found at {source}; run the simulation first")
    assert_no_private_data(source, REPO_ROOT / cfg.private_dir)

    # Sync the Hive-partitioned tree as-is: event_date=*/ prefixes become the
    # partition scheme DuckDB/Athena-style readers expect.
    cmd = [
        find_aws_cli(), "--profile", profile,
        "s3", "sync", str(source), f"s3://{bucket}/auction",
        "--exclude", "*.DS_Store",
        # Parquet basenames change every regeneration; --delete clears the
        # previous run's files so the lake always mirrors the local tree.
        "--delete",
    ]
    if args.dry_run:
        cmd.append("--dryrun")
    print("+", " ".join(cmd))
    subprocess.run(cmd, check=True)

    # Post-upload verification: object count and total bytes vs. local.
    local_files = [p for p in source.rglob("*") if p.is_file() and p.name != ".DS_Store"]
    local_bytes = sum(p.stat().st_size for p in local_files)
    print(f"local:  {len(local_files)} files, {local_bytes:,} bytes")
    summary = subprocess.run(
        [find_aws_cli(), "--profile", profile, "s3", "ls",
         f"s3://{bucket}/auction/", "--recursive", "--summarize"],
        check=True, capture_output=True, text=True,
    ).stdout.splitlines()[-2:]
    print("remote:", " / ".join(line.strip() for line in summary))


if __name__ == "__main__":
    main()
