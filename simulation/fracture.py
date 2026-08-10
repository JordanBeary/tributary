"""Silo fracturing engine — the production implementation of design.md Sections 2.3/3.2 stage 5.

Takes the unified pipeline outputs and shatters them into three silos in their
native formats, applying every Section 2.3 pathology on the way (C17):

- **Incompatible keys.** Auction keeps ``lead_uuid``; the CRM mints a dense
  integer ``lead_id`` (renumbered post-"migration") plus ``email_sha256``;
  marketing derives ``contact_id = md5(lower(email))``. No silo carries another
  silo's key, and both email hashes use different algorithms so the silos
  cannot be joined cryptographically — names, phones, and zips carry the
  fuzzy ER signal instead.
- **Orphans.** ~``cfg.orphan_rate`` of leads vanish from the CRM, concentrated
  in the first three months of the window — the fictional migration lost a
  slice of legacy records; their auction events remain, orphaned. Marketing's
  never-converted contacts (C15/C16 prospects) are the other orphan family.
- **Grain.** Auction stays event-grain; the CRM is entity-grain current-state
  (status and updated_at are overwritten, no history — the log and the CRM
  legitimately disagree); marketing is message-grain plus the audience and
  spend exports.
- **Timezones.** Auction exports UTC; CRM timestamps convert to US/Pacific
  and drop the offset (naive); marketing converts to US/Eastern, ISO strings.
- **Semantic drift.** "Conversion" means *sold* in the auction silo (win
  events), *funded loan* in the CRM (``status = funded``, drawn at the
  artifact's conversions/clicks rate among sold leads), and *email click* in
  marketing (the contact-level ``converted`` flag).

The auction bid_request rows carry the offer payload (state, amount, purpose,
FICO band) — real lead auctions transmit the lead to buyers, and without the
payload the auction silo would be unlinkable to the CRM even in principle,
since no key survives by design.

The crosswalk — consumer_key through every silo key — is written to
``cfg.private_dir`` only. It never enters git or any cloud silo (design 2.4).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import json
import numpy as np
import pandas as pd

CRM_TZ = "America/Los_Angeles"
MKT_TZ = "America/New_York"
ORPHAN_WINDOW_MONTHS = 3       # the "migration" lost early records (C17)
LEAD_ID_START = 100_001        # CRM sequence start, renumbered post-migration
FUNDED_LAG_DAYS = (7, 45)      # sale -> funded report-back (declared)
CRM_UPDATE_LAG_S = 3600.0      # submission -> terminal status write (declared)


def _sha256_email(emails: pd.Series) -> pd.Series:
    return emails.str.lower().map(
        lambda e: hashlib.sha256(e.encode()).hexdigest())


def _md5_email(emails: pd.Series) -> pd.Series:
    return emails.str.lower().map(
        lambda e: hashlib.md5(e.encode()).hexdigest())


def _to_naive(ts: pd.Series, tz: str) -> pd.Series:
    """UTC-naive pipeline timestamps -> local wall-clock, offset dropped."""
    return ts.dt.tz_localize("UTC").dt.tz_convert(tz).dt.tz_localize(None)


def funded_rate_from_artifact(params_dir: Path | str) -> float:
    """CRM funded flag rate = the artifact's conversions/clicks (spec Section 2)."""
    src = json.loads((Path(params_dir) / "auction_landscape.json").read_text()
                     )["metadata"]["sources"]
    return src["conversions"] / src["clicks"]


def build_crm(leads: pd.DataFrame, consumers: pd.DataFrame,
              outcomes: pd.DataFrame, window_start: str, orphan_rate: float,
              funded_rate: float, rng: np.random.Generator,
              ) -> tuple[pd.DataFrame, pd.Series]:
    """Entity-grain CRM table + the lead_uuid -> lead_id map for the crosswalk.

    Orphan drop first (migration), then a dense renumbered id sequence in
    submission order. Status is current-state: sold leads are 'funded' at the
    artifact CVR else 'sold'; the rest are 'closed_lost'. updated_at is the
    single overwritten audit column.
    """
    df = (leads.merge(consumers[["consumer_record_id", "email", "first_name",
                                 "last_name", "phone", "street_address",
                                 "city", "zip_code"]], on="consumer_record_id")
          .merge(outcomes[["lead_uuid", "sold"]], on="lead_uuid"))

    # Migration data loss: the orphan budget comes out of the earliest months
    cutoff = pd.Timestamp(window_start) + pd.DateOffset(months=ORPHAN_WINDOW_MONTHS)
    eligible = np.flatnonzero((df["submitted_at"] < cutoff).to_numpy())
    n_drop = min(round(orphan_rate * len(df)), len(eligible))
    dropped = rng.choice(eligible, size=n_drop, replace=False)
    df = df.drop(index=df.index[dropped]).sort_values(
        "submitted_at", kind="stable").reset_index(drop=True)
    df["lead_id"] = LEAD_ID_START + np.arange(len(df))

    # Current-state status + overwritten audit timestamp (entity-grain, mutable)
    funded = df["sold"].to_numpy() & (rng.uniform(size=len(df)) < funded_rate)
    df["status"] = np.select([funded, df["sold"]], ["funded", "sold"],
                             default="closed_lost")
    lag = np.where(
        funded,
        rng.uniform(*(d * 86_400.0 for d in FUNDED_LAG_DAYS), size=len(df)),
        rng.uniform(CRM_UPDATE_LAG_S, 2 * CRM_UPDATE_LAG_S, size=len(df)))
    df["updated_at"] = df["submitted_at"] + pd.to_timedelta(lag, unit="s")

    crm = pd.DataFrame({
        "lead_id": df["lead_id"],
        "email_sha256": _sha256_email(df["email"]),
        "first_name": df["first_name"], "last_name": df["last_name"],
        "phone": df["phone"], "street_address": df["street_address"],
        "city": df["city"], "state": df["addr_state"],
        "zip_code": df["zip_code"],
        "loan_amount": df["loan_amnt"].astype(int),
        "purpose": df["purpose"], "fico_band": df["fico_band"],
        "employment_length": df["emp_length"],
        "annual_income": df["annual_inc"].round(0).astype(int),
        "submitted_at": _to_naive(df["submitted_at"], CRM_TZ),
        "status": df["status"],
        "updated_at": _to_naive(df["updated_at"], CRM_TZ),
    })
    id_map = df.set_index("lead_uuid")["lead_id"]
    return crm, id_map


