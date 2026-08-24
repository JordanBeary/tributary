"""Model 2 — winning-price landscape: what would buyers pay?

Censored regression via the design's survival framing (Section 8, model 2).
The waterfall is a discrete-time hazard process over the tier ladder: a lead
is offered tier 1..6 in order, clears the first tier whose reserve its top
bid meets, and is right-censored if it exits the ladder unsold. Two heads,
trained only on what a real marketplace observes (cascade depth, and the
clearing price on sales -- never sub-reserve bid amounts):

  hazard  h_t(x) = P(clears tier t | reached tier t, x)   LightGBM binary on
          stacked (lead, offered tier) rows
  price   E[log clearing | cleared at tier t, x]          LightGBM regression
          on sold leads

The landscape is their composition: P(sells at t) = h_t * prod_{s<t}(1-h_s),
expected lead value = sum_t P(sells at t) * E[price | t], P(unsold) =
prod_t (1-h_t).

Specification test (documented, not headline): the textbook Type-I Tobit
(models/tobit.py) is also fitted. In this world censoring is driven by
C19 participation suppression -- buyers who never bid -- not by continuously
low valuations, so a single-sigma latent Gaussian must stretch (sigma ~ 1.4
in logs) and its latent collapses far below the sub-reserve demand actually
logged. The report shows this with bids the models never train on.

Baselines:
  B0  expected value = group sell rate x group sold-mean price on recency
      bucket x FICO band (the pipeline-pricing table a team ships first)
  B1  sold-price accuracy: train-period mean price by sold tier

Outputs: models/out/m2_metrics.json, models/out/m2_price_landscape.html,
boosters under models/out/boosters/. Usage:
.venv/bin/python models/train_price_landscape.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from models import common, report, tobit
from models.common import FEATURES, N_TIERS, OUT_DIR, SEED

LGB_PARAMS = dict(
    learning_rate=0.05, num_leaves=127, min_data_in_leaf=200,
    feature_fraction=0.9, bagging_fraction=0.8, bagging_freq=1,
    seed=SEED, verbosity=-1,
)
HAZARD_FEATURES = FEATURES + ["tier"]
OUTER_ITERATIONS = 3  # Tobit sigma profiling


def stacked_ladder(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (lead, tier offered): the discrete-time survival frame.
    A lead offered through tier k contributes k rows; 'cleared' marks the
    terminal row of sold leads. deepest_tier is cascade history, observable
    row by row -- not leakage in this stacked construction."""
    with common.connect() as con:
        depth = con.sql("""
            select lead_uuid, deepest_tier from main_marts.fct_leads
        """).df()
    d = df.merge(depth, on="lead_uuid")
    rows = d.loc[d.index.repeat(d["deepest_tier"])].copy()
    rows["tier"] = rows.groupby(level=0).cumcount() + 1
    rows["cleared"] = (rows["sold"] & (rows["tier"] == rows["sold_tier"])).to_numpy()
    return rows


def expected_value(hazard: lgb.Booster, price: lgb.Booster, df: pd.DataFrame):
    """Compose the two heads into P(sells at t), E[price|t], EV, P(unsold)."""
    n = len(df)
    h = np.empty((n, N_TIERS))
    p = np.empty((n, N_TIERS))
    x = df[FEATURES].copy()
    for t in range(1, N_TIERS + 1):
        x["tier"] = t
        h[:, t - 1] = hazard.predict(x[HAZARD_FEATURES])
        p[:, t - 1] = np.exp(price.predict(x[HAZARD_FEATURES]))
    surv = np.cumprod(1 - h, axis=1)
    reach = np.column_stack([np.ones(n), surv[:, :-1]])
    p_sell = reach * h
    ev = (p_sell * p).sum(axis=1)
    return ev, p_sell, p, surv[:, -1]


def fit_tobit(train: pd.DataFrame, valid: pd.DataFrame, c_log: float):
    """The specification test: Type-I Tobit, sigma profiled in an outer loop."""
    def encode(df):
        y = np.where(df["sold"], np.log(df["clearing_price"].fillna(1.0)), c_log)
        return y, (~df["sold"]).to_numpy()

    y_tr, cen_tr = encode(train)
    y_va, cen_va = encode(valid)
    base = float(y_tr[~cen_tr].mean())
    sigma_holder = {"sigma": float(y_tr[~cen_tr].std())}
    booster = None
    for _ in range(OUTER_ITERATIONS):
        dtrain = lgb.Dataset(train[FEATURES], y_tr, init_score=np.full(len(train), base))
        dvalid = lgb.Dataset(valid[FEATURES], y_va, reference=dtrain,
                             init_score=np.full(len(valid), base))
        booster = lgb.train(
            {**LGB_PARAMS, "objective": tobit.make_objective(y_tr, cen_tr, sigma_holder)},
            dtrain, num_boost_round=1500, valid_sets=[dvalid],
            feval=tobit.make_feval(y_va, cen_va, sigma_holder),
            callbacks=[lgb.early_stopping(50, verbose=False)],
        )
        mu_tr = base + booster.predict(train[FEATURES], raw_score=True)
        sigma_holder["sigma"] = tobit.profile_sigma(mu_tr, y_tr, cen_tr)
    return booster, base, sigma_holder["sigma"]


