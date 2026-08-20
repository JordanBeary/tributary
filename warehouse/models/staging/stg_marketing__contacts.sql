-- Marketing silo staging: contact grain. contact_id is md5 of lowercased
-- email (C17e) -- cryptographically unjoinable to the CRM's sha256 by
-- design; ER rides on name/phone/zip. Naive US/Eastern -> naive UTC.
select
    contact_id,
    first_name,
    last_name,
    phone,
    state,
    zip_code,
    acquisition_channel,
    engagement_segment,
    in_holdout,
    timezone('UTC', timezone('America/New_York', acquired_at)) as acquired_at_utc,
    converted
from {{ source('marketing', 'contacts') }}
