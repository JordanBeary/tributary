"""Shared report-page conventions for Phase 5 model evaluations.

Mirrors the Phase 4 dashboard look (analysis/dashboards/build_dashboards.py,
D10c): the validated categorical palette, light surface, recessive grid, and
the panel page template — so the model evaluation pages and the dashboards
read as one system. Pages are static Plotly HTML with plotly.js from the CDN;
they are the cached artifacts the site embeds.
"""
from __future__ import annotations

import json
from pathlib import Path

# Validated palette (same values as the dashboards; light look committed).
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
TIER_RAMP = {1: "#0d366b", 2: "#184f95", 3: "#256abf", 4: "#3987e5", 5: "#5598e7", 6: "#86b6ef"}
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1"
NEUTRAL = "#d9d8d3"  # reference/baseline marks

LAYOUT = dict(
    template="plotly_white", paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
    font=dict(family="Inter,'Helvetica Neue',Arial,sans-serif", color=INK, size=13),
    margin=dict(l=60, r=30, t=60, b=50), height=420,
    xaxis=dict(gridcolor=GRID, zerolinecolor=GRID),
    yaxis=dict(gridcolor=GRID, zerolinecolor=GRID),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
)

CSS = """
body{margin:0;background:#fcfcfb;color:#0b0b0b;font-family:Inter,'Helvetica Neue',Arial,sans-serif;line-height:1.45}
main{max-width:1080px;margin:0 auto;padding:36px 24px}
h1{font-size:28px;margin:0 0 6px} .sub{color:#52514e;margin:0 0 28px;max-width:860px}
.panel{margin:0 0 40px;padding:20px 20px 8px;border:1px solid #e6e5e1;border-radius:8px;background:#fff}
.panel h2{font-size:18px;margin:0 0 4px}
.note{color:#52514e;font-size:13px;margin:4px 0 10px;max-width:860px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin:0 0 28px}
.tile{border:1px solid #e6e5e1;border-radius:8px;padding:14px 16px;background:#fff}
.tile .v{font-size:26px;font-weight:600} .tile .l{color:#52514e;font-size:13px}
table{border-collapse:collapse;font-size:13px;width:100%} th,td{padding:6px 10px;border-bottom:1px solid #e6e5e1;text-align:left} th{color:#52514e;font-weight:600}
footer{color:#52514e;font-size:12px;margin-top:32px}
"""


def apply_layout(fig, **kw):
    fig.update_layout(**LAYOUT)
    if kw:
        fig.update_layout(**kw)
    return fig


def fig_html(fig) -> str:
    return fig.to_html(full_html=False, include_plotlyjs=False,
                       config={"displaylogo": False, "responsive": True})


def tile(value: str, label: str) -> str:
    return f'<div class="tile"><div class="v">{value}</div><div class="l">{label}</div></div>'


def panel(title: str, note: str, body: str) -> str:
    return f'<div class="panel"><h2>{title}</h2><p class="note">{note}</p>{body}</div>'


def write_page(path: Path, title: str, subtitle: str, tiles: list[str],
               panels: list[str], footer: str) -> None:
    html = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<script src="https://cdn.plot.ly/plotly-2.32.0.min.js"></script>
<style>{CSS}</style></head><body><main>
<h1>{title}</h1><p class="sub">{subtitle}</p>
<div class="tiles">{''.join(tiles)}</div>
{''.join(panels)}
<footer>{footer}</footer>
</main></body></html>"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html)


def write_metrics(path: Path, metrics: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metrics, indent=2, default=float) + "\n")
