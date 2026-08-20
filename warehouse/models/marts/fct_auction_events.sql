-- Event-grain wide fact (P-009): every auction event hydrated row-wise with the
-- lead's offer payload, consumer entity, CRM outcome, and marketing
-- acquisition attributes, so tier/buyer analyses segment by credit profile,
-- funding, and channel without joins. 24.5M rows; orphans keep null consumer
-- columns. Payload columns are filled on every row (the silo carries them on
-- bid_request rows only).
select
    e.lead_uuid,
    e.event_type,
    e.tier,
    e.buyer_id,
    e.bid_price,
    e.clearing_price,
    e.floor_price,
    e.event_at_utc,
    e.event_date,
    date_trunc('month', e.event_at_utc)        as event_month,

    -- offer payload, hydrated from the lead
    l.state, l.loan_amount, l.purpose, l.fico_band,

    -- unification spine
    l.crm_lead_id, l.consumer_entity_id, l.marketing_contact_id,
    l.is_orphan, l.has_marketing_contact,

    -- lead-level outcome carried onto each event
    l.sold, l.sold_tier, l.revenue_usd                        as lead_revenue_usd,
    l.winning_buyer_id,
    case when e.event_type = 'bid' and e.buyer_id = l.winning_buyer_id and e.tier = l.sold_tier
         then true when e.event_type = 'bid' then false end   as is_winning_bid,

    -- CRM and marketing attributes
    l.crm_status, l.funded, l.annual_income, l.employment_length,
    l.acquisition_channel, l.engagement_segment, l.in_holdout,
    l.last_touch_campaign_id,

    -- consumer-entity context
    l.application_seq, l.consumer_applications_total, l.is_repeat_application,
    l.duplicate_sale_same_buyer_30d, l.duplicate_sale_any_buyer_30d
from {{ ref('stg_auction__events') }} e
left join {{ ref('fct_leads') }} l on l.lead_uuid = e.lead_uuid
