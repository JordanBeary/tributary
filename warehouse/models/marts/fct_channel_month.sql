-- Acquisition cohort economics, month x channel: the marketing silo's spend
-- ledger joined to the downstream applications, sales, and auction revenue of
-- the contacts acquired in that month (cohort attribution). ROAS and CAC are
-- computable only after unification -- spend lives in marketing, revenue in
-- the auction lake (design 7.3; C16 economics).
with cohort as (
    select
        strftime(acquired_month, '%Y%m')    as spend_month,
        acquisition_channel                 as channel,
        count(*)                            as contacts,
        sum(clicked_any_message::int)       as contacts_clicked,
        sum(became_applicant::int)          as contacts_applied,
        sum(applications)                   as applications,
        sum(leads_sold)                     as leads_sold,
        sum(leads_funded)                   as leads_funded,
        sum(revenue_usd)                    as revenue_usd
    from {{ ref('fct_marketing_contacts') }}
    group by 1, 2
)
select
    s.spend_month,
    cast(strptime(s.spend_month || '01', '%Y%m%d') as date)  as month_start,
    s.channel,
    s.channel in ('paid_search', 'paid_social', 'display', 'affiliate') as is_paid,
    s.impressions, s.visits, s.new_contacts, s.spend_usd,
    coalesce(c.contacts, 0)          as contacts,
    coalesce(c.contacts_clicked, 0)  as contacts_clicked,
    coalesce(c.contacts_applied, 0)  as contacts_applied,
    coalesce(c.applications, 0)      as applications,
    coalesce(c.leads_sold, 0)        as leads_sold,
    coalesce(c.leads_funded, 0)      as leads_funded,
    coalesce(c.revenue_usd, 0.0)     as revenue_usd,
    case when s.spend_usd > 0 then c.revenue_usd / s.spend_usd end           as roas,
    case when c.contacts > 0 then s.spend_usd / c.contacts end               as cac_per_contact,
    case when c.leads_sold > 0 then s.spend_usd / c.leads_sold end           as cost_per_sold_lead
from {{ ref('stg_marketing__channel_spend') }} s
left join cohort c using (spend_month, channel)
