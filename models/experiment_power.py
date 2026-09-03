"""Experiment read-out arithmetic for the nurture holdout (design M3; dashboard 06).

Recomputes, from committed artifacts, every number docs/experiment_readout.md
cites: the pooled treatment effect and its interval, the sample the experiment
would need to detect the injected pooled effect, the minimum detectable effect
at the sample it has, the sample a segment-5 follow-up needs, and the value of
a segment-5-only send policy. Nothing here is typed in by hand.

Inputs: analysis/dashboards/data/06_uplift.json (arm and segment aggregates),
simulation/params/uplift_params.json (injected effect and heterogeneity),
analysis/dashboards/data/derived_figures.json (applications per applicant,
revenue per application), and the warehouse mart fct_marketing_contacts for
messages sent per segment (the only input not already in a JSON aggregate).

Power arithmetic: two-proportion z-test, two-sided alpha 0.05. For control
size n_c and treated size r * n_c, the total sample that detects an absolute
difference d with power 1 - beta is
    n_c = (z_{1-alpha/2} + z_{1-beta})^2 * (p_t(1-p_t)/r + p_c(1-p_c)) / d^2,
    N   = n_c * (1 + r).

Output: models/out/experiment_power.json. Usage: .venv/bin/python models/experiment_power.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from scipy.stats import norm

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from models import common, report
from models.common import OUT_DIR, ROOT

DATA = ROOT / "analysis" / "dashboards" / "data"
ALPHA = 0.05


def n_total(p_c: float, d: float, ratio: float, power: float) -> float:
    """Total contacts for a two-proportion z-test at treated:control = ratio:1."""
    p_t = p_c + d
    z = norm.ppf(1 - ALPHA / 2) + norm.ppf(power)
    n_c = z ** 2 * (p_t * (1 - p_t) / ratio + p_c * (1 - p_c)) / d ** 2
    return float(n_c * (1 + ratio))


def mde(p_c: float, n_c: float, ratio: float, power: float) -> float:
    """Minimum detectable absolute difference at the sample in hand (p_t ~ p_c)."""
    z = norm.ppf(1 - ALPHA / 2) + norm.ppf(power)
    return float(z * np.sqrt(p_c * (1 - p_c) * (1 / ratio + 1) / n_c))


def main() -> None:
    up = json.loads((DATA / "06_uplift.json").read_text())
    params = json.loads((ROOT / "simulation" / "params" / "uplift_params.json").read_text())
    derived = json.loads((DATA / "derived_figures.json").read_text())

    # ── Pooled read, recomputed from the arm aggregates ──
    arms = {x["in_holdout"]: x for x in up["arm"]}
    t, c = arms[False], arms[True]
    ate = t["app_rate"] - c["app_rate"]
    se = np.sqrt(t["app_rate"] * (1 - t["app_rate"]) / t["n"] + c["app_rate"] * (1 - c["app_rate"]) / c["n"])
    rev_lift = t["rev_per_contact"] - c["rev_per_contact"]
    rev_se = np.sqrt(t["rev_sd"] ** 2 / t["n"] + c["rev_sd"] ** 2 / c["n"])
    ratio = t["n"] / c["n"]
    injected = params["ate"]["absolute"]
    mult = np.asarray(params["heterogeneity"]["segment_multipliers"], dtype=float)
    seg_injected = injected * mult / mult.mean()  # per-segment injected uplift (C6 normalization)

    # ── Segment 5: the concentrated effect ──
    segs = {(x["segment"], x["in_holdout"]): x for x in up["segment"]}
    top = int(np.argmax(seg_injected)) + 1
    s_t, s_c = segs[(top, False)], segs[(top, True)]
    seg_lift = s_t["app_rate"] - s_c["app_rate"]
    seg_se = np.sqrt(s_t["app_rate"] * (1 - s_t["app_rate"]) / s_t["n"] + s_c["app_rate"] * (1 - s_c["app_rate"]) / s_c["n"])
    n_top = s_t["n"] + s_c["n"]

    # ── Messages by segment (treated arm): the cost side of a send policy ──
    with common.connect() as con:
        msgs = con.sql("""
            select engagement_segment as segment, count(*) as contacts, sum(messages_sent) as messages
            from main_marts.fct_marketing_contacts where treated group by 1 order by 1
        """).df()
    msgs_by_seg = {int(r.segment): dict(contacts=int(r.contacts), messages=int(r.messages)) for r in msgs.itertuples()}
    msgs_other = sum(v["messages"] for k, v in msgs_by_seg.items() if k != top)
    contacts_other = sum(v["contacts"] for k, v in msgs_by_seg.items() if k != top)

    # ── Value of a segment-5-only policy at the injected effect ──
    apps_per_applicant = derived["funnel"]["applications_per_applicant"]
    rev_per_app = derived["funnel"]["revenue_per_application"]
    incr_applicants = n_top * seg_injected[top - 1]
    policy_value = incr_applicants * apps_per_applicant * rev_per_app
    # What messaging segments 1-4 buys at their injected uplift (near zero)
    incr_other = sum(segs[(s, False)]["n"] + segs[(s, True)]["n"] for s in range(1, 6) if s != top) * 0.0
    other_value = sum((segs[(s, False)]["n"] + segs[(s, True)]["n"]) * seg_injected[s - 1]
                      for s in range(1, 6) if s != top) * apps_per_applicant * rev_per_app

    out = dict(
        pooled=dict(n_treated=t["n"], n_control=c["n"], allocation_ratio=ratio,
                    app_rate_treated=t["app_rate"], app_rate_control=c["app_rate"],
                    ate=ate, se=se, ci95=[ate - 1.96 * se, ate + 1.96 * se], injected=injected,
                    revenue_lift_per_contact=rev_lift, revenue_ci95=[rev_lift - 1.96 * rev_se, rev_lift + 1.96 * rev_se]),
        sample_size=dict(
            for_injected_pooled_effect_85_15_power80=n_total(c["app_rate"], injected, ratio, 0.80),
            for_injected_pooled_effect_85_15_power90=n_total(c["app_rate"], injected, ratio, 0.90),
            for_injected_pooled_effect_50_50_power80=n_total(c["app_rate"], injected, 1.0, 0.80),
            current_total=t["n"] + c["n"],
            mde_at_current_sample_power80=mde(c["app_rate"], c["n"], ratio, 0.80),
        ),
        top_segment=dict(
            segment=top, n=n_top, injected_uplift=float(seg_injected[top - 1]),
            empirical_lift=seg_lift, empirical_se=seg_se, ci95=[seg_lift - 1.96 * seg_se, seg_lift + 1.96 * seg_se],
            n_needed_85_15_power80=n_total(s_c["app_rate"], float(seg_injected[top - 1]), ratio, 0.80),
            n_needed_50_50_power80=n_total(s_c["app_rate"], float(seg_injected[top - 1]), 1.0, 0.80),
            n_needed_50_50_power80_at_half_effect=n_total(s_c["app_rate"], float(seg_injected[top - 1]) / 2, 1.0, 0.80),
            # Fresh contacts accrue at the year's observed rate; a follow-up test
            # needs new assignments, so express the sample as months of acquisition
            contacts_per_month=n_top / 12.0,
            months_to_accrue_85_15=n_total(s_c["app_rate"], float(seg_injected[top - 1]), ratio, 0.80) / (n_top / 12.0),
            months_to_accrue_50_50=n_total(s_c["app_rate"], float(seg_injected[top - 1]), 1.0, 0.80) / (n_top / 12.0),
        ),
        send_policy=dict(
            messages_by_segment_treated=msgs_by_seg,
            messages_avoided_if_only_top_segment=msgs_other, contacts_no_longer_messaged=contacts_other,
            incremental_applicants_top_segment=incr_applicants,
            applications_per_applicant=apps_per_applicant, revenue_per_application=rev_per_app,
            annual_revenue_value_top_segment_only=policy_value,
            annual_revenue_value_other_segments=other_value,
            note="per-message send cost is not in any silo; supply it to price the avoided messages",
        ),
        injected_by_segment={str(i + 1): float(v) for i, v in enumerate(seg_injected)},
    )
    report.write_metrics(OUT_DIR / "experiment_power.json", out)
    p, s, k, v = out["pooled"], out["sample_size"], out["top_segment"], out["send_policy"]
    print(f"ATE {p['ate']*100:+.3f}pp (95% CI {p['ci95'][0]*100:+.3f}..{p['ci95'][1]*100:+.3f}); injected {p['injected']*100:+.3f}pp")
    print(f"N for injected pooled effect, 85/15, 80% power: {s['for_injected_pooled_effect_85_15_power80']:,.0f} "
          f"(have {s['current_total']:,}; x{s['for_injected_pooled_effect_85_15_power80']/s['current_total']:.1f}); "
          f"50/50: {s['for_injected_pooled_effect_50_50_power80']:,.0f}; MDE now {s['mde_at_current_sample_power80']*100:.3f}pp")
    print(f"segment {k['segment']}: n {k['n']:,}, injected {k['injected_uplift']*100:+.3f}pp, empirical {k['empirical_lift']*100:+.3f}pp "
          f"(CI {k['ci95'][0]*100:+.3f}..{k['ci95'][1]*100:+.3f}); N needed 85/15 {k['n_needed_85_15_power80']:,.0f}, 50/50 {k['n_needed_50_50_power80']:,.0f}")
    print(f"policy: +{v['incremental_applicants_top_segment']:,.0f} applicants/yr, ${v['annual_revenue_value_top_segment_only']:,.0f} revenue; "
          f"{v['messages_avoided_if_only_top_segment']:,} messages avoided across {v['contacts_no_longer_messaged']:,} contacts; "
          f"other segments' value ${v['annual_revenue_value_other_segments']:,.0f}")


if __name__ == "__main__":
    main()
