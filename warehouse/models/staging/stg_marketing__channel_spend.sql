-- Marketing silo staging: month x channel spend. visits/impressions arrive
-- as float-or-null (nullable-count export artifact, D5); cast back to
-- integer counts here (BIGINT: monthly display impressions exceed INT32).
select
    "month"                       as spend_month,
    channel,
    cast(new_contacts as bigint)  as new_contacts,
    cast(visits as bigint)       as visits,
    cast(impressions as bigint)  as impressions,
    spend_usd
from {{ source('marketing', 'channel_spend') }}
