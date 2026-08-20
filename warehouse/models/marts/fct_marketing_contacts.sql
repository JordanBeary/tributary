-- Contact-grain wide fact: each marketing contact with its acquisition and
-- experiment attributes, its message funnel, and -- only possible after ER --
-- the applications, sales, funding, and auction revenue of the consumer it
-- resolves to. Revenue is attributed through the lead's best-match contact
-- (int_consumer_entities), so a person with several drifted contacts splits
-- revenue across them at lead grain, never double-counting a lead.
-- Uplift (design 7.3) reads treated vs in_holdout here: intention-to-treat,
-- per C15c.
with msgs as (
    select
        contact_id,
        count(*)                                        as messages_sent,
        sum((opened_at_utc is not null)::int)           as messages_opened,
        sum((clicked_at_utc is not null)::int)          as messages_clicked,
        min(sent_at_utc)                                as first_message_at_utc,
        max(sent_at_utc)                                as last_message_at_utc
    from {{ ref('stg_marketing__messages') }}
    group by 1
),

outcomes as (
    select
        marketing_contact_id                            as contact_id,
        mode(consumer_entity_id)                        as consumer_entity_id,
        count(*)                                        as applications,
        sum(sold::int)                                  as leads_sold,
        sum(coalesce(funded, false)::int)               as leads_funded,
        sum(revenue_usd)                                as revenue_usd,
        min(submitted_at_utc)                           as first_application_at_utc,
        max(submitted_at_utc)                           as last_application_at_utc
    from {{ ref('fct_leads') }}
    where marketing_contact_id is not null
    group by 1
)

select
    c.contact_id,
    c.acquisition_channel,
    c.engagement_segment,
    c.in_holdout,
    not c.in_holdout                                    as treated,
    c.acquired_at_utc,
    date_trunc('month', c.acquired_at_utc)              as acquired_month,
    c.state, c.zip_code,
    c.converted                                         as clicked_any_message,   -- the silo's own "conversion"

    coalesce(m.messages_sent, 0)                        as messages_sent,
    coalesce(m.messages_opened, 0)                      as messages_opened,
    coalesce(m.messages_clicked, 0)                     as messages_clicked,
    m.first_message_at_utc, m.last_message_at_utc,

    o.consumer_entity_id,
    o.applications is not null                          as became_applicant,
    coalesce(o.applications, 0)                         as applications,
    coalesce(o.leads_sold, 0)                           as leads_sold,
    coalesce(o.leads_funded, 0)                         as leads_funded,
    coalesce(o.revenue_usd, 0.0)                        as revenue_usd,
    o.first_application_at_utc, o.last_application_at_utc
from {{ ref('stg_marketing__contacts') }} c
left join msgs m     on m.contact_id = c.contact_id
left join outcomes o on o.contact_id = c.contact_id