CRM_SCHEMA_SQL = """\
-- CRM silo: entity-grain lead table (one mutable row per lead).
-- Timestamps are naive US/Pacific wall-clock, as exported by the CRM vendor.
-- 'Conversion' here means a funded loan (status = 'funded').
CREATE TABLE IF NOT EXISTS leads (
    lead_id           BIGINT PRIMARY KEY,
    email_sha256      CHAR(64) NOT NULL,
    first_name        TEXT,
    last_name         TEXT,
    phone             TEXT,
    street_address    TEXT,
    city              TEXT,
    state             CHAR(2),
    zip_code          CHAR(5),
    loan_amount       INTEGER,
    purpose           TEXT,
    fico_band         TEXT,
    employment_length TEXT,
    annual_income     INTEGER,
    submitted_at      TIMESTAMP,
    status            TEXT,
    updated_at        TIMESTAMP
);

-- Load (psql):
-- \\copy leads FROM 'leads.csv' WITH (FORMAT csv, HEADER true)
"""


def build_auction_export(events: pd.DataFrame,
                         leads: pd.DataFrame) -> pd.DataFrame:
    """Event-grain export, UTC, partitionable by event date. bid_request rows
    carry the offer payload the platform sent to buyers."""
    out = events.copy()
    payload = leads.set_index("lead_uuid")[
        ["addr_state", "loan_amnt", "purpose", "fico_band"]]
    req = out["event_type"] == "bid_request"
    looked = payload.reindex(out.loc[req, "lead_uuid"])
    out.loc[req, "state"] = looked["addr_state"].to_numpy()
    out.loc[req, "loan_amount"] = looked["loan_amnt"].to_numpy()
    out.loc[req, "purpose"] = looked["purpose"].to_numpy()
    out.loc[req, "fico_band"] = looked["fico_band"].to_numpy()
    out["event_date"] = out["event_at"].dt.strftime("%Y-%m-%d")
    return out


def build_marketing_export(contacts: pd.DataFrame, messages: pd.DataFrame,
                           spend: pd.DataFrame,
                           ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """ESP-style exports: hashed contact ids, US/Eastern wall-clock ISO strings.
    'Conversion' here means an email click (contact-level converted flag)."""
    cid = _md5_email(contacts["email"])
    clicked = (messages.loc[messages["clicked_at"].notna(), "email"]
               .drop_duplicates())
    contacts_out = pd.DataFrame({
        "contact_id": cid,
        "first_name": contacts["first_name"],
        "last_name": contacts["last_name"],
        "phone": contacts["phone"], "state": contacts["state"],
        "zip_code": contacts["zip_code"],
        "acquisition_channel": contacts["acquisition_channel"],
        "engagement_segment": contacts["engagement_segment"],
        "in_holdout": contacts["in_holdout"],
        "acquired_at": _to_naive(pd.Series(contacts["acquired_at"]),
                                 MKT_TZ).dt.strftime("%Y-%m-%dT%H:%M:%S"),
        "converted": contacts["email"].isin(set(clicked)),
    })
    cid_map = pd.Series(cid.to_numpy(), index=contacts["email"].to_numpy())
    msgs_out = pd.DataFrame({
        "message_id": messages["message_id"],
        "contact_id": messages["email"].map(cid_map),
        "campaign_id": messages["campaign_id"],
        "channel": messages["channel"],
    })
    for col in ("sent_at", "opened_at", "clicked_at"):
        msgs_out[col] = _to_naive(messages[col],
                                  MKT_TZ).dt.strftime("%Y-%m-%dT%H:%M:%S")
    return contacts_out, msgs_out, spend.copy()


def build_crosswalk(consumers: pd.DataFrame, leads: pd.DataFrame,
                    crm_id_map: pd.Series) -> pd.DataFrame:
    """The hidden ground truth, lead grain: consumer_key -> record -> lead_uuid
    -> CRM lead_id (null where the migration orphaned it) -> marketing
    contact_id. Never leaves cfg.private_dir (design Section 2.4)."""
    xw = leads[["lead_uuid", "consumer_record_id"]].merge(
        consumers[["consumer_record_id", "consumer_key", "email",
                   "is_duplicate"]], on="consumer_record_id")
    xw["crm_lead_id"] = xw["lead_uuid"].map(crm_id_map).astype("Int64")
    xw["contact_id"] = _md5_email(xw["email"])
    return xw[["consumer_key", "consumer_record_id", "lead_uuid",
               "crm_lead_id", "contact_id", "email", "is_duplicate"]]
