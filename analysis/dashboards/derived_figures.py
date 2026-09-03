"""Recompute every derived figure the case-study pages cite from the committed
dashboard aggregates, so no page number rests on hand arithmetic.

Reads analysis/dashboards/data/0[1-6]_*.json (identity-free aggregates written
by build_dashboards.py) and models/out/m3_metrics.json; writes
analysis/dashboards/data/derived_figures.json. Every value here is a ratio,
share, or sum of committed aggregates -- nothing is re-queried from the
warehouse. Pages cite this file; the 2026-09-01 reframe rule is that a
figure appears on a page only if a script emitted it.

Usage: .venv/bin/python analysis/dashboards/derived_figures.py
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
ROOT = HERE.parents[1]


def load(name: str) -> dict:
    return json.loads((DATA / f"{name}.json").read_text())


def main() -> None:
    funnel = load("02_funnel")
    auction = load("03_auction")
    identity = load("04_identity")
    attribution = load("05_attribution")
    m3 = json.loads((ROOT / "models" / "out" / "m3_metrics.json").read_text())

    out: dict = {"source": "analysis/dashboards/data/*.json + models/out/m3_metrics.json",
                 "note": "derived by analysis/dashboards/derived_figures.py; shares in [0,1], money in USD"}

    # ── Funnel and revenue per application ──
    s = funnel["stages"][0]
    out["funnel"] = {
        "applications": s["applications"], "sold": s["sold"], "funded": s["funded"],
        "revenue_usd": s["revenue"], "applicants": s["applied"],
        "sell_through": s["sold"] / s["applications"],
        "funded_per_sold_all": s["funded"] / s["sold"],
        "revenue_per_application": s["revenue"] / s["applications"],
        "applications_per_applicant": s["applications"] / s["applied"],
        "funded_revenue_share": s["funded_revenue"] / s["revenue"],
    }
    # Funded rate excluding sold migration orphans (CRM outcome unobservable)
    ft = funnel["funded_by_tier"]
    sold_with_crm = sum(x["sold"] - x["orphans"] for x in ft)
    out["funnel"]["sold_orphans"] = sum(x["orphans"] for x in ft)
    out["funnel"]["funded_per_sold_ex_orphan"] = sum(x["funded"] for x in ft) / sold_with_crm
    out["funnel"]["funded_by_tier_ex_orphan"] = {
        x["tier"]: x["funded"] / (x["sold"] - x["orphans"]) for x in ft}
    out["funnel"]["funded_by_price_band"] = {
        x["band"][2:]: x["funded"] / x["with_crm"] for x in funnel["funded_by_price"]}

    # ── Tier economics: revenue share, mean price, EPL per lead offered ──
    rev_by_tier = {x["tier"]: x["revenue"] for x in ft}
    out["tiers"] = {}
    for x in auction["sell_through"]:
        t = x["tier"]
        out["tiers"][t] = {
            "offered": x["offered"], "sold": x["sold"], "floor": x["floor"],
            "sell_through": x["sold"] / x["offered"],
            "mean_clearing_price": rev_by_tier[t] / x["sold"],
            "epl_per_lead_offered": rev_by_tier[t] / x["offered"],
            "revenue_share": rev_by_tier[t] / s["revenue"],
        }
    # Tier-1 price quantiles by FICO band: the floor-pinning fact
    out["tier1_price_quantiles_by_fico"] = {
        x["fico_band"]: dict(zip(["p10", "p25", "p50", "p75", "p90"], x["q"]))
        for x in auction["price_by_fico"] if x["tier"] == 1}
    out["tier1_epl_by_fico"] = {x["fico_band"]: x["epl"] for x in auction["epl"] if x["tier"] == 1}
    hh = auction["hhi"]
    out["hhi"] = {"min": min(x["hhi_revenue"] for x in hh), "max": max(x["hhi_revenue"] for x in hh),
                  "buyers_per_tier": hh[0]["buyers"], "top_share_tier1": hh[0]["top_share"]}

    # ── Identity: overcount, repeat share, concentration, duplicate spend ──
    c = identity["counts"][0]
    apps = identity["apps_dist"]
    rev_total = sum(x["revenue"] for x in apps)
    out["identity"] = {
        "consumers": c["consumers"], "lead_uuids": c["lead_uuids"], "crm_rows": c["crm_rows"],
        "overcount_lead_uuid": c["lead_uuids"] / c["consumers"],
        "overcount_crm": c["crm_rows"] / c["consumers"],
        "repeat_share": c["repeat_applications"] / c["lead_uuids"],
        "orphan_applications": c["orphans"],
        "one_application_consumer_share": apps[0]["consumers"] / c["consumers"],
        "one_application_revenue_share": apps[0]["revenue"] / rev_total,
        "five_plus_consumer_share": sum(x["consumers"] for x in apps if x["applications"] >= 5) / c["consumers"],
        "five_plus_revenue_share": sum(x["revenue"] for x in apps if x["applications"] >= 5) / rev_total,
        "twenty_plus_consumers": apps[-1]["consumers"],
        "twenty_plus_revenue_share": apps[-1]["revenue"] / rev_total,
        "single_identity_consumer_share": identity["identities"][0]["consumers"] / c["consumers"],
        "ten_plus_identity_consumers": identity["identities"][-1]["consumers"],
    }
    dc = identity["dup_cost"]
    rev = sum(x["revenue"] for x in dc)
    out["duplicate_spend"] = {
        "same_buyer_30d_usd": sum(x["same_buyer_30d"] for x in dc),
        "same_buyer_30d_share": sum(x["same_buyer_30d"] for x in dc) / rev,
        "same_buyer_30d_leads": sum(x["same_buyer_leads"] for x in dc),
        "any_buyer_30d_usd": sum(x["any_buyer_30d"] for x in dc),
        "any_buyer_30d_share": sum(x["any_buyer_30d"] for x in dc) / rev,
        "any_buyer_30d_leads": sum(x["any_buyer_leads"] for x in dc),
        "tier1_same_buyer_share": dc[0]["same_buyer_30d"] / dc[0]["revenue"],
        "by_window_days": {x["window_days"]: {"same_buyer_usd": x["same_buyer"], "any_buyer_usd": x["any_buyer"]}
                           for x in identity["dup_window"]},
    }
    rm = identity["repeat_month"]
    out["identity"]["repeat_share_first_month"] = rm[0]["repeats"] / rm[0]["applications"]
    out["identity"]["repeat_share_month_12"] = rm[11]["repeats"] / rm[11]["applications"]

    # ── Channel economics: ROAS, CAC, cost per sold lead, revenue per contact ──
    ch = {x["channel"]: x for x in attribution["channel"]}
    out["channels"] = {}
    for name, x in ch.items():
        out["channels"][name] = {
            "is_paid": x["is_paid"], "spend_usd": x["spend"], "revenue_usd": x["revenue"],
            "contacts": x["contacts"], "sold": x["sold"],
            "roas": (x["revenue"] / x["spend"]) if x["spend"] else None,
            "net_usd": x["revenue"] - x["spend"],
            "cac_per_contact": x["spend"] / x["contacts"],
            "cost_per_sold_lead": (x["spend"] / x["sold"]) if x["sold"] else None,
            "revenue_per_contact": x["revenue"] / x["contacts"],
            "contact_to_applicant": x["applied"] / x["contacts"],
            "application_to_sold": x["sold"] / x["applications"],
            "sold_to_funded": x["funded"] / x["sold"],
        }
    paid = [x for x in ch.values() if x["is_paid"]]
    out["paid_totals"] = {
        "spend_usd": sum(x["spend"] for x in paid), "revenue_usd": sum(x["revenue"] for x in paid),
        "blended_roas": sum(x["revenue"] for x in paid) / sum(x["spend"] for x in paid),
    }
    cov = attribution["attribution_coverage"][0]
    out["attribution_coverage"] = {
        "with_contact_share": cov["with_contact"] / cov["total"],
        "last_touch_30d_share": cov["with_last_touch"] / cov["total"],
        "click_30d_share": cov["click_30d"] / cov["total"],
    }
    # Monthly cohort ROAS: first and last cohort per paid channel (right-censoring)
    out["cohort_roas_first_last"] = {}
    for name in [x["channel"] for x in paid]:
        pts = [m["roas"] for m in attribution["monthly"] if m["channel"] == name and m["roas"]]
        out["cohort_roas_first_last"][name] = {"first_cohort": pts[0], "last_cohort": pts[-1],
                                               "min": min(pts), "max": max(pts)}

    # ── Floor policy economics from model 3 ──
    rp = m3["revenue_per_lead"]
    out["floor_policy"] = {
        "revenue_per_lead_deployed": rp["deployed"], "revenue_per_lead_recommended": rp["recommended"],
        "delta_per_lead_usd": rp["recommended"] - rp["deployed"],
        "annual_delta_usd_at_logged_volume": (rp["recommended"] - rp["deployed"]) * m3["n_leads"],
        "n_leads": m3["n_leads"],
        "lift_mean": m3["expected_lift"]["mean"], "lift_ci95": m3["expected_lift"]["ci95"],
        "sell_through_deployed": m3["sell_through"]["deployed"],
        "sell_through_recommended": m3["sell_through"]["recommended"],
        "global_sweep_at": {str(x["multiplier"]): x["revenue_per_lead"] for x in m3["global_sweep"]
                            if x["multiplier"] in (0.5, 0.8, 1.0, 1.2, 1.5, 2.0)},
        "recommended_floors": m3["recommended_floors"], "deployed_floors": m3["deployed_floors"],
        "recommended_multipliers": m3["recommended_multipliers"],
    }

    (DATA / "derived_figures.json").write_text(json.dumps(out, indent=1, default=float) + "\n")
    print(f"wrote {DATA / 'derived_figures.json'}")
    f, i, d, p = out["funnel"], out["identity"], out["duplicate_spend"], out["paid_totals"]
    print(f"sell-through {f['sell_through']:.3f}; funded/sold {f['funded_per_sold_all']:.3f} "
          f"(ex-orphan {f['funded_per_sold_ex_orphan']:.3f}); rev/app ${f['revenue_per_application']:.2f}")
    print(f"tier 1 revenue share {out['tiers'][1]['revenue_share']:.3f}, mean ${out['tiers'][1]['mean_clearing_price']:.2f}")
    print(f"consumers {i['consumers']:,}; overcount {i['overcount_lead_uuid']:.1f}x; repeat {i['repeat_share']:.3f}; "
          f"5+ apps: {i['five_plus_consumer_share']:.3f} of consumers, {i['five_plus_revenue_share']:.3f} of revenue")
    print(f"dup same-buyer ${d['same_buyer_30d_usd']/1e6:.2f}M ({d['same_buyer_30d_share']:.3f}); "
          f"any-buyer ${d['any_buyer_30d_usd']/1e6:.2f}M ({d['any_buyer_30d_share']:.3f})")
    print(f"paid ROAS {p['blended_roas']:.2f}x; display net ${out['channels']['display']['net_usd']/1e6:.2f}M")
    print(f"floor policy: +${out['floor_policy']['delta_per_lead_usd']:.2f}/lead, "
          f"${out['floor_policy']['annual_delta_usd_at_logged_volume']/1e6:.2f}M at logged volume")


if __name__ == "__main__":
    main()
