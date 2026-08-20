-- Auction silo staging: event grain preserved (one row per waterfall event).
-- Timestamps are already UTC (the one silo that logs in UTC, design 2.3);
-- keep them naive-UTC, the staging-wide convention. The offer payload
-- (state/loan_amount/purpose/fico_band, C17a) is the only consumer signal
-- this silo carries -- no name, no email, no CRM/marketing key.
select
    lead_uuid,
    event_type,
    tier,
    buyer_id,
    bid_price,
    clearing_price,
    floor_price,
    event_at                       as event_at_utc,
    event_date,
    state,
    cast(loan_amount as integer)   as loan_amount,
    purpose,
    fico_band
from {{ source('auction', 'events') }}
