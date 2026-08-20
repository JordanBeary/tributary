-- CRM silo staging: entity grain preserved (one mutable row per lead).
-- Two silo pathologies unwound here, both documented not "fixed":
--   * naive US/Pacific wall-clock -> naive UTC via ICU localization. Inside
--     the DST fall-back hour wall-clock times are ambiguous by construction
--     (C17f observed lead_id order inverting there); ICU picks one offset,
--     so a one-hour error on ~1 hour of rows per year is inherent to the
--     silo, not a staging bug.
--   * email_sha256 arrives as 32-byte BYTEA (deployed D6 shape) and is
--     re-encoded to the export's lowercase hex for ER comparability with
--     the marketing silo's md5 ids.
select
    lead_id,
    lower(hex(email_sha256))                              as email_sha256,
    first_name,
    last_name,
    phone,
    state,
    zip_code,
    loan_amount,
    purpose,
    fico_band,
    employment_length,
    annual_income,
    timezone('UTC', timezone('America/Los_Angeles', submitted_at)) as submitted_at_utc,
    status,
    timezone('UTC', timezone('America/Los_Angeles', updated_at))   as updated_at_utc
from {{ source('crm', 'leads') }}
