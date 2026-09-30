-- =============================================================================
-- PRAHARI — PostgreSQL 16 Schema Definition
-- SIH 26186 — AI-Powered Personnel Stress and Welfare Monitoring System
-- Baseline Schema for 28 Tables
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- =============================================================================
-- 1. Master Data & Identity
-- =============================================================================

-- Units
CREATE TABLE IF NOT EXISTS units (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unit_code VARCHAR(50) UNIQUE NOT NULL,
    unit_name VARCHAR(150) NOT NULL,
    unit_type VARCHAR(80) NOT NULL,
    parent_unit_id UUID REFERENCES units(id) ON DELETE SET NULL,
    location_label VARCHAR(150),
    sanctioned_strength INTEGER NOT NULL CHECK (sanctioned_strength >= 0),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_units_code ON units(unit_code);
CREATE INDEX IF NOT EXISTS idx_units_parent ON units(parent_unit_id);
CREATE INDEX IF NOT EXISTS idx_units_active ON units(is_active);

-- Personnel
CREATE TABLE IF NOT EXISTS personnel (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    personnel_code VARCHAR(50) UNIQUE NOT NULL,
    pseudo_id VARCHAR(50) UNIQUE NOT NULL,
    full_name VARCHAR(150) NOT NULL,
    unit_id UUID NOT NULL REFERENCES units(id) ON DELETE RESTRICT,
    rank_or_grade VARCHAR(80) NOT NULL,
    role_title VARCHAR(100) NOT NULL,
    status VARCHAR(40) NOT NULL,
    joining_date DATE,
    service_years NUMERIC(5,2) CHECK (service_years >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_personnel_code ON personnel(personnel_code);
CREATE INDEX IF NOT EXISTS idx_personnel_pseudo ON personnel(pseudo_id);
CREATE INDEX IF NOT EXISTS idx_personnel_unit ON personnel(unit_id);
CREATE INDEX IF NOT EXISTS idx_personnel_status ON personnel(status);
CREATE INDEX IF NOT EXISTS idx_personnel_name ON personnel(full_name);

-- Users (Exactly four roles)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role VARCHAR(30) NOT NULL CHECK (role IN ('PERSONNEL', 'COMMANDER', 'WELFARE_OFFICER', 'ADMIN')),
    personnel_id UUID REFERENCES personnel(id) ON DELETE SET NULL,
    unit_id UUID REFERENCES units(id) ON DELETE SET NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_personnel ON users(personnel_id);
CREATE INDEX IF NOT EXISTS idx_users_unit ON users(unit_id);
CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active);

-- Auth Sessions
CREATE TABLE IF NOT EXISTS auth_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    jti UUID UNIQUE NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    revoke_reason VARCHAR(80)
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_revoked ON auth_sessions(user_id, revoked_at);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON auth_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_sessions_jti ON auth_sessions(jti);

-- Posting History
CREATE TABLE IF NOT EXISTS posting_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    personnel_id UUID NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
    unit_id UUID NOT NULL REFERENCES units(id) ON DELETE RESTRICT,
    posting_start_date DATE NOT NULL,
    posting_end_date DATE,
    posting_type VARCHAR(80) NOT NULL,
    location_label VARCHAR(150),
    hardship_level INTEGER CHECK (hardship_level BETWEEN 1 AND 5),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_posting_dates CHECK (posting_end_date IS NULL OR posting_end_date >= posting_start_date)
);

CREATE INDEX IF NOT EXISTS idx_posting_personnel ON posting_history(personnel_id);
CREATE INDEX IF NOT EXISTS idx_posting_unit ON posting_history(unit_id);
CREATE INDEX IF NOT EXISTS idx_posting_start ON posting_history(posting_start_date);

-- =============================================================================
-- 2. Operational Data
-- =============================================================================

-- Deployments
CREATE TABLE IF NOT EXISTS deployments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    personnel_id UUID NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
    unit_id UUID NOT NULL REFERENCES units(id) ON DELETE RESTRICT,
    deployment_type VARCHAR(80) NOT NULL,
    location_label VARCHAR(150),
    start_date DATE NOT NULL,
    end_date DATE,
    intensity_level INTEGER CHECK (intensity_level BETWEEN 1 AND 5),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_deployment_dates CHECK (end_date IS NULL OR end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS idx_deployments_personnel ON deployments(personnel_id);
CREATE INDEX IF NOT EXISTS idx_deployments_unit ON deployments(unit_id);
CREATE INDEX IF NOT EXISTS idx_deployments_start ON deployments(start_date);

-- Duties
CREATE TABLE IF NOT EXISTS duties (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    personnel_id UUID NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
    unit_id UUID NOT NULL REFERENCES units(id) ON DELETE RESTRICT,
    duty_date DATE NOT NULL,
    start_at TIMESTAMPTZ NOT NULL,
    end_at TIMESTAMPTZ NOT NULL,
    duty_type VARCHAR(80) NOT NULL,
    shift_type VARCHAR(40) NOT NULL,
    is_night BOOLEAN NOT NULL DEFAULT FALSE,
    hours NUMERIC(6,2) NOT NULL CHECK (hours >= 0),
    deployment_id UUID REFERENCES deployments(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_duty_times CHECK (end_at > start_at)
);

CREATE INDEX IF NOT EXISTS idx_duties_personnel ON duties(personnel_id);
CREATE INDEX IF NOT EXISTS idx_duties_date ON duties(duty_date);
CREATE INDEX IF NOT EXISTS idx_duties_unit ON duties(unit_id);

-- Rest Records
CREATE TABLE IF NOT EXISTS rest_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    personnel_id UUID NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
    record_date DATE NOT NULL,
    rest_hours NUMERIC(6,2),
    rest_gap_hours NUMERIC(6,2),
    source VARCHAR(40) NOT NULL,
    data_quality_status VARCHAR(30) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rest_personnel_date ON rest_records(personnel_id, record_date);

-- Leave Records
CREATE TABLE IF NOT EXISTS leave_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    personnel_id UUID NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
    leave_type VARCHAR(60) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    days NUMERIC(6,2) NOT NULL CHECK (days >= 0),
    status VARCHAR(30) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_leave_dates CHECK (end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS idx_leave_personnel ON leave_records(personnel_id);
CREATE INDEX IF NOT EXISTS idx_leave_dates ON leave_records(start_date, end_date);

-- Training
CREATE TABLE IF NOT EXISTS training (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    personnel_id UUID NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
    training_name VARCHAR(150) NOT NULL,
    training_type VARCHAR(80),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    hours NUMERIC(6,2) CHECK (hours >= 0),
    status VARCHAR(40) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_training_dates CHECK (end_date >= start_date)
);

CREATE INDEX IF NOT EXISTS idx_training_personnel ON training(personnel_id);

-- Staffing
CREATE TABLE IF NOT EXISTS staffing (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unit_id UUID NOT NULL REFERENCES units(id) ON DELETE CASCADE,
    record_date DATE NOT NULL,
    sanctioned_strength INTEGER NOT NULL CHECK (sanctioned_strength >= 0),
    available_strength INTEGER NOT NULL CHECK (available_strength >= 0),
    required_strength INTEGER NOT NULL CHECK (required_strength >= 0),
    coverage_percent NUMERIC(6,2) CHECK (coverage_percent >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_staffing_unit_date ON staffing(unit_id, record_date);

-- =============================================================================
-- 3. Skills
-- =============================================================================

CREATE TABLE IF NOT EXISTS skills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    skill_code VARCHAR(50) UNIQUE NOT NULL,
    skill_name VARCHAR(120) NOT NULL,
    category VARCHAR(80),
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE IF NOT EXISTS person_skills (
    personnel_id UUID NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
    skill_id UUID NOT NULL REFERENCES skills(id) ON DELETE RESTRICT,
    proficiency_level INTEGER NOT NULL CHECK (proficiency_level BETWEEN 1 AND 5),
    valid_from DATE NOT NULL,
    valid_until DATE,
    PRIMARY KEY (personnel_id, skill_id),
    CONSTRAINT chk_skill_validity CHECK (valid_until IS NULL OR valid_until >= valid_from)
);

-- =============================================================================
-- 4. Analytics & Risk Engine Outputs
-- =============================================================================

-- WSI Snapshots
CREATE TABLE IF NOT EXISTS wsi_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    personnel_id UUID NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
    unit_id UUID NOT NULL REFERENCES units(id) ON DELETE RESTRICT,
    snapshot_date DATE NOT NULL,
    wsi_score NUMERIC(6,2) NOT NULL CHECK (wsi_score BETWEEN 0 AND 100),
    d_component NUMERIC(6,2) NOT NULL CHECK (d_component BETWEEN 0 AND 100),
    r_component NUMERIC(6,2) NOT NULL CHECK (r_component BETWEEN 0 AND 100),
    c_component NUMERIC(6,2) NOT NULL CHECK (c_component BETWEEN 0 AND 100),
    n_component NUMERIC(6,2) NOT NULL CHECK (n_component BETWEEN 0 AND 100),
    l_component NUMERIC(6,2) NOT NULL CHECK (l_component BETWEEN 0 AND 100),
    h_component NUMERIC(6,2) NOT NULL CHECK (h_component BETWEEN 0 AND 100),
    s_component NUMERIC(6,2) NOT NULL CHECK (s_component BETWEEN 0 AND 100),
    policy_version VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_wsi_personnel_date ON wsi_snapshots(personnel_id, snapshot_date);
CREATE INDEX IF NOT EXISTS idx_wsi_unit ON wsi_snapshots(unit_id);

-- Baseline Metrics
CREATE TABLE IF NOT EXISTS baseline_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    personnel_id UUID NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
    metric_date DATE NOT NULL,
    metric_name VARCHAR(80) NOT NULL,
    current_value NUMERIC(10,4),
    median_value NUMERIC(10,4),
    mad_value NUMERIC(10,4),
    z_score NUMERIC(10,4),
    ewma_value NUMERIC(10,4),
    history_count INTEGER NOT NULL CHECK (history_count >= 0),
    baseline_status VARCHAR(30) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_baseline_personnel_date ON baseline_metrics(personnel_id, metric_date);

-- Anomaly Events
CREATE TABLE IF NOT EXISTS anomaly_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    personnel_id UUID NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
    unit_id UUID NOT NULL REFERENCES units(id) ON DELETE RESTRICT,
    event_date DATE NOT NULL,
    algorithm VARCHAR(80) NOT NULL,
    anomaly_score NUMERIC(10,5),
    is_anomaly BOOLEAN NOT NULL,
    context_tag VARCHAR(80),
    feature_set_version VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_anomaly_personnel_date ON anomaly_events(personnel_id, event_date);
CREATE INDEX IF NOT EXISTS idx_anomaly_unit ON anomaly_events(unit_id);

-- Model Outputs (Risk Levels: LOW / MEDIUM / HIGH)
CREATE TABLE IF NOT EXISTS model_outputs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    personnel_id UUID NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
    prediction_date DATE NOT NULL,
    target_name VARCHAR(120) NOT NULL,
    hr_probability NUMERIC(7,6) CHECK (hr_probability BETWEEN 0 AND 1),
    wellbeing_probability NUMERIC(7,6) CHECK (wellbeing_probability BETWEEN 0 AND 1),
    combined_probability NUMERIC(7,6) CHECK (combined_probability BETWEEN 0 AND 1),
    risk_score NUMERIC(6,2) NOT NULL CHECK (risk_score BETWEEN 0 AND 100),
    risk_level VARCHAR(20) NOT NULL CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH')),
    predicted_class INTEGER CHECK (predicted_class IN (0, 1)),
    model_name VARCHAR(120) NOT NULL,
    model_version VARCHAR(50) NOT NULL,
    feature_set_version VARCHAR(50) NOT NULL,
    training_data_version VARCHAR(50),
    data_completeness NUMERIC(6,2) CHECK (data_completeness BETWEEN 0 AND 100),
    explanation_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_model_personnel_date ON model_outputs(personnel_id, prediction_date);
CREATE INDEX IF NOT EXISTS idx_model_risk_level ON model_outputs(risk_level);

-- =============================================================================
-- 5. Private Wellbeing Vault (Strict Privacy Separation)
-- =============================================================================

-- Wellbeing Consent
CREATE TABLE IF NOT EXISTS wellbeing_consent (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    personnel_id UUID NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
    consent_version VARCHAR(50) NOT NULL,
    purpose VARCHAR(150) NOT NULL,
    status VARCHAR(30) NOT NULL,
    consented_at TIMESTAMPTZ,
    withdrawn_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_consent_personnel ON wellbeing_consent(personnel_id);

-- Wellbeing Private (Raw Answers — Personnel Only)
CREATE TABLE IF NOT EXISTS wellbeing_private (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    personnel_id UUID NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
    assessment_date DATE NOT NULL,
    instrument_name VARCHAR(100) NOT NULL,
    instrument_version VARCHAR(50) NOT NULL,
    answers_json JSONB NOT NULL,
    score_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_wb_private_personnel ON wellbeing_private(personnel_id);

-- Wellbeing Results (Authorized Welfare View)
CREATE TABLE IF NOT EXISTS wellbeing_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wellbeing_private_id UUID NOT NULL REFERENCES wellbeing_private(id) ON DELETE CASCADE,
    personnel_id UUID NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
    instrument_name VARCHAR(100) NOT NULL,
    assessment_date DATE NOT NULL,
    score_summary_json JSONB NOT NULL,
    category_label VARCHAR(80),
    trend_label VARCHAR(40),
    model_version VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_wb_results_personnel ON wellbeing_results(personnel_id);

-- Support Requests
CREATE TABLE IF NOT EXISTS support_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    personnel_id UUID NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
    request_type VARCHAR(80) NOT NULL,
    status VARCHAR(40) NOT NULL,
    priority VARCHAR(30) NOT NULL,
    assigned_to_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    request_text TEXT,
    follow_up_date DATE,
    closed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_support_personnel ON support_requests(personnel_id);
CREATE INDEX IF NOT EXISTS idx_support_status ON support_requests(status);

-- =============================================================================
-- 6. Decision Support, Scenarios, Outcomes & Alerts
-- =============================================================================

CREATE TABLE IF NOT EXISTS roster_scenarios (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    unit_id UUID NOT NULL REFERENCES units(id) ON DELETE RESTRICT,
    created_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    scenario_name VARCHAR(150) NOT NULL,
    status VARCHAR(30) NOT NULL,
    current_snapshot_json JSONB NOT NULL,
    proposed_snapshot_json JSONB NOT NULL,
    before_metrics_json JSONB NOT NULL,
    after_metrics_json JSONB NOT NULL,
    constraint_results_json JSONB NOT NULL,
    optimizer_method VARCHAR(50) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS scenario_changes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id UUID NOT NULL REFERENCES roster_scenarios(id) ON DELETE CASCADE,
    personnel_id UUID NOT NULL REFERENCES personnel(id) ON DELETE CASCADE,
    change_type VARCHAR(80) NOT NULL,
    from_value JSONB,
    to_value JSONB,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS approvals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id UUID NOT NULL REFERENCES roster_scenarios(id) ON DELETE CASCADE,
    actor_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    decision VARCHAR(20) NOT NULL CHECK (decision IN ('ACCEPT', 'MODIFY', 'REJECT')),
    reason TEXT NOT NULL,
    decided_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS outcomes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    scenario_id UUID NOT NULL REFERENCES roster_scenarios(id) ON DELETE CASCADE,
    recorded_by_user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    observation_date DATE NOT NULL,
    observed_metrics_json JSONB NOT NULL,
    wsi_change NUMERIC(10,4),
    operational_event_observed BOOLEAN,
    notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    personnel_id UUID REFERENCES personnel(id) ON DELETE CASCADE,
    unit_id UUID NOT NULL REFERENCES units(id) ON DELETE RESTRICT,
    alert_type VARCHAR(80) NOT NULL,
    severity VARCHAR(20) NOT NULL,
    source_type VARCHAR(50) NOT NULL,
    source_id UUID,
    status VARCHAR(30) NOT NULL,
    dedupe_key VARCHAR(255) UNIQUE,
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_alerts_unit ON alerts(unit_id);
CREATE INDEX IF NOT EXISTS idx_alerts_personnel ON alerts(personnel_id);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);

-- =============================================================================
-- 7. Audit & Policy
-- =============================================================================

CREATE TABLE IF NOT EXISTS audit_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    actor_role VARCHAR(30),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(80) NOT NULL,
    resource_id UUID,
    result VARCHAR(30) NOT NULL,
    reason TEXT,
    metadata_json JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_events(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_events(actor_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_resource ON audit_events(resource_type, resource_id);

CREATE TABLE IF NOT EXISTS policy_config (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_key VARCHAR(100) NOT NULL,
    policy_value_json JSONB NOT NULL,
    version VARCHAR(50) NOT NULL,
    effective_from TIMESTAMPTZ NOT NULL,
    effective_until TIMESTAMPTZ,
    updated_by_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_policy_key ON policy_config(policy_key);
