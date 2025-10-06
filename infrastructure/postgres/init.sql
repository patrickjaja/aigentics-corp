-- Initialize TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Log database initialization
DO $$
BEGIN
    RAISE NOTICE 'Starting database initialization...';
END $$;

-- Switch to offer_agent database
\c offer_agent;

-- Enable TimescaleDB
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Create pgcrypto for UUID generation
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Create event store schema
CREATE SCHEMA IF NOT EXISTS events;

-- Create event store table
CREATE TABLE IF NOT EXISTS events.domain_events (
    event_id UUID DEFAULT gen_random_uuid(),
    aggregate_id UUID NOT NULL,
    aggregate_type VARCHAR(100) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    event_version INT NOT NULL DEFAULT 1,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    correlation_id UUID,
    causation_id UUID,
    actor_id UUID,
    metadata JSONB,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (event_id, occurred_at)
);

-- Convert events table to hypertable for time-series optimization
SELECT create_hypertable('events.domain_events', 'occurred_at',
    chunk_time_interval => INTERVAL '1 month',
    if_not_exists => TRUE
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_events_aggregate ON events.domain_events (aggregate_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_type ON events.domain_events (event_type, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_correlation ON events.domain_events (correlation_id, occurred_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_aggregate_type ON events.domain_events (aggregate_type, occurred_at DESC);

-- Create read model schemas
CREATE SCHEMA IF NOT EXISTS read_models;

-- Customers read model
CREATE TABLE IF NOT EXISTS read_models.customers (
    id UUID PRIMARY KEY,
    external_id VARCHAR(255) UNIQUE,
    company_name VARCHAR(500),
    contact_person VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    language_preference VARCHAR(10),
    gdpr_consent_given_at TIMESTAMPTZ,
    gdpr_consent_withdrawn_at TIMESTAMPTZ,
    deletion_requested_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Conversations read model
CREATE TABLE IF NOT EXISTS read_models.conversations (
    id UUID PRIMARY KEY,
    session_id VARCHAR(255) UNIQUE,
    customer_id UUID REFERENCES read_models.customers(id),
    project_id UUID,
    language VARCHAR(10),
    status VARCHAR(50),
    completion_percentage INT DEFAULT 0,
    started_at TIMESTAMPTZ NOT NULL,
    last_interaction_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Offers read model
CREATE TABLE IF NOT EXISTS read_models.offers (
    id UUID PRIMARY KEY,
    offer_number VARCHAR(50) UNIQUE,
    version INT NOT NULL DEFAULT 1,
    customer_id UUID REFERENCES read_models.customers(id),
    project_id UUID,
    conversation_id UUID REFERENCES read_models.conversations(id),
    status VARCHAR(50),
    total_value_amount DECIMAL(15, 4),
    total_value_currency VARCHAR(10),
    valid_until DATE,
    approval_required BOOLEAN DEFAULT FALSE,
    approval_workflow_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Work packages read model
CREATE TABLE IF NOT EXISTS read_models.work_packages (
    id UUID PRIMARY KEY,
    offer_id UUID REFERENCES read_models.offers(id) ON DELETE CASCADE,
    name VARCHAR(500),
    description TEXT,
    estimated_hours_optimistic DECIMAL(10, 2),
    estimated_hours_likely DECIMAL(10, 2),
    estimated_hours_pessimistic DECIMAL(10, 2),
    confidence DECIMAL(3, 2),
    hourly_rate_amount DECIMAL(15, 4),
    hourly_rate_currency VARCHAR(10),
    total_cost_amount DECIMAL(15, 4),
    total_cost_currency VARCHAR(10),
    display_order INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Approval workflows read model
CREATE TABLE IF NOT EXISTS read_models.approval_workflows (
    id UUID PRIMARY KEY,
    offer_id UUID REFERENCES read_models.offers(id),
    requested_by UUID,
    approver_id UUID,
    status VARCHAR(50),
    decision_outcome VARCHAR(50),
    decision_reason TEXT,
    requested_at TIMESTAMPTZ,
    decided_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Analytics schema
CREATE SCHEMA IF NOT EXISTS analytics;

-- Offer metrics table
CREATE TABLE IF NOT EXISTS analytics.offer_metrics (
    id UUID DEFAULT gen_random_uuid(),
    offer_id UUID,
    metric_type VARCHAR(100),
    metric_value DECIMAL(15, 4),
    metric_unit VARCHAR(50),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, recorded_at)
);

-- Convert offer_metrics to hypertable
SELECT create_hypertable('analytics.offer_metrics', 'recorded_at',
    chunk_time_interval => INTERVAL '1 week',
    if_not_exists => TRUE
);

-- Conversation metrics table
CREATE TABLE IF NOT EXISTS analytics.conversation_metrics (
    id UUID DEFAULT gen_random_uuid(),
    conversation_id UUID,
    metric_type VARCHAR(100),
    metric_value DECIMAL(15, 4),
    metric_unit VARCHAR(50),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, recorded_at)
);

-- Convert conversation_metrics to hypertable
SELECT create_hypertable('analytics.conversation_metrics', 'recorded_at',
    chunk_time_interval => INTERVAL '1 week',
    if_not_exists => TRUE
);

-- Create indexes for analytics
CREATE INDEX IF NOT EXISTS idx_offer_metrics_offer ON analytics.offer_metrics (offer_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_offer_metrics_type ON analytics.offer_metrics (metric_type, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_metrics_conversation ON analytics.conversation_metrics (conversation_id, recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_conversation_metrics_type ON analytics.conversation_metrics (metric_type, recorded_at DESC);

-- Continuous aggregates for analytics
CREATE MATERIALIZED VIEW IF NOT EXISTS analytics.daily_offer_stats
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', recorded_at) AS day,
    metric_type,
    COUNT(*) as count,
    AVG(metric_value) as avg_value,
    MIN(metric_value) as min_value,
    MAX(metric_value) as max_value
FROM analytics.offer_metrics
GROUP BY day, metric_type;

-- Add refresh policy for continuous aggregate
SELECT add_continuous_aggregate_policy('analytics.daily_offer_stats',
    start_offset => INTERVAL '3 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

-- Grant permissions
GRANT USAGE ON SCHEMA events TO offer_agent;
GRANT ALL ON ALL TABLES IN SCHEMA events TO offer_agent;
GRANT USAGE ON SCHEMA read_models TO offer_agent;
GRANT ALL ON ALL TABLES IN SCHEMA read_models TO offer_agent;
GRANT USAGE ON SCHEMA analytics TO offer_agent;
GRANT ALL ON ALL TABLES IN SCHEMA analytics TO offer_agent;

-- Log initialization complete
DO $$
BEGIN
    RAISE NOTICE 'Database initialization completed successfully';
END $$;
