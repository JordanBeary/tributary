"""Build the Phase 4 dashboards as static Plotly HTML (design Section 7.3).

Reads the dbt marts in warehouse/tributary.duckdb, writes per-dashboard
aggregate JSON to analysis/dashboards/data/ (small, identity-free) and one
self-describing HTML page per dashboard to analysis/dashboards/out/. The site
(Phase 7) embeds the HTML as cached static artifacts -- no live compute.

Every panel is tagged with the silo-audit question it answers
(docs/silo_audit.md Section 2, ids A1-A3 auction, C1-C3 CRM, M1-M3 marketing);
the exit checklist in silo_audit.md Section 6 points back at these tags.

Usage: .venv/bin/python analysis/dashboards/build_dashboards.py [--db PATH]
"""
from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path

import duckdb
import plotly.graph_objects as go
from plotly.subplots import make_subplots

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = HERE / "out"

# ---------------------------------------------------------------------------
# Palette: the validated reference instance (dataviz skill, light surface).
# Categorical slots are assigned in fixed order per entity, never cycled.
# ---------------------------------------------------------------------------
CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
CHANNELS = ["organic_search", "paid_search", "direct", "referral", "affiliate", "paid_social", "display"]
CHANNEL_COLOR = dict(zip(CHANNELS, CAT[:7]))
TIER_RAMP = {1: "#0d366b", 2: "#184f95", 3: "#256abf", 4: "#3987e5", 5: "#5598e7", 6: "#86b6ef"}
FICO_RAMP = {"600-659": "#86b6ef", "660-719": "#5598e7", "720-779": "#256abf", "780+": "#0d366b"}
BEFORE, AFTER = CAT[1], CAT[0]          # orange = a silo alone, blue = unified
TREATED, HOLDOUT = CAT[0], CAT[1]
SURFACE, INK, INK2, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1"

LAYOUT = dict(
    template="plotly_white", paper_bgcolor=SURFACE, plot_bgcolor=SURFACE,
    font=dict(family="Inter, Helvetica Neue, Arial, sans-serif", color=INK, size=13),
    margin=dict(l=60, r=30, t=60, b=50), hovermode="closest",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    xaxis=dict(gridcolor=GRID, zerolinecolor=GRID), yaxis=dict(gridcolor=GRID, zerolinecolor=GRID),
)


def fig(**kw) -> go.Figure:
    f = go.Figure()
    f.update_layout(**LAYOUT)
    f.update_layout(**kw)
    return f


def signed_money(x: float) -> str:
    return ("-" if x < 0 else "+") + f"${abs(x):,.2f}"


def money(x: float) -> str:
    return f"${x/1e6:,.1f}M" if abs(x) >= 1e6 else f"${x:,.0f}"