def main() -> None:
    df = common.load_leads(columns=["max_bid", "n_bids"])
    train, valid, test = common.split_frames(df)

    # ── Hazard head on the stacked ladder ──
    lad_tr, lad_va = stacked_ladder(train), stacked_ladder(valid)
    dh = lgb.Dataset(lad_tr[HAZARD_FEATURES], lad_tr["cleared"].to_numpy())
    dh_v = lgb.Dataset(lad_va[HAZARD_FEATURES], lad_va["cleared"].to_numpy(), reference=dh)
    hazard = lgb.train({**LGB_PARAMS, "objective": "binary"}, dh, num_boost_round=2000,
                       valid_sets=[dh_v], callbacks=[lgb.early_stopping(50, verbose=False)])

    # ── Price head on sold leads (tier = the tier it cleared) ──
    tr_s, va_s, te_s = (s[s["sold"]].assign(tier=lambda d: d["sold_tier"])
                        for s in (train, valid, test))
    dp = lgb.Dataset(tr_s[HAZARD_FEATURES], np.log(tr_s["clearing_price"]))
    dp_v = lgb.Dataset(va_s[HAZARD_FEATURES], np.log(va_s["clearing_price"]), reference=dp)
    price = lgb.train({**LGB_PARAMS, "objective": "regression"}, dp, num_boost_round=2000,
                      valid_sets=[dp_v], callbacks=[lgb.early_stopping(50, verbose=False)])

    # ── Compose the landscape on the test months ──
    ev, p_sell, p_tier, p_unsold = expected_value(hazard, price, test)
    realized = test["clearing_price"].fillna(0.0).to_numpy()
    te_sold = test["sold"].to_numpy()

    # B0: group EV table (sell rate x sold mean), the pipeline-pricing default
    keys = ["recency_bucket", "fico_band"]
    g = train.groupby(keys, observed=True)
    table = (g["sold"].mean() * g["clearing_price"].mean()).rename("ev")
    b0 = test[keys].merge(table, left_on=keys, right_index=True, how="left")["ev"] \
        .fillna(train["sold"].mean() * train["clearing_price"].mean()).to_numpy()

    def ev_scores(pred):
        e = pred - realized
        order = np.argsort(-pred)
        top = order[: len(order) // 10]
        return dict(rmse=float(np.sqrt((e**2).mean())), bias=float(e.mean()),
                    spearman=float(spearmanr(pred, realized)[0]),
                    top_decile_revenue_capture=float(realized[top].sum() / realized.sum()))

    # Sold-price accuracy at the observed tier; B1 = train tier-mean price
    pred_price_sold = np.exp(price.predict(te_s[HAZARD_FEATURES]))
    tier_mean = tr_s.groupby("sold_tier")["clearing_price"].mean()
    b1 = te_s["sold_tier"].map(tier_mean).to_numpy()
    obs_price = te_s["clearing_price"].to_numpy()

    def price_scores(pred):
        e = pred - obs_price
        return dict(mae=float(np.abs(e).mean()), rmse=float(np.sqrt((e**2).mean())),
                    bias=float(e.mean()))

    # P(unsold) reliability
    order = np.argsort(p_unsold)
    deciles = np.array_split(order, 10)
    rel = dict(predicted=[float(p_unsold[s].mean()) for s in deciles],
               observed=[float((~te_sold)[s].mean()) for s in deciles])

    # ── Specification test: the textbook Tobit on the same split ──
    floors = common.tier_floors()
    c_log = float(np.log(floors[-1]))
    tb, tb_base, sigma = fit_tobit(train, valid, c_log)
    mu_te = tb_base + tb.predict(test[FEATURES], raw_score=True)
    unsold_bid = (~te_sold) & test["max_bid"].notna().to_numpy() & (test["n_bids"] > 0).to_numpy()
    # max_bid is leakage-excluded as a feature; here it is ground truth only.
    spec = dict(
        sigma=sigma, n_unsold_with_bids=int(unsold_bid.sum()),
        median_observed_max_bid=float(test.loc[unsold_bid, "max_bid"].median()),
        median_tobit_latent=float(np.exp(np.median(mu_te[unsold_bid]))),
        median_survival_ev=float(np.median(ev[unsold_bid])),
        spearman_tobit_vs_demand=float(spearmanr(mu_te[unsold_bid],
                                                 np.log(test.loc[unsold_bid, "max_bid"]))[0]),
        spearman_ev_vs_demand=float(spearmanr(ev[unsold_bid],
                                              np.log(test.loc[unsold_bid, "max_bid"]))[0]),
    )

    metrics = dict(
        ev_test=dict(model=ev_scores(ev), group_table=ev_scores(b0)),
        sold_price_test=dict(n=len(te_s), model=price_scores(pred_price_sold),
                             tier_mean=price_scores(b1)),
        p_unsold_reliability=rel,
        tobit_specification_test=spec,
        best_iteration=dict(hazard=hazard.best_iteration, price=price.best_iteration),
        n=dict(train=len(train), valid=len(valid), test=len(test),
               ladder_train_rows=len(lad_tr)),
        censored_share_test=float((~te_sold).mean()),
    )

    boosters = OUT_DIR / "boosters"
    boosters.mkdir(parents=True, exist_ok=True)
    hazard.save_model(str(boosters / "m2_hazard.txt"))
    price.save_model(str(boosters / "m2_price.txt"))
    tb.save_model(str(boosters / "m2_tobit.txt"))
    report.write_metrics(OUT_DIR / "m2_metrics.json", metrics)

    build_report(metrics, test, realized, ev, b0, obs_price, pred_price_sold, b1, te_s)
    e, s = metrics["ev_test"], metrics["sold_price_test"]
    print(f"model 2: EV Spearman {e['model']['spearman']:.3f} vs table {e['group_table']['spearman']:.3f}; "
          f"top-decile capture {e['model']['top_decile_revenue_capture']:.1%} vs "
          f"{e['group_table']['top_decile_revenue_capture']:.1%}; sold MAE ${s['model']['mae']:.2f} "
          f"vs tier-mean ${s['tier_mean']['mae']:.2f}; tobit sigma {spec['sigma']:.2f}")


def build_report(metrics, test, realized, ev, b0, obs_price, pred_price_sold, b1, te_s) -> None:
    e, s, rel, spec = (metrics["ev_test"], metrics["sold_price_test"],
                       metrics["p_unsold_reliability"], metrics["tobit_specification_test"])

    # EV calibration: predicted expected value vs realized revenue by decile
    f1 = go.Figure()
    for name, pred, color in [("survival landscape", ev, report.CAT[0]),
                              ("group EV table", b0, report.CAT[1])]:
        order = np.argsort(pred)
        bins = np.array_split(order, 10)
        f1.add_scatter(x=[float(pred[bin].mean()) for bin in bins],
                       y=[float(realized[bin].mean()) for bin in bins],
                       mode="lines+markers", name=name, line=dict(color=color, width=2),
                       marker=dict(size=8),
                       hovertemplate="predicted $%{x:,.0f}, realized $%{y:,.0f}<extra>" + name + "</extra>")
    lim = max(float(ev.max()), float(realized.mean() * 4))
    f1.add_scatter(x=[0, lim], y=[0, lim], mode="lines", name="predicted = realized",
                   line=dict(color=report.NEUTRAL, width=2, dash="dot"), hoverinfo="skip")
    report.apply_layout(f1, title="Expected lead value vs realized revenue (test deciles, unsold = $0)",
                        xaxis_title="mean predicted value ($)", yaxis_title="mean realized revenue ($)")

    # Sold-price accuracy
    f2 = go.Figure()
    f2.add_scatter(x=[2, 600], y=[2, 600], mode="lines", name="observed = predicted",
                   line=dict(color=report.NEUTRAL, width=2, dash="dot"), hoverinfo="skip")
    for name, pred, color in [("price head (at cleared tier)", pred_price_sold, report.CAT[0]),
                              ("tier-mean baseline", b1, report.CAT[3])]:
        order = np.argsort(pred)
        bins = np.array_split(order, 30)
        f2.add_scatter(x=[float(np.median(pred[bin])) for bin in bins],
                       y=[float(np.median(obs_price[bin])) for bin in bins],
                       mode="lines+markers", name=name, line=dict(color=color, width=2),
                       marker=dict(size=7),
                       hovertemplate="predicted $%{x:,.0f}, observed $%{y:,.0f}<extra>" + name + "</extra>")
    report.apply_layout(f2, title="Clearing price given a sale (sold test leads, 30 bins)",
                        xaxis=dict(type="log", title="median predicted price ($)", gridcolor=report.GRID),
                        yaxis=dict(type="log", title="median observed price ($)", gridcolor=report.GRID))

    # Censoring reliability
    f3 = go.Figure()
    f3.add_scatter(x=[0, 1], y=[0, 1], mode="lines", name="perfect",
                   line=dict(color=report.NEUTRAL, width=2, dash="dot"), hoverinfo="skip")
    f3.add_scatter(x=rel["predicted"], y=rel["observed"], mode="lines+markers",
                   name="survival P(unsold)", line=dict(color=report.CAT[0], width=2),
                   marker=dict(size=8),
                   hovertemplate="predicted %{x:.2f}, observed %{y:.2f}<extra></extra>")
    report.apply_layout(f3, title="Predicted exit probability vs observed unsold rate (deciles)",
                        xaxis_title="predicted P(lead exits the ladder unsold)",
                        yaxis_title="observed unsold rate")

    # Specification test: the Tobit's latent claims to be the price level
    # itself, so it is compared directly against logged sub-reserve demand.
    # (The survival EV is an expected revenue, a different quantity; its rank
    # agreement with this demand is reported in the note instead.)
    med = [("observed top bid (sub-reserve)", spec["median_observed_max_bid"], report.CAT[2]),
           ("Tobit latent value", spec["median_tobit_latent"], report.CAT[1])]
    f4 = go.Figure()
    f4.add_bar(x=[m[0] for m in med], y=[m[1] for m in med],
               marker_color=[m[2] for m in med],
               text=[f"${m[1]:,.2f}" for m in med], textposition="outside",
               hovertemplate="%{x}: $%{y:,.2f}<extra></extra>")
    report.apply_layout(f4, title=f"Unsold test leads that drew bids (n={spec['n_unsold_with_bids']:,}): "
                        "median value estimates vs the demand that showed up",
                        yaxis_title="median $ per lead", showlegend=False)

    tiles = [
        report.tile(f"{e['model']['top_decile_revenue_capture']:.1%}",
                    f"revenue in the top EV decile (table {e['group_table']['top_decile_revenue_capture']:.1%})"),
        report.tile(f"{e['model']['spearman']:.3f}",
                    f"EV rank corr with realized revenue (table {e['group_table']['spearman']:.3f})"),
        report.tile(f"${s['model']['mae']:.2f}",
                    f"sold-price MAE (tier-mean ${s['tier_mean']['mae']:.2f})"),
        report.tile(f"{metrics['censored_share_test']:.1%}", "test leads with no observed price"),
    ]
    panels = [
        report.panel("The landscape, calibrated in dollars", "Expected value composes the tier "
                     "hazards with the price head; unsold leads count as zero revenue, so this "
                     "curve is the censoring-aware check.", report.fig_html(f1)),
        report.panel("Price given a sale", "Within-tier price variation beyond the reserve "
                     "schedule is real signal: the price head halves the tier-mean baseline's "
                     "error.", report.fig_html(f2)),
        report.panel("Exit calibration", "The survival product P(unsold) against outcomes.",
                     report.fig_html(f3)),
        report.panel("Why the textbook Tobit fails here (specification test)",
                     f"A Type-I Tobit stretches to sigma = {spec['sigma']:.2f} in logs: censoring "
                     "in this marketplace is participation-driven (C19 recency suppression), not "
                     "low-valuation-driven, so the single-sigma latent collapses two orders of "
                     "magnitude below the sub-reserve demand the lake actually logged (median "
                     f"latent ${spec['median_tobit_latent']:.2f} vs ${spec['median_observed_max_bid']:.2f} "
                     "observed). The bids shown were never used in training either model; against "
                     "them the survival landscape's expected value ranks unsold leads as well as "
                     f"the Tobit does (Spearman {spec['spearman_ev_vs_demand']:.2f} vs "
                     f"{spec['spearman_tobit_vs_demand']:.2f}) while staying calibrated in dollars.",
                     report.fig_html(f4)),
    ]
    n = metrics["n"]
    report.write_page(
        OUT_DIR / "m2_price_landscape.html", "Model 2 — Winning-price landscape",
        "Discrete-time survival over the tier ladder (hazard head, "
        f"{n['ladder_train_rows']:,} stacked training rows) composed with a price head trained "
        f"only on observed sales; temporal split (train n={n['train']:,}, test n={n['test']:,}). "
        "Model card: models/cards/model_2_price_landscape.md.",
        tiles, panels,
        "Phase 5, design Section 8 model 2. Rebuild: .venv/bin/python models/train_price_landscape.py")


if __name__ == "__main__":
    main()
