"""The fracture stage must make every Section 2.3 pathology real — and only those.

Runs the full five-stage pipeline at small scale into a tmp dir, then asserts
each pathology from the outside, the way the Phase 2-4 work will meet them:
key isolation (no silo carries another silo's key, or the hidden person key),
the migration orphans, current-state CRM semantics, timezone shifts, semantic
drift, and a crosswalk that accounts for every lead. The crosswalk lands in
private_dir and nowhere else — that invariant is the project's signature move.
"""

import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from simulation.config import SimConfig
from simulation.fracture import funded_rate_from_artifact
from simulation.pipeline import run_pipeline

SEED = 202608
SCALE = 0.01  # 15k consumer records -> ~24k leads: enough for rate assertions


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    out = tmp_path_factory.mktemp("generated")
    private = tmp_path_factory.mktemp("private")
    cfg = SimConfig(seed=SEED, scale=SCALE, out_dir=out, private_dir=private)
    run_pipeline(cfg)
    return cfg


def _silos(cfg):
    crm = pd.read_csv(cfg.out_dir / "crm" / "leads.csv",
                      parse_dates=["submitted_at", "updated_at"],
                      dtype={"zip_code": str})
    auction = pd.read_parquet(cfg.out_dir / "auction")
    contacts = pd.read_json(cfg.out_dir / "marketing" / "contacts.jsonl",
                            lines=True, dtype={"contact_id": str})
    xw = pd.read_parquet(cfg.private_dir / "crosswalk.parquet")
    return crm, auction, contacts, xw


def test_key_isolation(world):
    """No silo carries another silo's key, raw email, or the hidden keys."""
    crm, auction, contacts, _ = _silos(world)
    msgs = pd.read_json(world.out_dir / "marketing" / "messages.jsonl",
                        lines=True)
    forbidden = {"consumer_key", "consumer_record_id", "email", "q"}
    assert not (set(crm.columns) & (forbidden | {"lead_uuid", "contact_id"}))
    assert not (set(auction.columns) & (forbidden | {"lead_id", "contact_id",
                                                     "email_sha256"}))
    for df in (contacts, msgs):
        assert not (set(df.columns) & (forbidden | {"lead_uuid", "lead_id",
                                                    "email_sha256"}))


def test_crosswalk_accounts_for_everything(world):
    """One row per lead; keys resolve into each silo; the orphan gap shows up
    only as null CRM ids; hashes verify against the raw emails it retains."""
    crm, auction, contacts, xw = _silos(world)
    leads = pd.read_parquet(world.out_dir / "leads.parquet")
    assert len(xw) == len(leads)
    assert set(xw["lead_uuid"]) == set(leads["lead_uuid"])
    assert set(xw["crm_lead_id"].dropna().astype(int)) == set(crm["lead_id"])
    assert set(xw["contact_id"]) <= set(contacts["contact_id"])
    sample = xw.sample(200, random_state=0)
    assert (sample["contact_id"] == sample["email"].str.lower().map(
        lambda e: hashlib.md5(e.encode()).hexdigest())).all()


def test_migration_orphans(world):
    """~orphan_rate of leads are missing from the CRM, all from the early
    window; their auction events survive."""
    _, auction, _, xw = _silos(world)
    orphaned = xw[xw["crm_lead_id"].isna()]
    rate = len(orphaned) / len(xw)
    assert abs(rate - world.orphan_rate) < 0.005, f"orphan rate {rate:.3f}"
    leads = pd.read_parquet(world.out_dir / "leads.parquet")
    sub = leads.set_index("lead_uuid")["submitted_at"]
    cutoff = pd.Timestamp(world.window_start) + pd.DateOffset(months=3)
    assert (sub.reindex(orphaned["lead_uuid"]) < cutoff).all()
    assert set(orphaned["lead_uuid"]) <= set(auction["lead_uuid"])


