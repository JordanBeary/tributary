"""Marketing nurture engine — the production implementation of design.md Section 3.2 stage 4.

Consumes ``simulation/params/uplift_params.json`` (produced and QA-gated by
``analysis/profiling/03_criteo.ipynb``): the 85/15 treated/holdout split, the
absolute ATE on application probability, the out-of-sample engagement-segment
multipliers (C6: heterogeneity is concentrated — the top quintile carries ~4.5x
the average), and the C5 message funnel (send->open 0.35, open->click 0.08,
Poisson(3) messages per contact capped at 10).

Structure (C15). The nurture pool is built here, at contact grain (unique
email): every consumer record's email, plus never-applier prospects sized by
``cfg.marketing_only_rate`` — the experiment needs non-converters, and these
prospects double as the design's marketing-only orphan pathology. Applications
are already fixed by the leads stage, so the causal effect is injected by
**inverse construction**: within each engagement segment, the exact number of
converters assigned to treatment is solved so that treated-minus-holdout
conversion equals the injected per-segment uplift — a naive analyst recovers
the effect because it is arithmetically there. Assignment is intention-to-treat:
holdout contacts receive no messages, and ~5% of treated contacts draw zero
messages and stay silently enrolled.

Feasibility arithmetic (the INT-014 discipline): with tau <= ate x 4.52 ~ 0.52pp
and an ~90/10 converter/prospect pool, the solved treated-converter count moves
by well under 1% of either arm at any scale >= 0.01, so the construction always
has slack; per-segment rounding error is 0.5/min(arm size) ~ 0.01pp at test
scale, an order of magnitude under the smallest asserted tolerance.

Message timing is pre-submission nurture: sends land strictly before the
contact's first application (prospects use the full window). Open/click delays
and the mean-preserving segment factors on the funnel rates are declared
assumptions, recorded here as constants.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import json
import numpy as np
import pandas as pd

from simulation.consumers import IdentityVocab, _uuid4, sample_identity

N_SEGMENTS = 5
# Mean-preserving engagement scaling of the C5 funnel rates across segments
SEG_FACTORS = np.array([0.6, 0.8, 1.0, 1.2, 1.4])
CHANNELS = np.array(["email", "sms"])
CHANNEL_PROBS = np.array([0.85, 0.15])
OPEN_DELAY_MEAN_S = 6 * 3600.0     # send -> open lag (declared)
CLICK_DELAY_MEAN_S = 15 * 60.0     # open -> click lag (declared)

# ── Acquisition channels (C16): declared full-funnel economics ──
# Each contact enters the pool through an acquisition channel with its own
# intent level, and intent drives the whole funnel: contact->application
# conversion (conv_target, rescaled so the pool-weighted rate matches the
# structural rate implied by cfg.marketing_only_rate), engagement-segment mix
# (seg_tier), and lead quality among converters (q_tilt). Unit economics
# (click_to_contact, cpc/cpl, ctr) drive the monthly spend table so Phase 4
# can compute true per-channel CAC and ROAS through to auction revenue.
# Values are declared assumptions calibrated to lead-gen industry shape:
# personal-loan paid-search clicks are expensive ($10 CPC at 8% click->contact
# ~ $125 CAC), affiliates sell leads at ~$60 CPL, display retargeting buys
# cheap low-intent clicks that convert worst — by construction the channel mix
# spans clearly-profitable to unprofitable.
ACQ_CHANNELS = pd.DataFrame({
    "mix":              [0.08,   0.24,   0.08,   0.26,   0.12,   0.14,   0.08],
    "conv_target":      [0.97,   0.95,   0.93,   0.90,   0.85,   0.82,   0.72],
    "seg_tier":         ["high", "high", "mid",  "mid",  "low",  "low",  "low"],
    "q_tilt":           [0.30,   0.40,   0.20,   0.00,   -0.20,  -0.30,  -0.40],
    "click_to_contact": [0.35,   0.12,   0.10,   0.08,   np.nan, 0.025,  0.005],
    "cpc":              [0.0,    0.0,    0.0,    10.00,  np.nan, 1.60,   0.80],
    "cpl":              [np.nan, np.nan, np.nan, np.nan, 60.00,  np.nan, np.nan],
    "ctr":              [np.nan, np.nan, np.nan, 0.045,  np.nan, 0.009,  0.0025],
}, index=pd.Index(["direct", "organic_search", "referral", "paid_search",
                   "affiliate", "paid_social", "display"], name="channel"))

# Engagement-segment mix per intent tier (means 3.4 / 3.0 / 2.6)
SEG_TIER_PROBS = {
    "high": np.array([0.12, 0.16, 0.20, 0.24, 0.28]),
    "mid":  np.array([0.20, 0.20, 0.20, 0.20, 0.20]),
    "low":  np.array([0.28, 0.24, 0.20, 0.16, 0.12]),
}
ACQ_LAG_MEAN_S = 2 * 86_400.0      # acquisition -> first nurture send (declared)
SPEND_JITTER = 0.10                # monthly unit-cost wobble (declared)


@dataclass(frozen=True)
class UpliftModel:
    """The calibrated experiment parameterization, loaded verbatim from the artifact."""

    treated_share: float
    ate: float                  # absolute shift in application probability
    seg_mult: np.ndarray        # per-quintile multipliers, renormalized to mean 1
    open_rate: float
    click_rate: float
    lam: float                  # Poisson messages per treated contact
    cap: int

    @classmethod
    def from_params_dir(cls, params_dir: Path | str) -> "UpliftModel":
        p = json.loads((Path(params_dir) / "uplift_params.json").read_text())
        mult = np.asarray(p["heterogeneity"]["segment_multipliers"], dtype=float)
        funnel = p["message_funnel"]
        return cls(
            treated_share=p["treatment_ratio"],
            ate=p["ate"]["absolute"],
            seg_mult=mult / mult.mean(),
            open_rate=funnel["send_to_open"],
            click_rate=funnel["open_to_click"],
            lam=funnel["messages_per_contact_poisson_lambda"],
            cap=funnel["messages_cap"],
        )


def _contact_pool(consumers: pd.DataFrame, leads: pd.DataFrame,
                  vocab: IdentityVocab, marketing_only_rate: float,
                  rng: np.random.Generator) -> pd.DataFrame:
    """Contact grain = unique email. Consumer contacts carry their earliest
    application time; marketing-only prospects (fresh synthetic identities)
    never applied and have none."""
    by_rec = leads.groupby("consumer_record_id").agg(
        first_sub=("submitted_at", "min"), mean_q=("q", "mean"))
    # Phone/state/zip ride along: the ESP knows them from signup forms and SMS
    # reachability, and they are the cross-silo fuzzy-match signal for ER
    cons = consumers[["email", "first_name", "last_name", "phone",
                      "addr_state", "zip_code"]].copy()
    cons["first_sub"] = consumers["consumer_record_id"].map(by_rec["first_sub"])
    cons["_mean_q"] = consumers["consumer_record_id"].map(by_rec["mean_q"])
    contacts = (cons.sort_values("first_sub", kind="stable")
                .groupby("email", as_index=False)
                .agg(first_name=("first_name", "first"),
                     last_name=("last_name", "first"),
                     phone=("phone", "first"),
                     state=("addr_state", "first"),
                     zip_code=("zip_code", "first"),
                     first_sub=("first_sub", "min"),
                     _mean_q=("_mean_q", "mean")))
    contacts["is_marketing_only"] = False

    # Prospects sized so they are marketing_only_rate of the total pool
    n_mkt = round(len(contacts) * marketing_only_rate / (1 - marketing_only_rate))
    states = rng.choice(consumers["addr_state"].to_numpy(), size=n_mkt)
    ident = sample_identity(vocab, states, rng)
    # De-collide prospect emails against the consumer contact space
    taken = set(contacts["email"])
    clash = ident["email"].isin(taken)
    while clash.any():
        ident.loc[clash, "email"] = [
            e.partition("@")[0] + str(rng.integers(10)) + "@" + e.partition("@")[2]
            for e in ident.loc[clash, "email"]]
        clash = ident["email"].isin(taken) | ident["email"].duplicated()
    extras = pd.DataFrame({
        "email": ident["email"], "first_name": ident["first_name"],
        "last_name": ident["last_name"], "phone": ident["phone"],
        "state": states, "zip_code": ident["zip_code"],
        "first_sub": pd.NaT, "_mean_q": np.nan, "is_marketing_only": True,
    })
    pool = pd.concat([contacts, extras], ignore_index=True)
    return pool.iloc[rng.permutation(len(pool))].reset_index(drop=True)


def _assign_channels(pool: pd.DataFrame, marketing_only_rate: float,
                     rng: np.random.Generator) -> pd.DataFrame:
    """Acquisition channel per contact (C16), with the declared full funnel.

    Per-channel contact->application conversion targets are rescaled by one
    factor so the pool-weighted rate matches the structural rate implied by
    the marketing-only dial; the intent ordering is what carries the realism.
    Converter/prospect channel mixes follow by Bayes from (mix, conversion).
    Among converters, assignment tilts with realized mean lead quality
    (q_tilt), so high-intent channels also deliver better leads downstream.
    """
    a = ACQ_CHANNELS
    scale = (1 - marketing_only_rate) / (a["mix"] * a["conv_target"]).sum()
    conv_rate = (a["conv_target"] * scale).clip(upper=0.995)
    p_conv = (a["mix"] * conv_rate).to_numpy()
    p_conv = p_conv / p_conv.sum()
    p_pros = (a["mix"] * (1 - conv_rate)).to_numpy()
    p_pros = p_pros / p_pros.sum()

    channel = np.empty(len(pool), dtype=object)
    is_pros = pool["is_marketing_only"].to_numpy()

    # Prospects: plain mix draw (dominated by low-intent paid channels)
    channel[is_pros] = rng.choice(a.index.to_numpy(), size=int(is_pros.sum()),
                                  p=p_pros)
    # Converters: mix draw tilted by the contact's lead-quality percentile
    conv_idx = np.flatnonzero(~is_pros)
    q_pct = stats_rank(pool["_mean_q"].to_numpy()[conv_idx])
    probs = p_conv[None, :] * (1 + a["q_tilt"].to_numpy()[None, :]
                               * (q_pct[:, None] - 0.5))
    probs /= probs.sum(axis=1, keepdims=True)
    cum = np.cumsum(probs, axis=1)
    draw = rng.uniform(size=len(conv_idx))[:, None]
    pick = np.minimum((draw >= cum).sum(axis=1), len(a) - 1)  # float-sum guard
    channel[conv_idx] = a.index.to_numpy()[pick]
    return pool.assign(acquisition_channel=channel)


def stats_rank(x: np.ndarray) -> np.ndarray:
    """Percentile rank in (0,1); ties broken by stable order (x is continuous)."""
    order = np.argsort(x, kind="stable")
    ranks = np.empty(len(x))
    ranks[order] = np.arange(1, len(x) + 1)
    return ranks / (len(x) + 1)


def _assign_holdout(pool: pd.DataFrame, um: UpliftModel,
                    rng: np.random.Generator) -> pd.DataFrame:
    """Per-segment inverse construction: solve the exact treated-converter count
    so treated-minus-holdout conversion equals the injected per-segment uplift.

    With T treated and C holdout in a segment of N with A converters, setting
    T_a = round(T * (A + tau*C) / N) treated converters gives
    conv_T - conv_C = tau exactly (up to integer rounding).

    Segments draw from the acquisition channel's intent tier (C16), so
    engagement — and through it the funnel and the uplift response — is
    correlated with how the contact was acquired.
    """
    tier_matrix = np.stack([SEG_TIER_PROBS["high"], SEG_TIER_PROBS["mid"],
                            SEG_TIER_PROBS["low"]])
    tier_idx = (pool["acquisition_channel"].map(ACQ_CHANNELS["seg_tier"])
                .map({"high": 0, "mid": 1, "low": 2}).to_numpy())
    cum = np.cumsum(tier_matrix[tier_idx], axis=1)
    seg = 1 + (rng.uniform(size=(len(pool), 1)) >= cum).sum(axis=1)
    seg = np.minimum(seg, N_SEGMENTS)  # float-sum guard
    converted = ~pool["is_marketing_only"].to_numpy()
    treated = np.zeros(len(pool), dtype=bool)
    for s in range(1, N_SEGMENTS + 1):
        idx = np.flatnonzero(seg == s)
        n_s = len(idx)
        conv = converted[idx]
        a = int(conv.sum())
        t = int(round(um.treated_share * n_s))
        c = n_s - t
        tau = um.ate * um.seg_mult[s - 1]
        t_a = int(round(t * (a + tau * c) / n_s))
        t_m = t - t_a
        assert 0 <= t_a <= a and 0 <= t_m <= n_s - a, "inverse construction infeasible"
        treated[rng.permutation(idx[conv])[:t_a]] = True
        treated[rng.permutation(idx[~conv])[:t_m]] = True
    return pool.assign(engagement_segment=seg, in_holdout=~treated)


def _messages(pool: pd.DataFrame, um: UpliftModel, months: int,
              window_start: str, rng: np.random.Generator) -> pd.DataFrame:
    """Message-grain rows for treated contacts: pre-submission sends with the
    engagement-correlated C5 funnel."""
    start = pd.Timestamp(window_start)
    treated_idx = np.flatnonzero(~pool["in_holdout"].to_numpy())
    n_msgs = np.minimum(rng.poisson(um.lam, size=len(treated_idx)), um.cap)
    rep = np.repeat(treated_idx[n_msgs > 0], n_msgs[n_msgs > 0])

    # Nurture window: up to first application for converters, full window for
    # prospects. Sends are strictly pre-submission (uniform on [0, w) with the
    # degenerate w = 0 case dropped).
    window_s = int(months * 365.25 / 12) * 86_400.0
    fs = pool["first_sub"].to_numpy()
    w = np.where(np.isnat(fs), window_s,
                 (fs - start.to_numpy()) / np.timedelta64(1, "s"))
    t = rng.uniform(size=len(rep)) * w[rep]
    rep, t = rep[w[rep] > 0], t[w[rep] > 0]
    order = np.lexsort((t, rep))
    rep, t = rep[order], t[order]
    sent_at = start + pd.to_timedelta(t, unit="s")

    # Funnel: engagement-scaled open/click with seeded lags; click implies open
    seg = pool["engagement_segment"].to_numpy()[rep]
    opened = rng.uniform(size=len(rep)) < um.open_rate * SEG_FACTORS[seg - 1]
    clicked = opened & (rng.uniform(size=len(rep))
                        < um.click_rate * SEG_FACTORS[seg - 1])
    opened_at = sent_at + pd.to_timedelta(
        rng.exponential(OPEN_DELAY_MEAN_S, len(rep)), unit="s")
    clicked_at = opened_at + pd.to_timedelta(
        rng.exponential(CLICK_DELAY_MEAN_S, len(rep)), unit="s")

    msgs = pd.DataFrame({
        "message_id": _uuid4(len(rep), rng),
        "email": pool["email"].to_numpy()[rep],
        "channel": rng.choice(CHANNELS, size=len(rep), p=CHANNEL_PROBS),
        # Monthly campaign cohorts, keyed by send month (structured identifiers)
        "campaign_id": "camp_" + sent_at.to_period("M").astype(str)
                                 .str.replace("-", "", regex=False),
        "sent_at": sent_at,
        "opened_at": opened_at.where(opened),
        "clicked_at": clicked_at.where(clicked),
    })
    return msgs.sort_values("sent_at", kind="stable").reset_index(drop=True)


def _acquired_at(pool: pd.DataFrame, msgs: pd.DataFrame, months: int,
                 window_start: str, rng: np.random.Generator) -> np.ndarray:
    """When each contact entered the pool. Messaged contacts were acquired a
    short lag before their first send; unmessaged contacts draw uniformly over
    their own horizon (pre-application for converters, the window for
    prospects). Always before the first send and never after first_sub."""
    start = pd.Timestamp(window_start)
    window_s = int(months * 365.25 / 12) * 86_400.0
    fs = pool["first_sub"].to_numpy()
    horizon = np.where(np.isnat(fs), window_s,
                       (fs - start.to_numpy()) / np.timedelta64(1, "s"))
    t = rng.uniform(size=len(pool)) * horizon  # fallback: uniform on horizon

    first_send = msgs.groupby("email")["sent_at"].min()
    fsend = pool["email"].map(first_send).to_numpy()
    has_send = ~np.isnat(fsend)
    lag = rng.exponential(ACQ_LAG_MEAN_S, size=len(pool))
    send_s = (fsend - start.to_numpy()) / np.timedelta64(1, "s")
    t[has_send] = np.maximum(send_s[has_send] - lag[has_send], 0.0)
    return (start + pd.to_timedelta(t, unit="s")).to_numpy()


def _channel_spend(pool: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Monthly per-channel acquisition funnel and spend (C16).

    Traffic is back-derived from realized contacts: visits ~ contacts +
    Poisson slack at the declared click->contact rate (so visits >= contacts),
    impressions from the declared CTR for media channels. Spend is visits x
    CPC (with a monthly unit-cost wobble) for media, contacts x CPL for
    affiliate, zero for owned channels. Phase 4 joins this to auction revenue
    for true per-channel CAC and ROAS.
    """
    month = (pd.DatetimeIndex(pool["acquired_at"]).to_period("M").astype(str)
             .str.replace("-", "", regex=False))
    grp = (pd.DataFrame({"channel": pool["acquisition_channel"], "month": month})
           .groupby(["month", "channel"], as_index=False).size()
           .rename(columns={"size": "new_contacts"}))
    a = ACQ_CHANNELS.loc[grp["channel"]]
    n = grp["new_contacts"].to_numpy()

    rate = a["click_to_contact"].to_numpy()
    with np.errstate(invalid="ignore"):
        visits = np.where(np.isnan(rate), np.nan,
                          n + rng.poisson(np.nan_to_num(n * (1 - rate) / rate)))
        impressions = np.round(visits / a["ctr"].to_numpy())
    jitter = rng.uniform(1 - SPEND_JITTER, 1 + SPEND_JITTER, size=len(grp))
    cpc = a["cpc"].to_numpy()
    cpl = a["cpl"].to_numpy()
    spend = np.where(~np.isnan(cpl), n * cpl,
                     np.nan_to_num(visits * cpc * jitter))
    grp["visits"] = visits
    grp["impressions"] = impressions
    grp["spend_usd"] = np.round(spend, 2)
    return grp.sort_values(["month", "channel"]).reset_index(drop=True)


