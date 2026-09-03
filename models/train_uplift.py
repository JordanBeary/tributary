"""Model 4 — marketing uplift: who should we message at all?

T-learner (design Section 8, model 4) on the randomized nurture experiment at
contact grain (fct_marketing_contacts): one classifier per arm on
became_applicant, uplift = P(apply | treated) - P(apply | control). The base
learner is logistic regression on one-hot covariates -- the estimator the
calibration artifact itself used to measure heterogeneity, and the
power-appropriate choice at this effect size (see the inline note).

The experiment is underpowered for the pooled ATE at project scale (D10), so
per the Phase 5 handoff the model is evaluated on *ranking*: Qini/uplift
curves and recovery of the injected per-segment effect
(simulation/params/uplift_params.json: ate x mean-normalized segment
multipliers -- the top segment carries ~4.5x the average, the other four are
near zero). Features are pre-treatment only; the message funnel columns are
post-treatment and excluded.

Evaluation: 2-fold cross-fitting, folds stratified by arm (seeded) -- every
contact is scored out-of-fold, so the whole experiment feeds both training
and evaluation. Treatment is randomized at acquisition and the outcome spans
the whole year, so a temporal split has no leakage to prevent, and a plain
train/test split would halve the already-small control arm for no benefit
(D11).

Outputs: models/out/m4_metrics.json, models/out/m4_uplift.html, boosters
under models/out/boosters/. Usage: .venv/bin/python models/train_uplift.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from models import common, report
from models.common import OUT_DIR, ROOT, SEED

# Covariates = the nurture program's action space: the ESP targets sends by
# engagement segment and acquisition channel, so those are the dimensions a
# targeting policy can act on. Both are balanced across arms (treated share
# 85.0% within every segment and channel). Deliberately excluded: state (not
# actionable for message targeting, and its ~50 small control-arm cells feed
# pure arm-difference noise into the uplift at this effect size) and
# acquisition month (the inverse construction correlates arm assignment with
# converter/prospect composition over time -- control mean month 20.2 vs
# treated 19.1 -- so per-arm models extrapolate across the shift and inherit
# a ~-3pp level bias).
FEATURES = ["acquisition_channel", "engagement_segment"]
CATEGORICAL = ["acquisition_channel", "engagement_segment", "state"]


def load_contacts() -> pd.DataFrame:
    with common.connect() as con:
        df = con.sql("""
            select contact_id, treated, became_applicant,
                   acquisition_channel, engagement_segment, state,
                   datediff('month', date '2024-01-01', acquired_at_utc) as acquired_month_idx
            from main_marts.fct_marketing_contacts
        """).df()
    for c in CATEGORICAL:
        df[c] = df[c].astype("category")
    return df


def injected_truth() -> tuple[float, np.ndarray]:
    p = json.loads((ROOT / "simulation" / "params" / "uplift_params.json").read_text())
    mult = np.asarray(p["heterogeneity"]["segment_multipliers"], dtype=float)
    return float(p["ate"]["absolute"]), mult / mult.mean()


def uplift_curve(u: np.ndarray, y: np.ndarray, t: np.ndarray, grid: int = 100):
    """Absolute-gain uplift curve: incremental conversions per contact when the
    top-p fraction by predicted uplift is targeted, using the randomized arms
    inside the targeted slice. Returns (fractions, gains, auuc-above-random).

    Ties are broken by a seeded shuffle: scores here take few distinct values
    (segment x channel cells), and row order in the mart correlates with
    converter status by construction, so stable tie-breaking would fabricate
    uplift inside tied blocks."""
    perm = np.random.default_rng(SEED).permutation(len(u))
    order = perm[np.argsort(-u[perm], kind="stable")]
    y_o, t_o = y[order], t[order]
    cum_t, cum_ty = np.cumsum(t_o), np.cumsum(y_o * t_o)
    cum_c, cum_cy = np.cumsum(1 - t_o), np.cumsum(y_o * (1 - t_o))
    idx = np.unique((np.arange(1, grid + 1) / grid * len(u)).astype(int) - 1)
    with np.errstate(invalid="ignore", divide="ignore"):
        gain = (cum_ty[idx] / np.maximum(cum_t[idx], 1)
                - cum_cy[idx] / np.maximum(cum_c[idx], 1)) * (idx + 1) / len(u)
    frac = (idx + 1) / len(u)
    ate = gain[-1]  # endpoint equals the empirical ATE by construction
    auuc = float(np.trapezoid(gain, frac) - 0.5 * ate)  # area above the random line
    return frac, gain, auuc


def main() -> None:
    df = load_contacts()
    ate_true, seg_mult = injected_truth()

    # ── Cross-fitted T-learner: logistic regression per arm on one-hot
    # covariates — the estimator the calibration artifact itself used to
    # measure heterogeneity ("T-learner (logistic per arm)"). Two design
    # choices are power-driven and documented in the card: (a) the injected
    # per-segment effect (~0.5pp) sits below the per-segment sampling noise
    # of a tree learner's control model (~1.1pp), so the base learner is
    # linear; (b) every contact is scored out-of-fold (2 folds, stratified
    # by arm), so the whole experiment feeds both training and evaluation
    # instead of halving the already-small control arm. ──
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import OneHotEncoder

    rng = np.random.default_rng(SEED)
    fold = np.zeros(len(df), dtype=int)
    for arm in (True, False):
        i = np.flatnonzero(df["treated"].to_numpy() == arm)
        fold[rng.choice(i, size=len(i) // 2, replace=False)] = 1

    enc = OneHotEncoder(drop="first", sparse_output=True).fit(df[FEATURES])
    x_all = enc.transform(df[FEATURES])
    y_all = df["became_applicant"].to_numpy().astype(float)
    t_all = df["treated"].to_numpy().astype(int)

    u = np.empty(len(df))
    p_c_oof = np.empty(len(df))
    models = {}
    for k in (0, 1):
        fit_rows, score_rows = fold == k, fold != k
        for arm, name in [(1, "treated"), (0, "control")]:
            rows = fit_rows & (t_all == arm)
            models[f"{name}_fold{k}"] = LogisticRegression(max_iter=2000).fit(
                x_all[rows], y_all[rows])
        p_t = models[f"treated_fold{k}"].predict_proba(x_all[score_rows])[:, 1]
        p_c = models[f"control_fold{k}"].predict_proba(x_all[score_rows])[:, 1]
        u[score_rows] = p_t - p_c
        p_c_oof[score_rows] = p_c

    test, y_te, t_te = df, y_all, t_all  # evaluation set = all out-of-fold scores

    # Comparators: response-model targeting (rank by control-arm outcome
    # score -- the classic wrong tool) and the oracle injected-effect ranking
    seg_vals = np.sort(df["engagement_segment"].cat.categories.to_numpy())
    seg_to_mult = dict(zip(seg_vals, seg_mult))
    u_oracle = test["engagement_segment"].map(seg_to_mult).to_numpy(dtype=float)
    curves = {
        "model": uplift_curve(u, y_te, t_te),
        "response_targeting": uplift_curve(p_c_oof, y_te, t_te),
        "oracle_injected": uplift_curve(u_oracle, y_te, t_te),
    }

    # Per-segment recovery: predicted mean uplift vs injected vs empirical
    seg = pd.DataFrame({"segment": test["engagement_segment"].to_numpy(),
                        "u": u, "y": y_te, "t": t_te})
    g = seg.groupby("segment", observed=True)
    per_seg = pd.DataFrame({
        "predicted": g["u"].mean(),
        "injected": [ate_true * seg_to_mult[s] for s in g.groups],
        "empirical": g.apply(lambda s: s.loc[s.t == 1, "y"].mean() - s.loc[s.t == 0, "y"].mean(),
                             include_groups=False),
        "n": g.size(),
    })
    # Does the model put the concentrated segment on top?
    rank_agreement = float(np.corrcoef(
        per_seg["predicted"].rank(), per_seg["injected"].rank())[0, 1])

    metrics = dict(
        n=dict(contacts=len(df), treated=int(t_te.sum()),
               control=int(len(df) - t_te.sum()), folds=2),
        ate=dict(injected=ate_true,
                 empirical_test=float(y_te[t_te == 1].mean() - y_te[t_te == 0].mean()),
                 model_mean_uplift=float(u.mean())),
        auuc={k: v[2] for k, v in curves.items()},
        per_segment=per_seg.reset_index().to_dict(orient="records"),
        segment_rank_agreement=rank_agreement,
        top_segment_identified=bool(per_seg["predicted"].idxmax() == per_seg["injected"].idxmax()),
    )

    out_boosters = OUT_DIR / "boosters"
    out_boosters.mkdir(parents=True, exist_ok=True)
    joblib.dump({"encoder": enc, **models}, out_boosters / "m4_tlearner.joblib")
    report.write_metrics(OUT_DIR / "m4_metrics.json", metrics)

    build_report(metrics, curves, per_seg)
    print(f"model 4: AUUC model {metrics['auuc']['model']:.2e} vs response-targeting "
          f"{metrics['auuc']['response_targeting']:.2e} vs oracle {metrics['auuc']['oracle_injected']:.2e}; "
          f"top segment identified: {metrics['top_segment_identified']}")


def build_report(metrics, curves, per_seg) -> None:
    ate = metrics["ate"]

    # Uplift (gain) curves
    f1 = go.Figure()
    end = ate["empirical_test"]
    f1.add_scatter(x=[0, 1], y=[0, end], mode="lines", name="random targeting",
                   line=dict(color=report.NEUTRAL, width=2, dash="dot"), hoverinfo="skip")
    for key, name, color in [("oracle_injected", "oracle (injected effect)", report.CAT[2]),
                             ("model", "T-learner", report.CAT[0]),
                             ("response_targeting", "response-model targeting", report.CAT[1])]:
        frac, gain, _ = curves[key]
        f1.add_scatter(x=frac, y=gain, mode="lines", name=name,
                       line=dict(color=color, width=2),
                       hovertemplate="top %{x:.0%}: %{y:.5f} incremental applications/contact<extra>" + name + "</extra>")
    report.apply_layout(f1, title="Uplift gain curve, out-of-fold scores (absolute incremental applications)",
                        xaxis_title="fraction of contacts targeted (by predicted uplift)",
                        yaxis_title="incremental applications per contact", yaxis_tickformat=".4f")

    # Per-segment recovery
    segs = [str(s) for s in per_seg.index]
    f2 = go.Figure()
    f2.add_bar(x=segs, y=per_seg["injected"] * 100, name="injected",
               marker_color=report.CAT[2], hovertemplate="segment %{x}: %{y:.3f}pp<extra>injected</extra>")
    f2.add_bar(x=segs, y=per_seg["predicted"] * 100, name="T-learner predicted",
               marker_color=report.CAT[0], hovertemplate="segment %{x}: %{y:.3f}pp<extra>predicted</extra>")
    f2.add_scatter(x=segs, y=per_seg["empirical"] * 100, mode="markers",
                   name="empirical arm difference", marker=dict(color=report.INK, size=10, symbol="diamond"),
                   hovertemplate="segment %{x}: %{y:.3f}pp<extra>empirical</extra>")
    report.apply_layout(f2, title="Per-segment uplift: injected vs predicted vs empirical (pp)",
                        xaxis_title="engagement segment", yaxis_title="uplift (percentage points)",
                        barmode="group")

    tiles = [
        report.tile(f"{metrics['auuc']['model']:.2e}", "AUUC above random (T-learner)"),
        report.tile(f"{metrics['auuc']['response_targeting']:.2e}", "AUUC, response-model targeting"),
        report.tile("yes" if metrics["top_segment_identified"] else "no",
                    "concentrated segment ranked first"),
        report.tile(f"{ate['model_mean_uplift']*100:.3f}pp",
                    f"mean predicted uplift (injected {ate['injected']*100:.3f}pp)"),
    ]
    panels = [
        report.panel("Ranking quality", "The pooled experiment is underpowered (D10), so ranking "
                     "is the metric: the curve's rise above the random line is realized incremental "
                     "applications. The oracle curve is the ceiling an exact model could reach.",
                     report.fig_html(f1)),
        report.panel("Recovering the injected heterogeneity", "The engine concentrates ~4.5x the "
                     "average effect in one engagement segment; the other four are near zero.",
                     report.fig_html(f2)),
    ]
    n = metrics["n"]
    report.write_page(
        OUT_DIR / "m4_uplift.html", "Model 4 — Marketing uplift",
        "Cross-fitted T-learner (logistic regression per arm) on the randomized nurture experiment "
        f"at contact grain; pre-treatment covariates only; every contact scored out-of-fold "
        f"(n={n['contacts']:,}, control arm n={n['control']:,}, {n['folds']} folds). "
        "Model card: models/cards/model_4_uplift.md.",
        tiles, panels,
        "Phase 5, design Section 8 model 4. Rebuild: .venv/bin/python models/train_uplift.py")


if __name__ == "__main__":
    main()
