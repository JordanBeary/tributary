-- One row per CRM lead, carrying its resolved consumer entity (dedupe
-- cluster), its best-match marketing contact, and the ER confidence. This
-- is the unification spine: every downstream mart joins through it.
select
    l.lead_id,
    c.cluster_id                                   as consumer_entity_id,
    m.contact_id                                   as marketing_contact_id,
    m.match_probability                            as contact_match_probability
from {{ ref('stg_crm__leads') }} l
left join {{ source('er', 'consumer_clusters') }} c
       on c.crm_lead_id = l.lead_id
left join {{ source('er', 'crm_contact_best_match') }} m
       on m.crm_lead_id = l.lead_id