def test_crm_semantics(world):
    """Dense renumbered ids in submission order; funded ⊂ sold at the artifact
    CVR; Pacific naive timestamps; updated_at overwritten after submission."""
    crm, _, _, xw = _silos(world)
    assert (np.diff(crm["lead_id"]) == 1).all()
    # lead_id follows UTC submission order, but the naive Pacific wall-clock is
    # NOT monotonic across the DST fall-back — the timezone pathology biting
    # exactly as designed. Local inversions must exist and stay under the 1h
    # repeated window.
    steps = crm["submitted_at"].diff().dropna()
    assert (steps > -pd.Timedelta(hours=1, minutes=1)).all()

    outcomes = pd.read_parquet(world.out_dir / "lead_outcomes.parquet")
    sold = (xw.dropna(subset=["crm_lead_id"])
            .merge(outcomes[["lead_uuid", "sold"]], on="lead_uuid")
            .set_index("crm_lead_id")["sold"])
    by_status = crm.set_index("lead_id")
    assert (sold.reindex(by_status[by_status.status == "funded"].index)).all()
    assert (sold.reindex(by_status[by_status.status == "sold"].index)).all()
    assert not (sold.reindex(
        by_status[by_status.status == "closed_lost"].index)).any()
    funded_share = (crm["status"] == "funded").sum() / sold.sum()
    target = funded_rate_from_artifact("simulation/params")
    assert abs(funded_share - target) < 0.02

    # Timezone: CRM wall-clock re-localized to Pacific equals the UTC pipeline time
    leads = pd.read_parquet(world.out_dir / "leads.parquet")
    utc = (leads.merge(xw[["lead_uuid", "crm_lead_id"]], on="lead_uuid")
           .dropna(subset=["crm_lead_id"]).set_index("crm_lead_id")
           ["submitted_at"])
    back = (by_status["submitted_at"].dt.tz_localize(
        "America/Los_Angeles", nonexistent="NaT", ambiguous="NaT")
        .dt.tz_convert("UTC").dt.tz_localize(None))
    both = pd.DataFrame({"utc": utc.reindex(back.index), "back": back}).dropna()
    assert (both["utc"] == both["back"]).all()
    assert (crm["updated_at"] > crm["submitted_at"]).all()


def test_auction_payload_and_utc(world):
    """bid_request rows carry the offer payload, terminal rows do not; event
    timestamps are unchanged UTC; partition column present."""
    _, auction, _, _ = _silos(world)
    req = auction["event_type"] == "bid_request"
    assert auction.loc[req, ["state", "loan_amount", "purpose",
                             "fico_band"]].notna().all().all()
    assert auction.loc[~req, "state"].isna().all()
    events = pd.read_parquet(world.out_dir / "auction_events.parquet")
    assert len(auction) == len(events)
    assert "event_date" in auction.columns
    # Partitioned layout on disk
    parts = list((world.out_dir / "auction").glob("event_date=*"))
    assert len(parts) > 300


def test_marketing_semantics(world):
    """contact_id is the only contact key; converted == clicked any message;
    Eastern wall-clock strings round-trip to the pipeline UTC times."""
    _, _, contacts, _ = _silos(world)
    msgs = pd.read_json(world.out_dir / "marketing" / "messages.jsonl",
                        lines=True)
    clicked_contacts = set(msgs.loc[msgs["clicked_at"].notna(), "contact_id"])
    assert set(contacts.loc[contacts["converted"], "contact_id"]) \
        == clicked_contacts

    raw = pd.read_parquet(world.out_dir / "messages.parquet")
    sent_utc = (pd.to_datetime(msgs["sent_at"])
                .dt.tz_localize("America/New_York", nonexistent="NaT",
                                ambiguous="NaT")
                .dt.tz_convert("UTC").dt.tz_localize(None))
    both = pd.DataFrame({
        "exported": sent_utc.astype("datetime64[ns]"),
        # Export carries whole-second ISO strings — compare at that precision
        "pipeline": (raw.sort_values("sent_at")["sent_at"]
                     .dt.floor("s").reset_index(drop=True)),
    }).dropna()
    assert (both["exported"] == both["pipeline"]).all()

    spend = pd.read_json(world.out_dir / "marketing" / "channel_spend.jsonl",
                         lines=True)
    assert spend["new_contacts"].sum() == len(contacts)


def test_crosswalk_stays_private(world):
    """The crosswalk exists only under private_dir — nothing crosswalk-shaped
    ships with the silos."""
    assert (world.private_dir / "crosswalk.parquet").exists()
    stray = [p for p in world.out_dir.rglob("*")
             if "crosswalk" in p.name.lower()]
    assert not stray
