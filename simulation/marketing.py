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
    first_sub = leads.groupby("consumer_record_id")["submitted_at"].min()
    cons = consumers[["email", "first_name", "last_name"]].copy()
    cons["first_sub"] = consumers["consumer_record_id"].map(first_sub)
    contacts = (cons.sort_values("first_sub", kind="stable")
                .groupby("email", as_index=False)
                .agg(first_name=("first_name", "first"),
                     last_name=("last_name", "first"),
                     first_sub=("first_sub", "min")))
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
        "last_name": ident["last_name"], "first_sub": pd.NaT,
        "is_marketing_only": True,
    })
    pool = pd.concat([contacts, extras], ignore_index=True)
    return pool.iloc[rng.permutation(len(pool))].reset_index(drop=True)


def _assign_holdout(pool: pd.DataFrame, um: UpliftModel,
                    rng: np.random.Generator) -> pd.DataFrame:
    """Per-segment inverse construction: solve the exact treated-converter count
    so treated-minus-holdout conversion equals the injected per-segment uplift.

    With T treated and C holdout in a segment of N with A converters, setting
    T_a = round(T * (A + tau*C) / N) treated converters gives
    conv_T - conv_C = tau exactly (up to integer rounding).
    """
    seg = rng.integers(1, N_SEGMENTS + 1, size=len(pool))
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


def build_marketing(consumers: pd.DataFrame, leads: pd.DataFrame,
                    um: UpliftModel, vocab: IdentityVocab, months: int,
                    window_start: str, marketing_only_rate: float,
                    rng: np.random.Generator) -> tuple[pd.DataFrame, pd.DataFrame]:
    """The full marketing world: (contacts, messages).

    Contacts carry the experiment design (holdout flag, engagement segment) —
    the audience export a real ESP would hold; messages carry the sends and
    funnel events. Both are keyed by email; the fracture stage derives
    contact_id = md5(lower(email)) and never sees consumer_key.
    """
    pool = _contact_pool(consumers, leads, vocab, marketing_only_rate, rng)
    pool = _assign_holdout(pool, um, rng)
    msgs = _messages(pool, um, months, window_start, rng)
    contacts = pool.sort_values("email", kind="stable").reset_index(drop=True)
    return contacts, msgs
