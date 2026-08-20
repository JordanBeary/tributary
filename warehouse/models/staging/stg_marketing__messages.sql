-- Marketing silo staging: message grain preserved. "converted" semantics in
-- this silo stop at the click (semantic drift, design 2.3); nothing here
-- claims revenue. Naive US/Eastern -> naive UTC.
select
    message_id,
    contact_id,
    campaign_id,
    channel,
    timezone('UTC', timezone('America/New_York', sent_at))    as sent_at_utc,
    timezone('UTC', timezone('America/New_York', opened_at))  as opened_at_utc,
    timezone('UTC', timezone('America/New_York', clicked_at)) as clicked_at_utc
from {{ source('marketing', 'messages') }}