def build_marketing(consumers: pd.DataFrame, leads: pd.DataFrame,
                    um: UpliftModel, vocab: IdentityVocab, months: int,
                    window_start: str, marketing_only_rate: float,
                    rng: np.random.Generator,
                    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """The full marketing world: (contacts, messages, channel_spend).

    Contacts carry the experiment design (holdout flag, engagement segment)
    and acquisition provenance (channel, acquired_at) — the audience export a
    real ESP/CDP would hold; messages carry the sends and funnel events;
    channel_spend is the monthly media ledger. All keyed by email; the
    fracture stage derives contact_id = md5(lower(email)) and never sees
    consumer_key. The internal lead-quality column used for channel tilting
    is dropped — no silo may know underwriting quality directly.
    """
    pool = _contact_pool(consumers, leads, vocab, marketing_only_rate, rng)
    pool = _assign_channels(pool, marketing_only_rate, rng)
    pool = _assign_holdout(pool, um, rng)
    msgs = _messages(pool, um, months, window_start, rng)
    pool["acquired_at"] = _acquired_at(pool, msgs, months, window_start, rng)
    spend = _channel_spend(pool, rng)
    contacts = (pool.drop(columns="_mean_q")
                .sort_values("email", kind="stable").reset_index(drop=True))
    return contacts, msgs, spend
