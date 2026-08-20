-- Lead-grain wide fact (P-009): one row per auctioned lead (lead_uuid) carrying
-- the auction outcome, the offer payload, the CRM record, the marketing
-- contact, and the consumer entity it resolves to -- every silo's view of the
-- same application on one row. Migration orphans (auction-only, C17c) are
-- present with null CRM/consumer columns. Joins run through the Phase 3 spine.
--
-- Stated operating points: the consumer entity is the t=0.9 dedupe cluster
-- (D9b); the marketing contact is the Splink best match regardless of
-- probability (filter on contact_match_probability downstream if needed);
-- campaign attribution is last-touch within a 30-day pre-submission window.

with events as (
    select * from {{ ref('stg_auction__events') }}
),

-- Offer cascade: one bid_request per tier the lead was offered at; the
-- first request carries the submission time and the C17a payload.
requests as (
    select
        lead_uuid,
        min(event_at_utc)                  as submitted_at_utc,
        count(*)                           as tiers_offered,
        max(tier)                          as deepest_tier,
        arg_min(state, tier)               as state,
        arg_min(loan_amount, tier)         as loan_amount,
        arg_min(purpose, tier)             as purpose,
        arg_min(fico_band, tier)           as fico_band,
        arg_min(floor_price, tier)         as tier1_floor_price
    from events
    where event_type = 'bid_request'
    group by 1
),

bids as (
    select
        lead_uuid,
        count(*)                  as n_bids,
        count(distinct buyer_id)  as n_bidders,
        max(bid_price)            as max_bid
    from events
    where event_type = 'bid'
    group by 1
),

-- Second-price with reserve: the win row carries the clearing price but not
-- the buyer; the winner is the top bidder at the sold tier.
wins as (
    select lead_uuid, tier as sold_tier, clearing_price, floor_price as sold_tier_floor,
           event_at_utc as sold_at_utc
    from events
    where event_type = 'win'
),

tier_bids as (
    select lead_uuid, tier,
           arg_max(buyer_id, bid_price) as winning_buyer_id,
           max(bid_price)               as winning_bid,
           count(*)                     as n_bids_sold_tier
    from events
    where event_type = 'bid'
    group by 1, 2
),

spine as (
    select m.lead_uuid, m.crm_lead_id, m.consumer_entity_id, m.marketing_contact_id,
           e.contact_match_probability
    from {{ ref('int_auction_consumer_map') }} m
    left join {{ ref('int_consumer_entities') }} e on e.lead_id = m.crm_lead_id
),

crm as (
    select lead_id, status, annual_income, employment_length,
           submitted_at_utc as crm_submitted_at_utc, updated_at_utc as crm_updated_at_utc
    from {{ ref('stg_crm__leads') }}
),

contacts as (
    select contact_id, acquisition_channel, engagement_segment, in_holdout,
           acquired_at_utc as contact_acquired_at_utc
    from {{ ref('stg_marketing__contacts') }}
),

base as (
    select
        r.lead_uuid,
        s.crm_lead_id,
        s.consumer_entity_id,
        s.marketing_contact_id,
        s.contact_match_probability,
        s.crm_lead_id is null                      as is_orphan,
        s.marketing_contact_id is not null         as has_marketing_contact,

        r.submitted_at_utc,
        cast(r.submitted_at_utc as date)           as submitted_date,
        date_trunc('month', r.submitted_at_utc)    as submitted_month,

        -- offer payload (available for every lead, orphans included)
        r.state, r.loan_amount, r.purpose, r.fico_band,

        -- auction outcome
        r.tiers_offered, r.deepest_tier, r.tier1_floor_price,
        coalesce(b.n_bids, 0)                      as n_bids,
        coalesce(b.n_bidders, 0)                   as n_bidders,
        b.max_bid,
        w.sold_tier is not null                    as sold,
        w.sold_tier, w.sold_at_utc, w.sold_tier_floor,
        w.clearing_price,
        coalesce(w.clearing_price, 0.0)            as revenue_usd,
        tb.winning_buyer_id, tb.winning_bid, tb.n_bids_sold_tier,
        case when w.sold_tier is not null and w.clearing_price <= w.sold_tier_floor + 1e-9 then true
             when w.sold_tier is not null then false end as cleared_at_floor,

        -- CRM view (current state; funded reports back 7-45 days after sale)
        c.status                                   as crm_status,
        c.status = 'funded'                        as funded,
        c.annual_income, c.employment_length,
        c.crm_submitted_at_utc, c.crm_updated_at_utc,

        -- marketing view
        k.acquisition_channel, k.engagement_segment, k.in_holdout, k.contact_acquired_at_utc
    from requests r
    left join spine s      on s.lead_uuid = r.lead_uuid
    left join bids b       on b.lead_uuid = r.lead_uuid
    left join wins w       on w.lead_uuid = r.lead_uuid
    left join tier_bids tb on tb.lead_uuid = r.lead_uuid and tb.tier = w.sold_tier
    left join crm c        on c.lead_id = s.crm_lead_id
    left join contacts k   on k.contact_id = s.marketing_contact_id
),

