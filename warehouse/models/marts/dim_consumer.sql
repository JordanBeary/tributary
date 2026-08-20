-- Consumer-entity dimension: one row per resolved person (dedupe cluster at
-- t=0.9, D9b) with identity multiplicity, application history, lifetime
-- auction revenue, funding, and the channel that acquired them. The "how many
-- consumers" question (silo audit Section 2) is answered by this table's row
-- count, against lead_uuid and lead_id counts in the silos.
select
    consumer_entity_id,
    count(distinct crm_lead_id)                          as crm_identities,
    count(distinct marketing_contact_id)                 as marketing_contacts,
    count(*)                                             as applications,
    min(submitted_at_utc)                                as first_application_at_utc,
    max(submitted_at_utc)                                as last_application_at_utc,
    sum(sold::int)                                       as leads_sold,
    sum(coalesce(funded, false)::int)                    as leads_funded,
    sum(revenue_usd)                                     as lifetime_revenue_usd,
    sum(case when duplicate_sale_any_buyer_30d then revenue_usd else 0 end)
                                                         as duplicate_sale_revenue_usd,
    arg_min(acquisition_channel, submitted_at_utc)       as acquisition_channel,
    arg_min(fico_band, submitted_at_utc)                 as first_fico_band,
    arg_max(fico_band, submitted_at_utc)                 as last_fico_band,
    arg_min(state, submitted_at_utc)                     as state,
    bool_or(in_holdout)                                  as any_contact_in_holdout
from {{ ref('fct_leads') }}
where consumer_entity_id is not null
group by 1
