-- lead_uuid -> CRM lead -> consumer entity: the payload/time-proximity
-- linkage (er/link_auction_crm.py) that makes auction events
-- consumer-joinable (design Section 9 Phase 3 exit criterion). lag_s is
-- kept for audit: ~[0, 540] normally, ~-3600 for DST-ambiguous CRM rows.
select
    a.lead_uuid,
    a.crm_lead_id,
    a.lag_s,
    e.consumer_entity_id,
    e.marketing_contact_id
from {{ source('er', 'auction_crm_matches') }} a
left join {{ ref('int_consumer_entities') }} e
       on e.lead_id = a.crm_lead_id