-- Last-touch campaign: the most recent message to the matched contact inside
-- the 30 days before submission (ASOF join), plus pre-submission counts.
messages as (
    select contact_id, campaign_id, channel as message_channel, sent_at_utc,
           opened_at_utc is not null as opened, clicked_at_utc is not null as clicked
    from {{ ref('stg_marketing__messages') }}
),

last_touch as (
    select b.lead_uuid, m.campaign_id as last_touch_campaign_id,
           m.message_channel as last_touch_channel, m.sent_at_utc as last_touch_at_utc
    from base b
    asof join messages m
        on m.contact_id = b.marketing_contact_id
       and m.sent_at_utc <= b.submitted_at_utc
    where m.sent_at_utc >= b.submitted_at_utc - interval 30 day
),

pre_sub as (
    select b.lead_uuid,
           count(*)                    as msgs_30d_pre,
           sum(m.opened::int)          as opens_30d_pre,
           sum(m.clicked::int)         as clicks_30d_pre
    from base b
    join messages m
      on m.contact_id = b.marketing_contact_id
     and m.sent_at_utc <= b.submitted_at_utc
     and m.sent_at_utc >= b.submitted_at_utc - interval 30 day
    group by 1
),

-- Consumer-entity sequence: repeat applications and the duplicate-sale flags
-- that price the duplicate-consumer problem (design 7.3).
seq as (
    select
        lead_uuid,
        row_number() over w_entity                                   as application_seq,
        count(*) over (partition by consumer_entity_id)              as consumer_applications_total,
        date_diff('day', lag(submitted_at_utc) over w_entity, submitted_at_utc)
                                                                     as days_since_prior_application,
        -- the same buyer had already bought this consumer within 30 days
        case when sold then date_diff('day',
             lag(sold_at_utc) over (partition by consumer_entity_id, winning_buyer_id
                                    order by sold_at_utc, lead_uuid), sold_at_utc) end
                                                                     as days_since_prior_sale_same_buyer,
        -- any buyer had bought this consumer within 30 days
        case when sold then date_diff('day',
             lag(sold_at_utc) over (partition by consumer_entity_id, sold
                                    order by sold_at_utc, lead_uuid), sold_at_utc) end
                                                                     as days_since_prior_sale_any_buyer
    from base
    where consumer_entity_id is not null
    window w_entity as (partition by consumer_entity_id order by submitted_at_utc, lead_uuid)
)

select
    b.*,
    lt.last_touch_campaign_id, lt.last_touch_channel, lt.last_touch_at_utc,
    coalesce(p.msgs_30d_pre, 0)   as msgs_30d_pre,
    coalesce(p.opens_30d_pre, 0)  as opens_30d_pre,
    coalesce(p.clicks_30d_pre, 0) as clicks_30d_pre,
    q.application_seq,
    q.consumer_applications_total,
    coalesce(q.application_seq > 1, false)                         as is_repeat_application,
    q.days_since_prior_application,
    q.days_since_prior_sale_same_buyer,
    q.days_since_prior_sale_any_buyer,
    coalesce(q.days_since_prior_sale_same_buyer <= 30, false)      as duplicate_sale_same_buyer_30d,
    coalesce(q.days_since_prior_sale_any_buyer <= 30, false)       as duplicate_sale_any_buyer_30d
from base b
left join last_touch lt using (lead_uuid)
left join pre_sub p     using (lead_uuid)
left join seq q         using (lead_uuid)
