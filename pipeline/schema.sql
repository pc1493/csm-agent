-- DuckDB schema for the Low-ARR Renewal Agent.
-- Loaded by pipeline/db.py. The Streamlit app reads exclusively from these tables.

CREATE TABLE IF NOT EXISTS account_results (
    account_id           VARCHAR PRIMARY KEY,
    account_name         VARCHAR,
    industry             VARCHAR,
    arr_usd              DOUBLE,
    usage_tier           VARCHAR,
    days_to_renewal      INTEGER,
    strategy             VARCHAR,
    replied              BOOLEAN,
    sentiment            VARCHAR,        -- nullable: no reply
    renewal_likelihood   DOUBLE,         -- nullable
    upsell_signal        BOOLEAN,
    upsell_type          VARCHAR,
    nba_action           VARCHAR,
    nba_play             VARCHAR,
    nba_priority         VARCHAR,
    estimated_value_usd  DOUBLE,
    decision             VARCHAR,        -- auto | escalate
    queue                VARCHAR,        -- save_call | ae_upsell | ... | none
    confidence           DOUBLE,
    exception_codes      VARCHAR,        -- comma-joined E-codes, '' if clean
    outreach_subject     VARCHAR,
    outreach_body        VARCHAR,
    reply_body           VARCHAR         -- NULL for bounce / silent
);

CREATE TABLE IF NOT EXISTS exceptions_queue (
    account_id     VARCHAR,
    exception_code VARCHAR,             -- E1..E8
    queue          VARCHAR,
    note           VARCHAR
);

CREATE TABLE IF NOT EXISTS eval_metrics (
    account_id                 VARCHAR PRIMARY KEY,
    pred_sentiment             VARCHAR,
    true_sentiment             VARCHAR,
    sentiment_correct          BOOLEAN,
    pred_renewal_likelihood    DOUBLE,
    true_disposition           VARCHAR,
    disposition_bucket_correct BOOLEAN,
    pred_upsell_type           VARCHAR,
    true_upsell_fit            VARCHAR,
    upsell_correct             BOOLEAN,
    confidence                 DOUBLE,
    was_escalated              BOOLEAN
);
