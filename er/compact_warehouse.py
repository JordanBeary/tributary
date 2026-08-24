"""Drop Splink scratch tables and compact the warehouse file.

The Splink linker materializes large intermediate tables (``__splink__*``) and
the er scripts stage input tables (``er_in_*``) in ``main`` of
``warehouse/tributary.duckdb``; none are needed once ``main_er`` is written,
but DuckDB does not shrink files in place, so after dropping them the file is
rebuilt by copying every surviving schema into a fresh database and swapping
it over the old one. Run after the ER pipeline (any time; idempotent).

Usage: .venv/bin/python er/compact_warehouse.py
"""
from __future__ import annotations

from pathlib import Path

import duckdb

DB = Path(__file__).resolve().parents[1] / "warehouse" / "tributary.duckdb"
TMP = DB.with_suffix(".compact.duckdb")


def main() -> None:
    before = DB.stat().st_size
    con = duckdb.connect(str(DB))
    scratch = con.execute("""
        select table_name, table_type from information_schema.tables
        where table_schema = 'main'
          and (table_name like '__splink__%' or table_name like 'er_in_%')
    """).fetchall()
    for t, kind in scratch:
        obj = "view" if kind == "VIEW" else "table"
        con.execute(f'drop {obj} if exists main."{t}"')
    # Rebuild compactly: copy the whole database into a fresh file, then swap
    TMP.unlink(missing_ok=True)
    con.execute(f"attach '{TMP}' as compacted")
    con.execute("copy from database tributary to compacted")
    con.close()
    TMP.replace(DB)
    after = DB.stat().st_size
    print(f"dropped {len(scratch)} scratch tables; "
          f"{before / 1e9:.2f} GB -> {after / 1e9:.2f} GB")


if __name__ == "__main__":
    main()