def rows(con, sql: str) -> list[dict]:
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def wilson(p: float, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson interval for a proportion."""
    if n == 0:
        return (0.0, 0.0)
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


# ---------------------------------------------------------------------------
# Page assembly: one HTML page per dashboard, plotly.js loaded once from the
# CDN so committed files stay small; each panel carries its question tag.
# ---------------------------------------------------------------------------
CSS = """
body{margin:0;background:#fcfcfb;color:#0b0b0b;font-family:Inter,'Helvetica Neue',Arial,sans-serif;line-height:1.45}
main{max-width:1180px;margin:0 auto;padding:32px 24px 64px}
h1{font-size:28px;margin:0 0 6px} .sub{color:#52514e;margin:0 0 28px;max-width:820px}
.panel{margin:0 0 40px;padding:20px 20px 8px;border:1px solid #e6e5e1;border-radius:8px;background:#fff}
.panel h2{font-size:18px;margin:0 0 4px} .q{display:inline-block;font-size:12px;color:#52514e;border:1px solid #d9d8d3;border-radius:4px;padding:1px 6px;margin:0 6px 8px 0}
.note{color:#52514e;font-size:13px;margin:4px 0 10px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;margin:0 0 28px}
.tile{border:1px solid #e6e5e1;border-radius:8px;padding:14px 16px;background:#fff}
.tile .v{font-size:26px;font-weight:600} .tile .l{color:#52514e;font-size:13px}
table{border-collapse:collapse;font-size:13px;width:100%} th,td{padding:6px 10px;border-bottom:1px solid #e6e5e1;text-align:left} th{color:#52514e;font-weight:600}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
footer{color:#52514e;font-size:12px;margin-top:32px}
"""


class Page:
    def __init__(self, slug: str, title: str, subtitle: str):
        self.slug, self.title, self.subtitle = slug, title, subtitle
        self.parts: list[str] = []

    def tiles(self, items: list[tuple[str, str]]):
        self.parts.append('<div class="tiles">' + "".join(
            f'<div class="tile"><div class="v">{v}</div><div class="l">{l}</div></div>' for v, l in items) + "</div>")

    def panel(self, title: str, tags: list[str], f: go.Figure, note: str = ""):
        html = f.to_html(full_html=False, include_plotlyjs=False, config={"displaylogo": False, "responsive": True})
        tag_html = "".join(f'<span class="q">{t}</span>' for t in tags)
        self.parts.append(f'<section class="panel"><h2>{title}</h2>{tag_html}'
                          f'{f"<p class=note>{note}</p>" if note else ""}{html}</section>')

    def table(self, title: str, tags: list[str], header: list[str], body: list[list], note: str = ""):
        def cell(v, tag):
            num = isinstance(v, (int, float))
            s = f"{v:,.0f}" if isinstance(v, int) else (f"{v:,.2f}" if isinstance(v, float) else str(v))
            return f'<{tag}{" class=num" if num else ""}>{s}</{tag}>'
        th = "".join(cell(h, "th") for h in header)
        tr = "".join("<tr>" + "".join(cell(v, "td") for v in r) + "</tr>" for r in body)
        tag_html = "".join(f'<span class="q">{t}</span>' for t in tags)
        self.parts.append(f'<section class="panel"><h2>{title}</h2>{tag_html}'
                          f'{f"<p class=note>{note}</p>" if note else ""}<table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></section>')

    def write(self, built_at: str):
        doc = (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
               f'<title>{self.title}</title><style>{CSS}</style>'
               f'<script src="https://cdn.plot.ly/plotly-2.35.2.min.js" charset="utf-8"></script></head><body><main>'
               f'<h1>{self.title}</h1><p class="sub">{self.subtitle}</p>{"".join(self.parts)}'
               f'<footer>Static export built {built_at} from the dbt marts (warehouse/models/marts). '
               f'Question tags refer to docs/silo_audit.md Section 2. All data is synthetic.</footer></main></body></html>')
        (OUT / f"{self.slug}.html").write_text(doc)


def dump(name: str, obj) -> None:
    (DATA / f"{name}.json").write_text(json.dumps(obj, indent=1, default=str))


# ---------------------------------------------------------------------------
# Dashboard 1: before/after silo audit
# ---------------------------------------------------------------------------
def dash_before_after(con, built_at):
    d = {}
    d["counts"] = rows(con, """
        select 'auction lead_uuid' as what, count(*) as n from main_staging.stg_auction__events where event_type='bid_request' and tier=1
        union all select 'CRM lead_id', count(*) from main_staging.stg_crm__leads
        union all select 'marketing contact_id', count(*) from main_staging.stg_marketing__contacts
        union all select 'resolved consumers', count(*) from main_marts.dim_consumer""")
    d["joinable"] = rows(con, """
        select sum((consumer_entity_id is not null)::int)/count(*) as after_share,
               sum((has_marketing_contact)::int)/count(*) as marketing_share from main_marts.fct_auction_events""")
    d["revenue"] = rows(con, """
        select sum(revenue_usd) as total,
               sum(case when has_marketing_contact then revenue_usd else 0 end) as via_contact,
               sum(case when acquisition_channel in ('paid_search','paid_social','display','affiliate') then revenue_usd else 0 end) as via_paid,
               sum(case when last_touch_campaign_id is not null then revenue_usd else 0 end) as via_campaign_30d
        from main_marts.fct_leads""")
    d["roi"] = rows(con, """
        select channel, sum(spend_usd) as spend, sum(contacts_clicked) as clicks, sum(revenue_usd) as revenue,
               sum(leads_sold) as sold, sum(leads_funded) as funded
        from main_marts.fct_channel_month where is_paid group by 1 order by 1""")
    dump("01_before_after", d)

    p = Page("01_silo_audit_before_after", "Silo audit: before and after unification",
             "Each silo looks self-sufficient and is not (design 7.1). The same questions, answered by the silo alone versus through the unification spine.")
    r, j = d["revenue"][0], d["joinable"][0]
    p.tiles([(f"{j['after_share']:.1%}", "auction events consumer-joinable after ER (0% before)"),
             (money(r["via_contact"]), f"auction revenue attributable to a marketing contact ({r['via_contact']/r['total']:.0%}; $0 before)"),
             (f"{d['counts'][3]['n']:,}", "distinct consumers, versus 2.40M lead_uuids and 2.28M CRM rows"),
             (money(r["via_paid"]), "revenue traced to paid acquisition channels")])

    f = fig(title="How many people are in this marketplace? Each silo's count vs. the resolved answer", yaxis_title="rows")
    cols = [BEFORE, BEFORE, BEFORE, AFTER]
    f.add_bar(x=[c["what"] for c in d["counts"]], y=[c["n"] for c in d["counts"]], marker_color=cols,
              text=[f"{c['n']/1e6:.2f}M" for c in d["counts"]], textposition="outside", width=0.55,
              hovertemplate="%{x}: %{y:,}<extra></extra>")
    f.update_layout(showlegend=False)
    p.panel("Distinct consumers: silo counts vs. resolved entities", ["A2", "C3"], f,
            "Orange: what each silo believes on its own. Blue: connected components over the CRM dedupe at t=0.9. The lake overcounts consumers 3.8x; the CRM 3.6x.")

    ch = [x["channel"] for x in d["roi"]]
    f = make_subplots(rows=1, cols=2, subplot_titles=("silo alone: clicks per $1,000 spend (the only 'ROI' it can compute)", "after unification: auction revenue / spend (ROAS)"))
    f.add_bar(x=ch, y=[x["clicks"] / x["spend"] * 1000 for x in d["roi"]], marker_color=BEFORE, text=[f"{x['clicks']/x['spend']*1000:.1f}" for x in d["roi"]], textposition="outside",
              hovertemplate="%{x}: %{y:.1f} clicks per $1,000<extra></extra>", row=1, col=1)
    f.add_bar(x=ch, y=[x["revenue"] / x["spend"] for x in d["roi"]], marker_color=AFTER, text=[f"{x['revenue']/x['spend']:.2f}x" for x in d["roi"]], textposition="outside",
              hovertemplate="%{x}: ROAS %{y:.2f}x<extra></extra>", row=1, col=2)
    f.add_hline(y=1.0, line_dash="dot", line_color=INK2, annotation_text="break-even", annotation_position="top left", row=1, col=2)
    f.update_layout(**LAYOUT); f.update_layout(showlegend=False, title="Paid-channel ROI: click-value vs. revenue through the auction")
    p.panel("Campaign ROI: what marketing can compute alone vs. after unification", ["M1", "A1"], f,
            "Alone, the marketing silo can only price a click, and by clicks paid social looks best and affiliate (no click funnel) looks worthless. Through ER the same spend resolves to sold-lead revenue and affiliate leads.")

    p.table("The nine questions, scored", ["A1", "A2", "A3", "C1", "C2", "C3", "M1", "M2", "M3"],
            ["Question", "Silo alone", "After unification", "Dashboard"],
            [["A1 How much revenue did marketing drive?", "unanswerable", f"{money(r['via_contact'])} of {money(r['total'])} to a contact; {money(r['via_paid'])} to paid channels", "05 attribution"],
             ["A2 How many distinct consumers do we auction?", "2.40M lead_uuids", f"{d['counts'][3]['n']:,} consumers", "04 identity"],
             ["A3 Did the leads we sold actually fund?", "'conversion' = sold", "funded rate by tier and price", "02 funnel"],
             ["C1 What did this lead sell for?", "unanswerable", "clearing price on every CRM lead", "03 auction"],
             ["C2 Which campaign sourced this applicant?", "unanswerable", "acquisition channel + last-touch campaign per lead", "05 attribution"],
             ["C3 How many unique applicants do we have?", "2.28M lead_ids", f"{d['counts'][3]['n']:,} consumers; 112k orphan applications restored", "04 identity"],
             ["M1 What is campaign ROI?", "clicks per dollar", "ROAS and CAC per channel through auction revenue", "05 attribution"],
             ["M2 Did the people we messaged apply or fund?", "unanswerable", "application, sale, funding rates per contact", "02 funnel"],
             ["M3 What did the holdout experiment lift?", "click lift only", "application-rate and revenue lift per contact, by segment", "06 uplift"]])
    p.write(built_at)


# ---------------------------------------------------------------------------
# Dashboard 2: full funnel with drop-off economics
# ---------------------------------------------------------------------------
def dash_funnel(con, built_at):
    d = {}
    d["stages"] = rows(con, """
        with s as (select sum(impressions) as impressions, sum(visits) as visits, sum(new_contacts) as contacts,
                          sum(contacts_applied) as applied from main_marts.fct_channel_month),
             l as (select count(*) as applications, sum(sold::int) as sold, sum(coalesce(funded,false)::int) as funded,
                          sum(revenue_usd) as revenue, sum(case when funded then revenue_usd else 0 end) as funded_revenue from main_marts.fct_leads)
        select * from s, l""")
    d["by_channel"] = rows(con, """
        select channel, sum(contacts) as contacts, sum(contacts_applied) as applied, sum(applications) as applications,
               sum(leads_sold) as sold, sum(leads_funded) as funded, sum(revenue_usd) as revenue, sum(spend_usd) as spend
        from main_marts.fct_channel_month group by 1""")
    d["unsold"] = rows(con, """
        select e.tier, count(distinct e.lead_uuid) as leads_offered, avg(e.floor_price) as floor,
               avg(case when e.event_type = 'bid' then e.bid_price end) as mean_bid,
               sum((e.event_type = 'bid')::int) / count(distinct e.lead_uuid) as bids_per_lead
        from main_marts.fct_auction_events e where not e.sold group by 1 order by 1""")
    d["funded_by_tier"] = rows(con, """
        select sold_tier as tier, count(*) as sold, sum(coalesce(funded,false)::int) as funded, sum(is_orphan::int) as orphans,
               sum(revenue_usd) as revenue, sum(case when funded then revenue_usd else 0 end) as funded_revenue
        from main_marts.fct_leads where sold group by 1 order by 1""")
    d["funded_by_price"] = rows(con, """
        select case when clearing_price < 10 then 'a <$10' when clearing_price < 25 then 'b $10-25' when clearing_price < 50 then 'c $25-50'
                    when clearing_price < 100 then 'd $50-100' when clearing_price < 200 then 'e $100-200' when clearing_price < 300 then 'f $200-300' else 'g $300+' end as band,
               count(*) as sold, sum(coalesce(funded,false)::int) as funded, sum(case when funded is not null then 1 else 0 end) as with_crm
        from main_marts.fct_leads where sold group by 1 order by 1""")
    dump("02_funnel", d)

    s = d["stages"][0]
    p = Page("02_full_funnel", "Full funnel: impressions to funded loans",
             "Top of funnel from the marketing spend ledger, applications and sales from the auction lake, funding from the CRM -- one chain only visible after unification (design 7.3).")
    p.tiles([(f"{s['contacts']/1e3:,.0f}k", "contacts acquired"), (f"{s['applications']/1e6:.2f}M", "applications auctioned"),
             (f"{s['sold']/s['applications']:.1%}", "sell-through"), (f"{s['funded']/s['sold']:.1%}", "of sold leads funded (CRM-reported)"),
             (money(s["revenue"]), "auction revenue"), (money(s["funded_revenue"]), "revenue on leads that funded")])

    stages = [("impressions (media)", s["impressions"]), ("visits", s["visits"]), ("contacts", s["contacts"]),
              ("contacts who applied", s["applied"]), ("applications", s["applications"]), ("sold", s["sold"]), ("funded", s["funded"])]
    f = fig(title="Stage volumes (log scale): where the funnel drops", xaxis_title="count (log)", xaxis_type="log", height=420)
    f.add_bar(y=[n for n, _ in stages][::-1], x=[v for _, v in stages][::-1], orientation="h", marker_color=AFTER,
              text=[f"{v:,.0f}" for _, v in stages][::-1], textposition="outside", hovertemplate="%{y}: %{x:,}<extra></extra>")
    f.update_layout(showlegend=False, margin=dict(l=170, r=90))
    p.panel("The whole funnel on one axis", ["M2", "A3"], f,
            "Applications exceed applicants because people re-apply (mean 3.6 applications per consumer). Impressions and visits exist for media channels only.")

    f = fig(title="Stage-to-stage conversion by acquisition channel", yaxis_title="rate", yaxis_tickformat=".0%", barmode="group")
    steps = [("contact to applicant", "applied", "contacts"), ("application to sold", "sold", "applications"), ("sold to funded", "funded", "sold")]
    for ch in CHANNELS:
        row = next(x for x in d["by_channel"] if x["channel"] == ch)
        f.add_bar(name=ch, x=[n for n, _, _ in steps], y=[row[a] / row[b] for _, a, b in steps], marker_color=CHANNEL_COLOR[ch],
                  hovertemplate=ch + " %{x}: %{y:.1%}<extra></extra>")
    p.panel("Conversion by channel at each stage", ["M2"], f,
            "Intent ranks the channels at the top of the funnel; once a lead is in the auction, the tiers price it the same way regardless of where it came from.")

    f = fig(title="Revenue and drop-off economics by channel", yaxis_title="USD", barmode="group")
    chs = [x["channel"] for x in sorted(d["by_channel"], key=lambda x: -x["revenue"])]
    byc = {x["channel"]: x for x in d["by_channel"]}
    f.add_bar(name="auction revenue", x=chs, y=[byc[c]["revenue"] for c in chs], marker_color=AFTER, hovertemplate="%{x}: $%{y:,.0f}<extra></extra>")
    f.add_bar(name="acquisition spend", x=chs, y=[byc[c]["spend"] for c in chs], marker_color=BEFORE, hovertemplate="%{x}: $%{y:,.0f}<extra></extra>")
    p.panel("Revenue vs. spend by channel", ["A1", "M1"], f)

    f = fig(title="Sold leads: funded rate and revenue by tier", yaxis_title="funded rate", yaxis_tickformat=".1%")
    ft = d["funded_by_tier"]
    f.add_bar(x=[f"tier {x['tier']}" for x in ft], y=[x["funded"] / (x["sold"] - x["orphans"]) for x in ft],
              marker_color=[TIER_RAMP[x["tier"]] for x in ft], text=[f"{x['funded']/(x['sold']-x['orphans']):.1%}<br>{money(x['revenue'])}" for x in ft],
              textposition="outside", hovertemplate="%{x}: funded %{y:.1%}<extra></extra>")
    f.update_layout(showlegend=False)
    p.panel("Did what we sold fund? Funded rate by tier", ["A3"], f,
            "Denominator excludes the 112k migration-orphan leads whose CRM outcome is lost (C17c). The lake alone calls every sale a 'conversion'. Funded declines with tier because funding rides a modest price gradient (C19, calibrated direction with the mean preserved at the CRM's 13.3%).")

    f = fig(title="Funded rate by clearing-price band", yaxis_title="funded rate", yaxis_tickformat=".1%")
    fb = d["funded_by_price"]
    f.add_bar(x=[x["band"][2:] for x in fb], y=[x["funded"] / x["with_crm"] for x in fb], marker_color=AFTER,
              text=[f"{x['sold']:,} sold" for x in fb], textposition="outside", hovertemplate="%{x}: %{y:.1%}<extra></extra>")
    f.update_layout(showlegend=False)
    p.panel("Does price predict funding?", ["A3", "C1"], f, "Modestly, yes (C19): funded odds rise with log clearing price, so higher-priced bands fund more often -- visible only after unification, since price and funding live in different silos.")

    f = fig(title="Unsold leads: mean bid vs. floor at each tier of the cascade (log USD)", yaxis_title="USD (log)", yaxis_type="log", barmode="group")
    u = d["unsold"]
    f.add_bar(name="tier floor", x=[f"tier {x['tier']}" for x in u], y=[x["floor"] for x in u], marker_color="#d9d8d3", hovertemplate="%{x} floor: $%{y:,.2f}<extra></extra>")
    f.add_bar(name="mean bid received (below floor)", x=[f"tier {x['tier']}" for x in u], y=[x["mean_bid"] for x in u], marker_color=BEFORE,
              text=[f"{x['bids_per_lead']:.1f} bids/lead" for x in u], textposition="outside", hovertemplate="%{x} mean bid: $%{y:,.2f}<extra></extra>")
    p.panel("Censored outcomes: the unsold tail", ["A3"], f,
            f"All {u[0]['leads_offered']:,} unsold leads cascaded through every tier without a bid clearing the floor. Their value is never observed -- the censoring the Phase 5 models must handle.")
    p.write(built_at)


# ---------------------------------------------------------------------------
# Dashboard 3: auction economics by credit band, buyer concentration
# ---------------------------------------------------------------------------
def dash_auction(con, built_at):
    d = {}
    d["epl"] = rows(con, """
        select tier, fico_band, count(*) as offered, sum((sold and sold_tier = tier)::int) as sold,
               sum(case when sold_tier = tier then lead_revenue_usd else 0 end) as revenue,
               sum(case when sold_tier = tier then lead_revenue_usd else 0 end) / count(*) as epl,
               avg(case when sold_tier = tier then clearing_price end) as mean_price
        from main_marts.fct_auction_events where event_type = 'bid_request' group by 1, 2 order by 1, 2""")
    d["sell_through"] = rows(con, """
        select tier, count(*) as offered, sum((sold_tier = tier)::int) as sold, avg(floor_price) as floor
        from main_marts.fct_auction_events where event_type = 'bid_request' group by 1 order by 1""")
    d["hhi"] = rows(con, """
        with w as (select sold_tier as tier, winning_buyer_id as buyer, sum(revenue_usd) as rev, count(*) as n
                   from main_marts.fct_leads where sold group by 1, 2),
             t as (select tier, sum(rev) as tot, count(*) as buyers from w group by 1)
        select w.tier, t.buyers, sum(power(w.rev / t.tot, 2)) * 10000 as hhi_revenue,
               max(w.rev / t.tot) as top_share, sum(case when w.rev / t.tot >= 0.1 then 1 else 0 end) as buyers_over_10pct
        from w join t using (tier) group by 1, 2 order by 1""")
    d["buyer_share"] = rows(con, """
        with w as (select sold_tier as tier, winning_buyer_id as buyer, sum(revenue_usd) as rev from main_marts.fct_leads where sold group by 1, 2),
             r as (select *, row_number() over (partition by tier order by rev desc) as rk, sum(rev) over (partition by tier) as tot from w)
        select tier, case when rk <= 5 then buyer else 'other buyers' end as buyer, sum(rev / tot) as share
        from r group by 1, 2 order by 1, 3 desc""")
    d["price_by_fico"] = rows(con, """
        select sold_tier as tier, fico_band, count(*) as n, quantile_cont(clearing_price, [0.1, 0.25, 0.5, 0.75, 0.9]) as q
        from main_marts.fct_leads where sold group by 1, 2 order by 1, 2""")
    d["crm_price"] = rows(con, """
        select fico_band, purpose, count(*) as leads, sum(sold::int) as sold, sum(revenue_usd) as revenue, sum(revenue_usd)/count(*) as epl
        from main_marts.fct_leads where not is_orphan group by 1, 2 order by 1, 2""")
    dump("03_auction", d)

    p = Page("03_auction_economics", "Auction economics by credit profile and buyer",
             "Earnings per lead by tier and FICO band, buyer concentration, and the clearing price every CRM lead never knew it had (design 7.3).")
    hh = d["hhi"]
    st = d["sell_through"]
    p.tiles([(f"{sum(x['sold'] for x in st)/st[0]['offered']:.1%}", "overall sell-through"),
             (f"{hh[0]['hhi_revenue']:,.0f}", "tier-1 revenue HHI (10,000 = monopsony)"),
             (f"{max(x['hhi_revenue'] for x in hh):,.0f}", f"highest HHI (tier {max(hh, key=lambda x: x['hhi_revenue'])['tier']})"),
             (f"{hh[0]['buyers']}", "buyers winning in tier 1")])

    bands = ["600-659", "660-719", "720-779", "780+"]
    tiers = list(range(1, 7))
    z = [[next((x["epl"] for x in d["epl"] if x["tier"] == t and x["fico_band"] == b), None) for t in tiers] for b in bands]
    f = fig(title="Earnings per lead offered, by tier and FICO band (USD)", xaxis_title="tier", yaxis_title="FICO band", height=380)
    f.add_heatmap(z=z, x=[f"tier {t}" for t in tiers], y=bands, colorscale=[[0, "#cde2fb"], [1, "#0d366b"]],
                  text=[[f"${v:,.0f}" if v is not None else "" for v in r] for r in z], texttemplate="%{text}",
                  hovertemplate="%{x}, FICO %{y}: EPL $%{z:,.2f}<extra></extra>", colorbar=dict(title="EPL"))
    p.panel("EPL by tier x credit band", ["C1"], f,
            "EPL = revenue at the tier / leads offered at the tier. The auction silo can segment by the FICO band in its payload; the CRM's richer profile (income, employment) joins through the spine.")

    f = fig(title="Clearing-price spread by tier and FICO band (p10-p90, median marked)", yaxis_title="clearing price (USD, log)", yaxis_type="log", xaxis_title="tier")
    for i, b in enumerate(bands):
        pts = [x for x in d["price_by_fico"] if x["fico_band"] == b]
        f.add_scatter(name=f"FICO {b}", x=[x["tier"] + (i - 1.5) * 0.18 for x in pts], y=[x["q"][2] for x in pts], mode="markers",
                      marker=dict(color=FICO_RAMP[b], size=10, line=dict(color=SURFACE, width=2)),
                      error_y=dict(type="data", symmetric=False, array=[x["q"][4] - x["q"][2] for x in pts], arrayminus=[x["q"][2] - x["q"][0] for x in pts], thickness=1.5, width=0),
                      hovertemplate="FICO " + b + ": median $%{y:,.2f}<extra></extra>")
    f.update_xaxes(tickvals=tiers, ticktext=[f"tier {t}" for t in tiers])
    p.panel("What did this lead sell for?", ["C1"], f, "The CRM records 'sold' with no amount. Joined through the spine, every sold CRM lead gets its hammer price.")

    f = fig(title="Sell-through and average floor by tier", yaxis_title="share of leads offered that sold", yaxis_tickformat=".0%")
    f.add_bar(x=[f"tier {x['tier']}" for x in st], y=[x["sold"] / x["offered"] for x in st], marker_color=[TIER_RAMP[x["tier"]] for x in st],
              text=[f"{x['sold']/x['offered']:.1%}<br>floor ${x['floor']:,.0f}" for x in st], textposition="outside", hovertemplate="%{x}: %{y:.1%}<extra></extra>")
    f.update_layout(showlegend=False)
    p.panel("Sell-through by tier", ["A3"], f)

    f = fig(title="Buyer concentration by tier: revenue-share HHI", yaxis_title="HHI (0-10,000)")
    f.add_bar(x=[f"tier {x['tier']}" for x in hh], y=[x["hhi_revenue"] for x in hh], marker_color=[TIER_RAMP[x["tier"]] for x in hh],
              text=[f"{x['hhi_revenue']:,.0f}<br>{x['buyers']} buyers" for x in hh], textposition="outside", hovertemplate="%{x}: HHI %{y:,.0f}<extra></extra>")
    f.add_hline(y=1500, line_dash="dot", line_color=INK2, annotation_text="1,500: moderately concentrated", annotation_position="bottom right")
    f.add_hline(y=2500, line_dash="dot", line_color=INK2, annotation_text="2,500: highly concentrated", annotation_position="bottom right")
    f.update_layout(showlegend=False)
    p.panel("Buyer concentration (HHI) by tier", ["A1"], f,
            "HHI on each buyer's share of tier revenue; thresholds are the usual antitrust reference bands. Each tier has a fixed panel of five buyers in this world (auction landscape artifact), so every tier sits just above 'highly concentrated' -- the spread within the panel is what varies.")

    f = fig(title="Top-5 buyers' revenue share by tier", yaxis_title="share of tier revenue", yaxis_tickformat=".0%", barmode="stack")
    ranks = {}
    for x in d["buyer_share"]:
        ranks.setdefault(x["tier"], []).append(x)
    for k in range(6):
        f.add_bar(name=f"rank {k+1}" if k < 5 else "other buyers", x=[f"tier {t}" for t in tiers],
                  y=[ranks[t][k]["share"] if k < len(ranks[t]) else 0 for t in tiers],
                  marker_color=[TIER_RAMP[1], TIER_RAMP[2], TIER_RAMP[3], TIER_RAMP[4], TIER_RAMP[5], "#d9d8d3"][k],
                  marker_line=dict(color=SURFACE, width=2), customdata=[ranks[t][k]["buyer"] if k < len(ranks[t]) else "" for t in tiers],
                  hovertemplate="%{x} %{customdata}: %{y:.1%}<extra></extra>")
    p.panel("Who wins each tier", ["A1"], f)

    purposes = sorted({x["purpose"] for x in d["crm_price"]})
    f = fig(title="EPL by FICO band and loan purpose (CRM leads with an auction price)", xaxis_title="loan purpose", yaxis_title="FICO band", height=380)
    z = [[next((x["epl"] for x in d["crm_price"] if x["fico_band"] == b and x["purpose"] == pu), None) for pu in purposes] for b in bands]
    f.add_heatmap(z=z, x=purposes, y=bands, colorscale=[[0, "#cde2fb"], [1, "#0d366b"]], text=[[f"${v:,.0f}" if v else "" for v in r] for r in z],
                  texttemplate="%{text}", hovertemplate="%{x}, FICO %{y}: EPL $%{z:,.2f}<extra></extra>", colorbar=dict(title="EPL"))
    p.panel("Lead value by CRM attributes", ["C1"], f)
    p.write(built_at)


# ---------------------------------------------------------------------------
# Dashboard 4: consumer identity and the duplicate-consumer cost
# ---------------------------------------------------------------------------
def dash_identity(con, built_at):
    d = {}
    d["counts"] = rows(con, """
        select (select count(*) from main_staging.stg_auction__events where event_type='bid_request' and tier=1) as lead_uuids,
               (select count(*) from main_staging.stg_crm__leads) as crm_rows,
               (select count(*) from main_staging.stg_marketing__contacts) as contacts,
               (select count(*) from main_marts.dim_consumer) as consumers,
               (select sum(is_orphan::int) from main_marts.fct_leads) as orphans,
               (select sum(is_repeat_application::int) from main_marts.fct_leads) as repeat_applications""")
    d["apps_dist"] = rows(con, """
        select least(applications, 20) as applications, count(*) as consumers, sum(lifetime_revenue_usd) as revenue
        from main_marts.dim_consumer group by 1 order by 1""")
    d["identities"] = rows(con, """
        select least(crm_identities, 10) as identities, count(*) as consumers from main_marts.dim_consumer group by 1 order by 1""")
    d["dup_cost"] = rows(con, """
        select sold_tier as tier,
               sum(revenue_usd) as revenue,
               sum(case when duplicate_sale_same_buyer_30d then revenue_usd else 0 end) as same_buyer_30d,
               sum(case when duplicate_sale_any_buyer_30d then revenue_usd else 0 end) as any_buyer_30d,
               sum(duplicate_sale_same_buyer_30d::int) as same_buyer_leads,
               sum(duplicate_sale_any_buyer_30d::int) as any_buyer_leads, count(*) as sold
        from main_marts.fct_leads where sold group by 1 order by 1""")
    d["dup_window"] = rows(con, """
        select w as window_days,
               sum(case when days_since_prior_sale_same_buyer <= w then revenue_usd else 0 end) as same_buyer,
               sum(case when days_since_prior_sale_any_buyer <= w then revenue_usd else 0 end) as any_buyer
        from main_marts.fct_leads, (select unnest([1, 7, 14, 30, 60, 90]) as w) where sold group by 1 order by 1""")
    d["repeat_month"] = rows(con, """
        select submitted_month, count(*) as applications, sum(is_repeat_application::int) as repeats,
               sum(is_orphan::int) as orphans
        from main_marts.fct_leads group by 1 order by 1""")
    d["marketing_dups"] = rows(con, """
        select least(marketing_contacts, 6) as contacts_per_consumer, count(*) as consumers from main_marts.dim_consumer group by 1 order by 1""")
    dump("04_identity", d)

    c = d["counts"][0]
    dc = d["dup_cost"]
    same = sum(x["same_buyer_30d"] for x in dc)
    anyb = sum(x["any_buyer_30d"] for x in dc)
    rev = sum(x["revenue"] for x in dc)
    p = Page("04_consumer_identity", "Consumer identity: how many people, and what duplicates cost",
             "Lead and contact counts against resolved consumers, the repeat-application tail (C18), and the dollars buyers paid for consumers they had already bought (design 7.3).")
    p.tiles([(f"{c['consumers']:,}", "resolved consumers"), (f"{c['lead_uuids']/c['consumers']:.1f}x", "lead_uuid overcount"),
             (f"{c['repeat_applications']/c['lead_uuids']:.0%}", "of applications are repeats by a known consumer"),
             (money(same), f"paid by a buyer for a consumer it had bought within 30 days ({same/rev:.1%} of revenue)"),
             (money(anyb), f"revenue on consumers sold to any buyer within the prior 30 days ({anyb/rev:.1%})"),
             (f"{c['orphans']:,}", "orphan applications with no CRM row (migration loss)")])

    f = fig(title="Rows per silo vs. people", yaxis_title="count")
    labels = ["auction lead_uuids", "CRM lead_ids", "marketing contacts", "resolved consumers"]
    vals = [c["lead_uuids"], c["crm_rows"], c["contacts"], c["consumers"]]
    f.add_bar(x=labels, y=vals, marker_color=[BEFORE, BEFORE, BEFORE, AFTER], text=[f"{v:,}" for v in vals], textposition="outside", width=0.55,
              hovertemplate="%{x}: %{y:,}<extra></extra>")
    f.update_layout(showlegend=False)
    p.panel("How many unique applicants do we have?", ["A2", "C3"], f,
            "The CRM both overcounts (drifted identities) and undercounts (the pre-migration gap); the resolved count restores the orphans' applications and collapses the variants.")

    f = fig(title="Applications per consumer (capped at 20+)", xaxis_title="applications in the year", yaxis_title="consumers (log)", yaxis_type="log")
    f.add_bar(x=[str(x["applications"]) + ("+" if x["applications"] == 20 else "") for x in d["apps_dist"]], y=[x["consumers"] for x in d["apps_dist"]],
              marker_color=AFTER, hovertemplate="%{x} applications: %{y:,} consumers<extra></extra>")
    f.update_layout(showlegend=False)
    p.panel("The heavy tail of repeat applicants", ["A2", "C3"], f, "Fitted from industry data (P-010): power law with exponential cutoff, mean 3.6 applications per person as resolved.")

    f = fig(title="CRM identities per consumer (drifted variants, capped at 10+)", xaxis_title="distinct CRM rows per person", yaxis_title="consumers (log)", yaxis_type="log")
    f.add_bar(x=[str(x["identities"]) + ("+" if x["identities"] == 10 else "") for x in d["identities"]], y=[x["consumers"] for x in d["identities"]],
              marker_color=AFTER, hovertemplate="%{x} identities: %{y:,} consumers<extra></extra>")
    f.update_layout(showlegend=False)
    p.panel("Identity drift: one person, many CRM rows", ["C3"], f)

    f = fig(title="Duplicate-consumer cost by tier: revenue on leads sold within 30 days of a prior sale of the same consumer", yaxis_title="USD", barmode="group")
    f.add_bar(name="same buyer bought this consumer within 30 days", x=[f"tier {x['tier']}" for x in dc], y=[x["same_buyer_30d"] for x in dc], marker_color=AFTER,
              text=[f"{x['same_buyer_30d']/x['revenue']:.0%}" for x in dc], textposition="outside", hovertemplate="%{x}: $%{y:,.0f}<extra></extra>")
    f.add_bar(name="any buyer bought this consumer within 30 days", x=[f"tier {x['tier']}" for x in dc], y=[x["any_buyer_30d"] for x in dc], marker_color=BEFORE,
              text=[f"{x['any_buyer_30d']/x['revenue']:.0%}" for x in dc], textposition="outside", hovertemplate="%{x}: $%{y:,.0f}<extra></extra>")
    f.add_bar(name="all tier revenue", x=[f"tier {x['tier']}" for x in dc], y=[x["revenue"] for x in dc], marker_color="#d9d8d3", hovertemplate="%{x}: $%{y:,.0f}<extra></extra>")
    p.panel("What duplicates cost, in dollars", ["A2"], f,
            "Labels are the share of tier revenue. The same-buyer figure is the money a buyer paid twice for one person; the any-buyer figure is the marketplace's re-sale of the same consumer. Neither is visible to the lake, which sees only fresh UUIDs. Buyers already suppress and discount recent repeats (C19), so these are the dollars that slip through that defense.")

    f = fig(title="Duplicate-sale revenue vs. the de-duplication window", xaxis_title="window (days since prior sale)", yaxis_title="USD")
    dw = d["dup_window"]
    f.add_scatter(name="same buyer", x=[x["window_days"] for x in dw], y=[x["same_buyer"] for x in dw], mode="lines+markers", line=dict(color=AFTER, width=2), marker=dict(size=8), hovertemplate="%{x}d: $%{y:,.0f}<extra></extra>")
    f.add_scatter(name="any buyer", x=[x["window_days"] for x in dw], y=[x["any_buyer"] for x in dw], mode="lines+markers", line=dict(color=BEFORE, width=2), marker=dict(size=8), hovertemplate="%{x}d: $%{y:,.0f}<extra></extra>")
    p.panel("Sensitivity to the window", ["A2"], f, "The 30-day window is a stated operating choice; the curve shows how the dollar figure moves with it.")

    rm = d["repeat_month"]
    f = fig(title="Repeat share and orphan share of applications by month", yaxis_title="share of month's applications", yaxis_tickformat=".0%")
    f.add_scatter(name="repeat applications", x=[x["submitted_month"] for x in rm], y=[x["repeats"] / x["applications"] for x in rm], mode="lines+markers", line=dict(color=AFTER, width=2), marker=dict(size=8), hovertemplate="%{x|%b %Y}: %{y:.1%}<extra></extra>")
    f.add_scatter(name="orphans (no CRM row)", x=[x["submitted_month"] for x in rm], y=[x["orphans"] / x["applications"] for x in rm], mode="lines+markers", line=dict(color=BEFORE, width=2), marker=dict(size=8), hovertemplate="%{x|%b %Y}: %{y:.1%}<extra></extra>")
    p.panel("Repeats accumulate; the migration gap is a window, not noise", ["C3"], f,
            "Repeat share climbs through the year as the consumer base ages. The orphan share sits in the first three months only (C17c), and drops to zero afterwards.")
    p.write(built_at)


# ---------------------------------------------------------------------------
# Dashboard 5: marketing attribution and per-channel ROAS
# ---------------------------------------------------------------------------
def dash_attribution(con, built_at):
    d = {}
    d["channel"] = rows(con, """
        select channel, is_paid, sum(spend_usd) as spend, sum(contacts) as contacts, sum(contacts_clicked) as clicks, sum(contacts_applied) as applied,
               sum(applications) as applications, sum(leads_sold) as sold, sum(leads_funded) as funded, sum(revenue_usd) as revenue
        from main_marts.fct_channel_month group by 1, 2""")
    d["monthly"] = rows(con, """
        select month_start, channel, spend_usd, revenue_usd, contacts, roas from main_marts.fct_channel_month order by 1, 2""")
    d["campaign"] = rows(con, """
        select last_touch_campaign_id as campaign, count(*) as leads, sum(sold::int) as sold, sum(revenue_usd) as revenue
        from main_marts.fct_leads where last_touch_campaign_id is not null group by 1 order by 1""")
    d["campaign_funnel"] = rows(con, """
        select campaign_id as campaign, count(*) as sent, sum((opened_at_utc is not null)::int) as opened, sum((clicked_at_utc is not null)::int) as clicked
        from main_staging.stg_marketing__messages group by 1 order by 1""")
    d["attribution_coverage"] = rows(con, """
        select sum(revenue_usd) as total, sum(case when has_marketing_contact then revenue_usd else 0 end) as with_contact,
               sum(case when last_touch_campaign_id is not null then revenue_usd else 0 end) as with_last_touch,
               sum(case when msgs_30d_pre > 0 then revenue_usd else 0 end) as any_msg_30d,
               sum(case when clicks_30d_pre > 0 then revenue_usd else 0 end) as click_30d
        from main_marts.fct_leads""")
    d["segment"] = rows(con, """
        select acquisition_channel as channel, engagement_segment as segment, count(*) as contacts, avg(revenue_usd) as revenue_per_contact
        from main_marts.fct_marketing_contacts group by 1, 2 order by 1, 2""")
    dump("05_attribution", d)

    ch = {x["channel"]: x for x in d["channel"]}
    paid = [c for c in CHANNELS if ch[c]["is_paid"]]
    cov = d["attribution_coverage"][0]
    p = Page("05_marketing_attribution", "Marketing attribution: spend to auction revenue",
             "Spend lives in the marketing silo, revenue in the auction lake; only the spine connects them. Channel ROAS uses acquisition-cohort attribution, campaign revenue uses last-touch within 30 days (design 7.3).")
    tot_spend = sum(ch[c]["spend"] for c in paid)
    tot_rev = sum(ch[c]["revenue"] for c in paid)
    p.tiles([(money(tot_spend), "paid acquisition spend"), (money(tot_rev), "auction revenue from paid-acquired contacts"),
             (f"{tot_rev/tot_spend:.2f}x", "blended paid ROAS"), (f"{cov['with_contact']/cov['total']:.0%}", "of all revenue attributed to a marketing contact"),
             (f"{min(ch[c]['revenue']/ch[c]['spend'] for c in paid):.2f}x to {max(ch[c]['revenue']/ch[c]['spend'] for c in paid):.2f}x", "ROAS spread across paid channels")])

    f = fig(title="ROAS by paid channel (auction revenue / spend)", yaxis_title="ROAS")
    order = sorted(paid, key=lambda c: ch[c]["revenue"] / ch[c]["spend"])
    f.add_bar(x=order, y=[ch[c]["revenue"] / ch[c]["spend"] for c in order], marker_color=[CHANNEL_COLOR[c] for c in order],
              text=[f"{ch[c]['revenue']/ch[c]['spend']:.2f}x<br>CAC ${ch[c]['spend']/ch[c]['contacts']:,.0f}" for c in order], textposition="outside", width=0.5,
              hovertemplate="%{x}: ROAS %{y:.2f}x<extra></extra>")
    f.add_hline(y=1.0, line_dash="dot", line_color=INK2, annotation_text="break-even", annotation_position="top left")
    f.update_layout(showlegend=False)
    p.panel("Which channels pay back?", ["M1", "A1"], f,
            "Display is below break-even; affiliate (CPL) and paid social lead. Recency-penalized repeat leads (C19) weigh hardest on the low-intent channels. The marketing silo alone ranks channels by click volume, which inverts this ordering.")

    f = fig(title="Cost vs. value per contact, by channel", xaxis_title="acquisition cost per contact (USD)", yaxis_title="auction revenue per contact (USD)")
    for c in CHANNELS:
        x = ch[c]
        pos = {"organic_search": "middle right", "direct": "top right", "referral": "bottom right", "affiliate": "bottom right", "paid_social": "top left"}.get(c, "top center")
        f.add_scatter(name=c, x=[x["spend"] / x["contacts"]], y=[x["revenue"] / x["contacts"]], mode="markers+text", text=[c], textposition=pos,
                      marker=dict(color=CHANNEL_COLOR[c], size=12, line=dict(color=SURFACE, width=2)), textfont=dict(color=INK2),
                      hovertemplate=c + ": CAC $%{x:,.0f}, revenue/contact $%{y:,.0f}<extra></extra>")
    mx = max(x["spend"] / x["contacts"] for x in ch.values()) * 1.1
    f.add_scatter(name="break-even", x=[0, mx], y=[0, mx], mode="lines", line=dict(color=INK2, dash="dot", width=1), hoverinfo="skip")
    p.panel("CAC against revenue per contact", ["M1"], f, "Owned channels sit on the y-axis at zero cost; anything above the dotted line earns more than it costs.")

    f = fig(title="Monthly ROAS by paid channel (acquisition cohort)", yaxis_title="ROAS", xaxis_title="acquisition month")
    for c in paid:
        pts = [x for x in d["monthly"] if x["channel"] == c]
        f.add_scatter(name=c, x=[x["month_start"] for x in pts], y=[x["roas"] for x in pts], mode="lines+markers", line=dict(color=CHANNEL_COLOR[c], width=2), marker=dict(size=7),
                      hovertemplate=c + " %{x|%b %Y}: %{y:.2f}x<extra></extra>")
    f.add_hline(y=1.0, line_dash="dot", line_color=INK2)
    p.panel("ROAS over time", ["M1"], f, "Later cohorts have had less time to re-apply, so the right-hand months are right-censored; compare channels within a month, not months within a channel.")

    f = fig(title="Revenue by acquisition channel, paid vs. owned", yaxis_title="USD")
    order = sorted(CHANNELS, key=lambda c: -ch[c]["revenue"])
    f.add_bar(x=order, y=[ch[c]["revenue"] for c in order], marker_color=[CHANNEL_COLOR[c] for c in order], text=[money(ch[c]["revenue"]) for c in order], textposition="outside",
              hovertemplate="%{x}: $%{y:,.0f}<extra></extra>")
    f.update_layout(showlegend=False)
    p.panel("How much revenue did marketing drive, by channel", ["A1", "C2"], f)

    cf = {x["campaign"]: x for x in d["campaign_funnel"]}
    cp = d["campaign"]
    f = make_subplots(rows=1, cols=2, subplot_titles=("what the silo sees: clicks per campaign", "after unification: last-touch revenue per campaign (30-day window)"))
    f.add_bar(x=[x["campaign"] for x in cp], y=[cf[x["campaign"]]["clicked"] for x in cp], marker_color=BEFORE, name="clicks", hovertemplate="%{x}: %{y:,} clicks<extra></extra>", row=1, col=1)
    f.add_bar(x=[x["campaign"] for x in cp], y=[x["revenue"] for x in cp], marker_color=AFTER, name="revenue", hovertemplate="%{x}: $%{y:,.0f}<extra></extra>", row=1, col=2)
    f.update_layout(**LAYOUT); f.update_layout(showlegend=False, title="Monthly campaigns: clicks vs. revenue")
    p.panel("Which campaign sourced this applicant?", ["C2", "M1"], f,
            f"{cov['with_last_touch']/cov['total']:.0%} of revenue has a message within 30 days before the application; {cov['click_30d']/cov['total']:.0%} a click. Campaigns are monthly nurture sends, so last-touch credit is modest by construction.")

    f = fig(title="Revenue per contact by engagement segment and channel", xaxis_title="engagement segment (1 = least engaged)", yaxis_title="USD per contact", barmode="group")
    for c in CHANNELS:
        pts = [x for x in d["segment"] if x["channel"] == c]
        f.add_bar(name=c, x=[f"segment {x['segment']}" for x in pts], y=[x["revenue_per_contact"] for x in pts], marker_color=CHANNEL_COLOR[c], hovertemplate=c + " %{x}: $%{y:,.0f}<extra></extra>")
    p.panel("Value by engagement segment", ["M2"], f)
    p.write(built_at)


# ---------------------------------------------------------------------------
# Dashboard 6: uplift experiment, measured through ER
# ---------------------------------------------------------------------------
def dash_uplift(con, built_at):
    d = {}
    d["arm"] = rows(con, """
        select in_holdout, count(*) as n, avg(became_applicant::int) as app_rate, avg(revenue_usd) as rev_per_contact,
               stddev_samp(revenue_usd) as rev_sd, avg(clicked_any_message::int) as click_rate, avg(leads_funded) as funded_per_contact
        from main_marts.fct_marketing_contacts group by 1 order by 1""")
    d["segment"] = rows(con, """
        select engagement_segment as segment, in_holdout, count(*) as n, avg(became_applicant::int) as app_rate,
               avg(revenue_usd) as rev_per_contact, stddev_samp(revenue_usd) as rev_sd
        from main_marts.fct_marketing_contacts group by 1, 2 order by 1, 2""")
    d["channel"] = rows(con, """
        select acquisition_channel as channel, in_holdout, count(*) as n, avg(became_applicant::int) as app_rate, avg(revenue_usd) as rev_per_contact
        from main_marts.fct_marketing_contacts group by 1, 2 order by 1, 2""")
    injected = json.loads((HERE.parents[1] / "simulation" / "params" / "uplift_params.json").read_text())
    # Injected effect: ATE x per-quintile multipliers renormalized to mean 1
    # (simulation/marketing.py, C6).
    mult = injected["heterogeneity"]["segment_multipliers"]
    mean = sum(mult) / len(mult)
    d["injected"] = {"ate": injected["ate"]["absolute"], "segment_multipliers": [m / mean for m in mult]}
    dump("06_uplift", d)

    a = {x["in_holdout"]: x for x in d["arm"]}
    t, h = a[False], a[True]
    ate = t["app_rate"] - h["app_rate"]
    se = math.sqrt(t["app_rate"] * (1 - t["app_rate"]) / t["n"] + h["app_rate"] * (1 - h["app_rate"]) / h["n"])
    rev_lift = t["rev_per_contact"] - h["rev_per_contact"]
    rev_se = math.sqrt(t["rev_sd"] ** 2 / t["n"] + h["rev_sd"] ** 2 / h["n"])
    inj = d["injected"]["ate"]
    p = Page("06_uplift_experiment", "The nurture holdout: what did it lift?",
             "Intention-to-treat (C15c): treated contacts received nurture messages, holdout contacts none. The marketing silo can only measure click lift; application and revenue lift need the CRM and the auction lake.")
    p.tiles([(f"{t['n']:,} / {h['n']:,}", "treated / holdout contacts"),
             (f"{t['click_rate']:.1%} vs {h['click_rate']:.1%}", "click rate, treated vs holdout: the only lift the silo can see"),
             (f"{ate*100:+.3f}pp", f"application-rate lift (95% CI {(ate-1.96*se)*100:+.3f} to {(ate+1.96*se)*100:+.3f}pp)"),
             (f"{inj*100:+.3f}pp" if inj else "n/a", "injected effect (simulation parameter)"),
             (signed_money(rev_lift), f"revenue lift per contact (95% CI {signed_money(rev_lift-1.96*rev_se)} to {signed_money(rev_lift+1.96*rev_se)})")])
    p.parts.append('<p class="note">The point estimate lands on the injected effect, but the interval spans zero: at 129k holdout contacts the experiment is underpowered for a tenth-of-a-point lift. The honest read is "consistent with the injected effect, not proven by this sample".</p>')

    segs = sorted({x["segment"] for x in d["segment"]})
    f = fig(title="Application rate by arm and engagement segment (95% Wilson intervals)", xaxis_title="engagement segment", yaxis_title="became an applicant", yaxis_tickformat=".1%")
    for hold, name, color, dx in [(False, "treated", TREATED, -0.12), (True, "holdout", HOLDOUT, 0.12)]:
        pts = [x for x in d["segment"] if x["in_holdout"] == hold]
        lo_hi = [wilson(x["app_rate"], x["n"]) for x in pts]
        f.add_scatter(name=name, x=[x["segment"] + dx for x in pts], y=[x["app_rate"] for x in pts], mode="markers",
                      marker=dict(color=color, size=10, line=dict(color=SURFACE, width=2)),
                      error_y=dict(type="data", symmetric=False, array=[hi - x["app_rate"] for x, (lo, hi) in zip(pts, lo_hi)], arrayminus=[x["app_rate"] - lo for x, (lo, hi) in zip(pts, lo_hi)], thickness=1.5, width=0),
                      hovertemplate=name + " segment %{x:.0f}: %{y:.2%}<extra></extra>")
    f.update_xaxes(tickvals=segs)
    p.panel("Did messaged people apply more?", ["M3", "M2"], f,
            "The injected effect is +0.115pp overall, concentrated in the top segment (C6: top-quintile uplift about 4.5x the average). At this sample size the per-segment intervals overlap; the pooled estimate recovers the injected size.")

    f = fig(title="Application-rate lift by segment: measured through ER vs. injected", xaxis_title="engagement segment", yaxis_title="treated minus holdout (pp)")
    lifts, errs, injected_pts = [], [], []
    mult = d["injected"]["segment_multipliers"] or []
    for s in segs:
        tt = next(x for x in d["segment"] if x["segment"] == s and not x["in_holdout"])
        hh = next(x for x in d["segment"] if x["segment"] == s and x["in_holdout"])
        lifts.append((tt["app_rate"] - hh["app_rate"]) * 100)
        errs.append(1.96 * math.sqrt(tt["app_rate"] * (1 - tt["app_rate"]) / tt["n"] + hh["app_rate"] * (1 - hh["app_rate"]) / hh["n"]) * 100)
        injected_pts.append(inj * mult[s - 1] * 100 if inj and len(mult) >= s else None)
    f.add_bar(name="measured lift", x=segs, y=lifts, marker_color=TREATED, error_y=dict(type="data", array=errs, thickness=1.5, width=0), width=0.5, hovertemplate="segment %{x}: %{y:+.3f}pp<extra></extra>")
    if any(v is not None for v in injected_pts):
        f.add_scatter(name="injected effect", x=segs, y=injected_pts, mode="markers", marker=dict(color=HOLDOUT, size=11, symbol="diamond", line=dict(color=SURFACE, width=2)), hovertemplate="segment %{x}: injected %{y:+.3f}pp<extra></extra>")
    f.add_hline(y=0, line_color=INK2, line_width=1)
    f.update_xaxes(tickvals=segs)
    p.panel("Measured vs. injected heterogeneity", ["M3"], f,
            "Diamonds are the simulation's per-segment effect; bars are what a naive analyst recovers after probabilistic linkage (link F1 0.88). Linkage noise attenuates, it does not fabricate.")

    f = fig(title="Revenue per contact by arm and segment", xaxis_title="engagement segment", yaxis_title="auction revenue per contact (USD)", barmode="group")
    for hold, name, color in [(False, "treated", TREATED), (True, "holdout", HOLDOUT)]:
        pts = [x for x in d["segment"] if x["in_holdout"] == hold]
        f.add_bar(name=name, x=[f"segment {x['segment']}" for x in pts], y=[x["rev_per_contact"] for x in pts], marker_color=color,
                  error_y=dict(type="data", array=[1.96 * x["rev_sd"] / math.sqrt(x["n"]) for x in pts], thickness=1.5, width=0), hovertemplate=name + " %{x}: $%{y:,.2f}<extra></extra>")
    p.panel("Revenue lift per contact", ["M3"], f,
            "Revenue per contact is dominated by who the contact is, not whether they were messaged; the experiment moved applications by a tenth of a point, and revenue follows with wide intervals.")

    f = fig(title="Application rate by arm and acquisition channel", yaxis_title="became an applicant", yaxis_tickformat=".0%", barmode="group")
    for hold, name, color in [(False, "treated", TREATED), (True, "holdout", HOLDOUT)]:
        pts = {x["channel"]: x for x in d["channel"] if x["in_holdout"] == hold}
        f.add_bar(name=name, x=CHANNELS, y=[pts[c]["app_rate"] for c in CHANNELS], marker_color=color, hovertemplate=name + " %{x}: %{y:.2%}<extra></extra>")
    p.panel("Balance check: arms look alike within every channel", ["M3"], f, "Randomization held within segments; the channel mix of the arms matches, so channel cannot confound the pooled estimate.")
    p.write(built_at)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(HERE.parents[1] / "warehouse" / "tributary.duckdb"))
    args = ap.parse_args()
    DATA.mkdir(exist_ok=True); OUT.mkdir(exist_ok=True)
    built_at = time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())
    con = duckdb.connect(args.db, read_only=True)
    receipt = {"built_at": built_at, "dashboards": {}}
    for fn in (dash_before_after, dash_funnel, dash_auction, dash_identity, dash_attribution, dash_uplift):
        t0 = time.perf_counter()
        fn(con, built_at)
        receipt["dashboards"][fn.__name__] = {"seconds": round(time.perf_counter() - t0, 2)}
        print(f"{fn.__name__}: {time.perf_counter() - t0:.1f}s")
    # Mart sizes: the cost receipt for the local DuckDB path (no BigQuery scans).
    receipt["marts"] = rows(con, """
        select table_name, estimated_size as rows, column_count
        from duckdb_tables() where schema_name = 'main_marts' order by 1""")
    (DATA / "build_receipt.json").write_text(json.dumps(receipt, indent=1, default=str))


if __name__ == "__main__":
    main()
