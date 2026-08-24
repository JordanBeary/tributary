"""Model 1 — sale propensity: which leads will sell, and at which tier?

Gradient boosting (LightGBM) on the auction-time feature contract
(models/common.py), isotonic-calibrated on the validation months. A second
multiclass head predicts the sold tier conditional on a sale, so the pair
answers the design's question end to end: P(sold) and P(tier | sold).

Baselines (the exit criterion is beating them):
  B0  global training-period sell rate applied to every lead
  B1  group-rate table on recency bucket x FICO band (the two strongest
      drivers by construction: C19 demand dials and tier assignment)

Outputs: models/out/m1_metrics.json, models/out/m1_sale_propensity.html
(static evaluation report), boosters under models/out/boosters/ (git-ignored,
reproducible). Usage: .venv/bin/python models/train_sale_propensity.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from models import common, report
from models.common import FEATURES, OUT_DIR, SEED

LGB_PARAMS = dict(
    objective="binary", learning_rate=0.05, num_leaves=127, min_data_in_leaf=200,
    feature_fraction=0.9, bagging_fraction=0.8, bagging_freq=1,
    seed=SEED, verbosity=-1,
)
TIER_PARAMS = {**LGB_PARAMS, "objective": "multiclass", "num_class": common.N_TIERS}


def group_rate_baseline(train: pd.DataFrame, other: pd.DataFrame, target: str) -> np.ndarray:
    """B1: train-period rate per recency bucket x FICO band, global fallback."""
    keys = ["recency_bucket", "fico_band"]
    rates = train.groupby(keys, observed=True)[target].mean()
    joined = other[keys].merge(rates.rename("r"), left_on=keys, right_index=True, how="left")
    return joined["r"].fillna(train[target].mean()).to_numpy()


def ece(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    """Expected calibration error over equal-count probability bins."""
    order = np.argsort(p)
    splits = np.array_split(order, bins)
    return float(sum(len(s) * abs(y[s].mean() - p[s].mean()) for s in splits) / len(y))


def reliability(y: np.ndarray, p: np.ndarray, bins: int = 10):
    order = np.argsort(p)
    splits = np.array_split(order, bins)
    return ([float(p[s].mean()) for s in splits], [float(y[s].mean()) for s in splits])


def main() -> None:
    df = common.load_leads()
    train, valid, test = common.split_frames(df)
    y_tr, y_va, y_te = (s["sold"].to_numpy() for s in (train, valid, test))

    # ── Binary head: P(sold), early-stopped on the validation months ──
    dtrain = lgb.Dataset(train[FEATURES], y_tr)
    dvalid = lgb.Dataset(valid[FEATURES], y_va, reference=dtrain)
    booster = lgb.train(LGB_PARAMS, dtrain, num_boost_round=2000, valid_sets=[dvalid],
                        callbacks=[lgb.early_stopping(50, verbose=False)])

    # Isotonic calibration on validation scores (test stays untouched)
    p_va_raw = booster.predict(valid[FEATURES])
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0).fit(p_va_raw, y_va)
    p_te_raw = booster.predict(test[FEATURES])
    p_te = iso.predict(p_te_raw)

    # Baselines on the test months
    b0 = np.full(len(test), y_tr.mean())
    b1 = group_rate_baseline(train, test, "sold")

    def scores(p):
        return dict(
            roc_auc=float(roc_auc_score(y_te, p)), pr_auc=float(average_precision_score(y_te, p)),
            log_loss=float(log_loss(y_te, np.clip(p, 1e-6, 1 - 1e-6))),
            brier=float(brier_score_loss(y_te, p)), ece=ece(y_te, p),
        )

    metrics = dict(
        model=scores(p_te), model_uncalibrated=scores(p_te_raw),
        baseline_global=scores(b0), baseline_group_rate=scores(b1),
        best_iteration=booster.best_iteration,
        n=dict(train=len(train), valid=len(valid), test=len(test)),
        test_sell_rate=float(y_te.mean()),
    )

    # ── Tier head: P(sold_tier | sold), trained on sold training leads ──
    tr_s, va_s, te_s = (s[s["sold"]] for s in (train, valid, test))
    t_tr, t_va, t_te = (s["sold_tier"].to_numpy() - 1 for s in (tr_s, va_s, te_s))
    dtier = lgb.Dataset(tr_s[FEATURES], t_tr)
    dtier_v = lgb.Dataset(va_s[FEATURES], t_va, reference=dtier)
    tier_booster = lgb.train(TIER_PARAMS, dtier, num_boost_round=2000, valid_sets=[dtier_v],
                             callbacks=[lgb.early_stopping(50, verbose=False)])
    pt_te = tier_booster.predict(te_s[FEATURES])

    # Tier baseline: train-period tier mix within the same group table
    keys = ["recency_bucket", "fico_band"]
    mix = (tr_s.groupby(keys, observed=True)["sold_tier"]
           .value_counts(normalize=True).unstack(fill_value=0.0)
           .reindex(columns=range(1, common.N_TIERS + 1), fill_value=0.0))
    bt = te_s[keys].merge(mix, left_on=keys, right_index=True, how="left")
    bt = bt[list(range(1, common.N_TIERS + 1))].to_numpy(dtype=float)
    global_mix = np.bincount(t_tr, minlength=common.N_TIERS) / len(t_tr)
    bt[np.isnan(bt).any(axis=1)] = global_mix

    metrics["tier_head"] = dict(
        accuracy=float((pt_te.argmax(1) == t_te).mean()),
        log_loss=float(log_loss(t_te, np.clip(pt_te, 1e-9, 1), labels=list(range(common.N_TIERS)))),
        baseline_accuracy=float((bt.argmax(1) == t_te).mean()),
        baseline_log_loss=float(log_loss(t_te, np.clip(bt, 1e-9, 1), labels=list(range(common.N_TIERS)))),
        best_iteration=tier_booster.best_iteration,
        n_sold_test=len(te_s),
    )

    # ── Persist boosters (git-ignored) and metrics ──
    boosters = OUT_DIR / "boosters"
    boosters.mkdir(parents=True, exist_ok=True)
    booster.save_model(str(boosters / "m1_sold.txt"))
    tier_booster.save_model(str(boosters / "m1_tier.txt"))
    report.write_metrics(OUT_DIR / "m1_metrics.json", metrics)

    build_report(metrics, y_te, p_te, b1, test, pt_te, t_te)
    m = metrics["model"]
    print(f"model 1: test ROC-AUC {m['roc_auc']:.4f} (group baseline "
          f"{metrics['baseline_group_rate']['roc_auc']:.4f}), ECE {m['ece']:.4f}; "
          f"tier accuracy {metrics['tier_head']['accuracy']:.3f} vs "
          f"baseline {metrics['tier_head']['baseline_accuracy']:.3f}")


def build_report(metrics, y_te, p_te, b1, test, pt_te, t_te) -> None:
    m, bg = metrics["model"], metrics["baseline_group_rate"]

    # Reliability: calibrated model vs the group-rate baseline
    f1 = go.Figure()
    f1.add_scatter(x=[0, 1], y=[0, 1], mode="lines", name="perfect calibration",
                   line=dict(color=report.NEUTRAL, width=2, dash="dot"), hoverinfo="skip")
    for name, p, color in [("model (isotonic-calibrated)", p_te, report.CAT[0]),
                           ("group-rate baseline", b1, report.CAT[1])]:
        px, py = reliability(y_te, p)
        f1.add_scatter(x=px, y=py, mode="lines+markers", name=name,
                       line=dict(color=color, width=2), marker=dict(size=8),
                       hovertemplate="predicted %{x:.3f}, observed %{y:.3f}<extra>" + name + "</extra>")
    report.apply_layout(f1, title="Reliability on the test months (equal-count deciles)",
                        xaxis_title="mean predicted P(sold)", yaxis_title="observed sell rate")

    # Sell rate by model-score decile: separation the baseline cannot express
    order = np.argsort(p_te)
    deciles = np.array_split(order, 10)
    f2 = go.Figure()
    f2.add_bar(x=[f"d{i+1}" for i in range(10)], y=[float(y_te[s].mean()) for s in deciles],
               marker_color=report.CAT[0], name="observed sell rate",
               hovertemplate="%{x}: %{y:.1%}<extra></extra>")
    f2.add_scatter(x=[f"d{i+1}" for i in range(10)], y=[float(b1[s].mean()) for s in deciles],
                   mode="lines+markers", name="group-rate baseline prediction",
                   line=dict(color=report.CAT[1], width=2), marker=dict(size=8),
                   hovertemplate="%{x}: %{y:.1%}<extra></extra>")
    report.apply_layout(f2, title="Observed sell rate by model-score decile (test)",
                        xaxis_title="model score decile (low to high)", yaxis_title="sell rate",
                        yaxis_tickformat=".0%")

    # Tier head: predicted vs observed tier mix on sold test leads
    th = metrics["tier_head"]
    obs_mix = np.bincount(t_te, minlength=common.N_TIERS) / len(t_te)
    pred_mix = pt_te.mean(axis=0)
    f3 = go.Figure()
    f3.add_bar(x=[f"tier {t}" for t in range(1, 7)], y=obs_mix, name="observed",
               marker_color=[report.TIER_RAMP[t] for t in range(1, 7)],
               hovertemplate="%{x}: %{y:.1%}<extra>observed</extra>")
    f3.add_bar(x=[f"tier {t}" for t in range(1, 7)], y=pred_mix, name="predicted (mean P)",
               marker_color=report.NEUTRAL, hovertemplate="%{x}: %{y:.1%}<extra>predicted</extra>")
    report.apply_layout(f3, title="Sold-tier mix, observed vs predicted (sold test leads)",
                        yaxis_title="share of sales", yaxis_tickformat=".0%", barmode="group")

    tiles = [
        report.tile(f"{m['roc_auc']:.3f}", f"test ROC-AUC (baseline {bg['roc_auc']:.3f})"),
        report.tile(f"{m['ece']:.4f}", "expected calibration error (10 bins)"),
        report.tile(f"{m['brier']:.4f}", f"Brier score (baseline {bg['brier']:.4f})"),
        report.tile(f"{th['accuracy']:.1%}", f"tier accuracy | sold (baseline {th['baseline_accuracy']:.1%})"),
    ]
    panels = [
        report.panel("Calibration", "Isotonic calibration fitted on the validation months; "
                     "the test months are untouched until this evaluation.", report.fig_html(f1)),
        report.panel("Discrimination", "The model orders leads far beyond the recency-by-FICO "
                     "table: the top decile sells at several times the bottom decile's rate.",
                     report.fig_html(f2)),
        report.panel("Which tier", "Multiclass head conditional on a sale; combined with P(sold) "
                     "this answers the design's question end to end.", report.fig_html(f3)),
    ]
    n = metrics["n"]
    report.write_page(
        OUT_DIR / "m1_sale_propensity.html", "Model 1 — Sale propensity",
        "LightGBM on auction-time features from the unified marts; temporal split "
        f"(train n={n['train']:,}, valid n={n['valid']:,}, test n={n['test']:,}). "
        "Model card: models/cards/model_1_sale_propensity.md.",
        tiles, panels,
        "Phase 5, design Section 8 model 1. Rebuild: .venv/bin/python models/train_sale_propensity.py")


if __name__ == "__main__":
    main()
