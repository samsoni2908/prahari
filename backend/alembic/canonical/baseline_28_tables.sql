CREATE TABLE public.alerts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    personnel_id uuid,
    unit_id uuid NOT NULL,
    alert_type character varying(80) NOT NULL,
    severity character varying(20) NOT NULL,
    source_type character varying(50) NOT NULL,
    source_id uuid,
    status character varying(30) NOT NULL,
    dedupe_key character varying(255),
    message text NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    resolved_at timestamp with time zone
);



CREATE TABLE public.anomaly_events (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    personnel_id uuid NOT NULL,
    unit_id uuid NOT NULL,
    event_date date NOT NULL,
    algorithm character varying(80) NOT NULL,
    anomaly_score numeric(10,5),
    is_anomaly boolean NOT NULL,
    context_tag character varying(80),
    feature_set_version character varying(50) NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);



CREATE TABLE public.approvals (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    scenario_id uuid NOT NULL,
    actor_user_id uuid NOT NULL,
    decision character varying(20) NOT NULL,
    reason text NOT NULL,
    decided_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT approvals_decision_check CHECK (((decision)::text = ANY ((ARRAY['ACCEPT'::character varying, 'MODIFY'::character varying, 'REJECT'::character varying])::text[])))
);



CREATE TABLE public.audit_events (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    actor_user_id uuid,
    actor_role character varying(30),
    action character varying(100) NOT NULL,
    resource_type character varying(80) NOT NULL,
    resource_id uuid,
    result character varying(30) NOT NULL,
    reason text,
    metadata_json jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);



CREATE TABLE public.auth_sessions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id uuid NOT NULL,
    jti uuid NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_seen_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    revoked_at timestamp with time zone,
    revoke_reason character varying(80)
);



CREATE TABLE public.baseline_metrics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    personnel_id uuid NOT NULL,
    metric_date date NOT NULL,
    metric_name character varying(80) NOT NULL,
    current_value numeric(10,4),
    median_value numeric(10,4),
    mad_value numeric(10,4),
    z_score numeric(10,4),
    ewma_value numeric(10,4),
    history_count integer NOT NULL,
    baseline_status character varying(30) NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT baseline_metrics_history_count_check CHECK ((history_count >= 0))
);



CREATE TABLE public.deployments (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    personnel_id uuid NOT NULL,
    unit_id uuid NOT NULL,
    deployment_type character varying(80) NOT NULL,
    location_label character varying(150),
    start_date date NOT NULL,
    end_date date,
    intensity_level integer,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_deployment_dates CHECK (((end_date IS NULL) OR (end_date >= start_date))),
    CONSTRAINT deployments_intensity_level_check CHECK (((intensity_level >= 1) AND (intensity_level <= 5)))
);



CREATE TABLE public.duties (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    personnel_id uuid NOT NULL,
    unit_id uuid NOT NULL,
    duty_date date NOT NULL,
    start_at timestamp with time zone NOT NULL,
    end_at timestamp with time zone NOT NULL,
    duty_type character varying(80) NOT NULL,
    shift_type character varying(40) NOT NULL,
    is_night boolean DEFAULT false NOT NULL,
    hours numeric(6,2) NOT NULL,
    deployment_id uuid,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_duty_times CHECK ((end_at > start_at)),
    CONSTRAINT duties_hours_check CHECK ((hours >= (0)::numeric))
);



CREATE TABLE public.leave_records (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    personnel_id uuid NOT NULL,
    leave_type character varying(60) NOT NULL,
    start_date date NOT NULL,
    end_date date NOT NULL,
    days numeric(6,2) NOT NULL,
    status character varying(30) NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_leave_dates CHECK ((end_date >= start_date)),
    CONSTRAINT leave_records_days_check CHECK ((days >= (0)::numeric))
);



CREATE TABLE public.model_outputs (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    personnel_id uuid NOT NULL,
    prediction_date date NOT NULL,
    target_name character varying(120) NOT NULL,
    hr_probability numeric(7,6),
    wellbeing_probability numeric(7,6),
    combined_probability numeric(7,6),
    risk_score numeric(6,2) NOT NULL,
    risk_level character varying(20) NOT NULL,
    predicted_class integer,
    model_name character varying(120) NOT NULL,
    model_version character varying(50) NOT NULL,
    feature_set_version character varying(50) NOT NULL,
    training_data_version character varying(50),
    data_completeness numeric(6,2),
    explanation_json jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT model_outputs_combined_probability_check CHECK (((combined_probability >= (0)::numeric) AND (combined_probability <= (1)::numeric))),
    CONSTRAINT model_outputs_data_completeness_check CHECK (((data_completeness >= (0)::numeric) AND (data_completeness <= (100)::numeric))),
    CONSTRAINT model_outputs_hr_probability_check CHECK (((hr_probability >= (0)::numeric) AND (hr_probability <= (1)::numeric))),
    CONSTRAINT model_outputs_predicted_class_check CHECK ((predicted_class = ANY (ARRAY[0, 1]))),
    CONSTRAINT model_outputs_risk_level_check CHECK (((risk_level)::text = ANY ((ARRAY['LOW'::character varying, 'MEDIUM'::character varying, 'HIGH'::character varying])::text[]))),
    CONSTRAINT model_outputs_risk_score_check CHECK (((risk_score >= (0)::numeric) AND (risk_score <= (100)::numeric))),
    CONSTRAINT model_outputs_wellbeing_probability_check CHECK (((wellbeing_probability >= (0)::numeric) AND (wellbeing_probability <= (1)::numeric)))
);



CREATE TABLE public.outcomes (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    scenario_id uuid NOT NULL,
    recorded_by_user_id uuid NOT NULL,
    observation_date date NOT NULL,
    observed_metrics_json jsonb NOT NULL,
    wsi_change numeric(10,4),
    operational_event_observed boolean,
    notes text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);



CREATE TABLE public.person_skills (
    personnel_id uuid NOT NULL,
    skill_id uuid NOT NULL,
    proficiency_level integer NOT NULL,
    valid_from date NOT NULL,
    valid_until date,
    CONSTRAINT chk_skill_validity CHECK (((valid_until IS NULL) OR (valid_until >= valid_from))),
    CONSTRAINT person_skills_proficiency_level_check CHECK (((proficiency_level >= 1) AND (proficiency_level <= 5)))
);



CREATE TABLE public.personnel (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    personnel_code character varying(50) NOT NULL,
    pseudo_id character varying(50) NOT NULL,
    full_name character varying(150) NOT NULL,
    unit_id uuid NOT NULL,
    rank_or_grade character varying(80) NOT NULL,
    role_title character varying(100) NOT NULL,
    status character varying(40) NOT NULL,
    joining_date date,
    service_years numeric(5,2),
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT personnel_service_years_check CHECK ((service_years >= (0)::numeric))
);



CREATE TABLE public.policy_config (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    policy_key character varying(100) NOT NULL,
    policy_value_json jsonb NOT NULL,
    version character varying(50) NOT NULL,
    effective_from timestamp with time zone NOT NULL,
    effective_until timestamp with time zone,
    updated_by_user_id uuid,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);



CREATE TABLE public.posting_history (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    personnel_id uuid NOT NULL,
    unit_id uuid NOT NULL,
    posting_start_date date NOT NULL,
    posting_end_date date,
    posting_type character varying(80) NOT NULL,
    location_label character varying(150),
    hardship_level integer,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_posting_dates CHECK (((posting_end_date IS NULL) OR (posting_end_date >= posting_start_date))),
    CONSTRAINT posting_history_hardship_level_check CHECK (((hardship_level >= 1) AND (hardship_level <= 5)))
);



CREATE TABLE public.rest_records (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    personnel_id uuid NOT NULL,
    record_date date NOT NULL,
    rest_hours numeric(6,2),
    rest_gap_hours numeric(6,2),
    source character varying(40) NOT NULL,
    data_quality_status character varying(30) NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);



CREATE TABLE public.roster_scenarios (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    unit_id uuid NOT NULL,
    created_by_user_id uuid NOT NULL,
    scenario_name character varying(150) NOT NULL,
    status character varying(30) NOT NULL,
    current_snapshot_json jsonb NOT NULL,
    proposed_snapshot_json jsonb NOT NULL,
    before_metrics_json jsonb NOT NULL,
    after_metrics_json jsonb NOT NULL,
    constraint_results_json jsonb NOT NULL,
    optimizer_method character varying(50) NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);



CREATE TABLE public.scenario_changes (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    scenario_id uuid NOT NULL,
    personnel_id uuid NOT NULL,
    change_type character varying(80) NOT NULL,
    from_value jsonb,
    to_value jsonb,
    reason text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);



CREATE TABLE public.skills (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    skill_code character varying(50) NOT NULL,
    skill_name character varying(120) NOT NULL,
    category character varying(80),
    is_active boolean DEFAULT true NOT NULL
);



CREATE TABLE public.staffing (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    unit_id uuid NOT NULL,
    record_date date NOT NULL,
    sanctioned_strength integer NOT NULL,
    available_strength integer NOT NULL,
    required_strength integer NOT NULL,
    coverage_percent numeric(6,2),
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT staffing_available_strength_check CHECK ((available_strength >= 0)),
    CONSTRAINT staffing_coverage_percent_check CHECK ((coverage_percent >= (0)::numeric)),
    CONSTRAINT staffing_required_strength_check CHECK ((required_strength >= 0)),
    CONSTRAINT staffing_sanctioned_strength_check CHECK ((sanctioned_strength >= 0))
);



CREATE TABLE public.support_requests (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    personnel_id uuid NOT NULL,
    request_type character varying(80) NOT NULL,
    status character varying(40) NOT NULL,
    priority character varying(30) NOT NULL,
    assigned_to_user_id uuid,
    request_text text,
    follow_up_date date,
    closed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);



CREATE TABLE public.training (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    personnel_id uuid NOT NULL,
    training_name character varying(150) NOT NULL,
    training_type character varying(80),
    start_date date NOT NULL,
    end_date date NOT NULL,
    hours numeric(6,2),
    status character varying(40) NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT chk_training_dates CHECK ((end_date >= start_date)),
    CONSTRAINT training_hours_check CHECK ((hours >= (0)::numeric))
);



CREATE TABLE public.units (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    unit_code character varying(50) NOT NULL,
    unit_name character varying(150) NOT NULL,
    unit_type character varying(80) NOT NULL,
    parent_unit_id uuid,
    location_label character varying(150),
    sanctioned_strength integer NOT NULL,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT units_sanctioned_strength_check CHECK ((sanctioned_strength >= 0))
);



CREATE TABLE public.users (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    username character varying(100) NOT NULL,
    password_hash text NOT NULL,
    role character varying(30) NOT NULL,
    personnel_id uuid,
    unit_id uuid,
    is_active boolean DEFAULT true NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT users_role_check CHECK (((role)::text = ANY ((ARRAY['PERSONNEL'::character varying, 'COMMANDER'::character varying, 'WELFARE_OFFICER'::character varying, 'ADMIN'::character varying])::text[])))
);



CREATE TABLE public.wellbeing_consent (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    personnel_id uuid NOT NULL,
    consent_version character varying(50) NOT NULL,
    purpose character varying(150) NOT NULL,
    status character varying(30) NOT NULL,
    consented_at timestamp with time zone,
    withdrawn_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);



CREATE TABLE public.wellbeing_private (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    personnel_id uuid NOT NULL,
    assessment_date date NOT NULL,
    instrument_name character varying(100) NOT NULL,
    instrument_version character varying(50) NOT NULL,
    answers_json jsonb NOT NULL,
    score_json jsonb,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);



CREATE TABLE public.wellbeing_results (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    wellbeing_private_id uuid NOT NULL,
    personnel_id uuid NOT NULL,
    instrument_name character varying(100) NOT NULL,
    assessment_date date NOT NULL,
    score_summary_json jsonb NOT NULL,
    category_label character varying(80),
    trend_label character varying(40),
    model_version character varying(50),
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);



CREATE TABLE public.wsi_snapshots (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    personnel_id uuid NOT NULL,
    unit_id uuid NOT NULL,
    snapshot_date date NOT NULL,
    wsi_score numeric(6,2) NOT NULL,
    d_component numeric(6,2) NOT NULL,
    r_component numeric(6,2) NOT NULL,
    c_component numeric(6,2) NOT NULL,
    n_component numeric(6,2) NOT NULL,
    l_component numeric(6,2) NOT NULL,
    h_component numeric(6,2) NOT NULL,
    s_component numeric(6,2) NOT NULL,
    policy_version character varying(50) NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT wsi_snapshots_c_component_check CHECK (((c_component >= (0)::numeric) AND (c_component <= (100)::numeric))),
    CONSTRAINT wsi_snapshots_d_component_check CHECK (((d_component >= (0)::numeric) AND (d_component <= (100)::numeric))),
    CONSTRAINT wsi_snapshots_h_component_check CHECK (((h_component >= (0)::numeric) AND (h_component <= (100)::numeric))),
    CONSTRAINT wsi_snapshots_l_component_check CHECK (((l_component >= (0)::numeric) AND (l_component <= (100)::numeric))),
    CONSTRAINT wsi_snapshots_n_component_check CHECK (((n_component >= (0)::numeric) AND (n_component <= (100)::numeric))),
    CONSTRAINT wsi_snapshots_r_component_check CHECK (((r_component >= (0)::numeric) AND (r_component <= (100)::numeric))),
    CONSTRAINT wsi_snapshots_s_component_check CHECK (((s_component >= (0)::numeric) AND (s_component <= (100)::numeric))),
    CONSTRAINT wsi_snapshots_wsi_score_check CHECK (((wsi_score >= (0)::numeric) AND (wsi_score <= (100)::numeric)))
);



ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_dedupe_key_key UNIQUE (dedupe_key);



ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_pkey PRIMARY KEY (id);



ALTER TABLE ONLY public.anomaly_events
    ADD CONSTRAINT anomaly_events_pkey PRIMARY KEY (id);



ALTER TABLE ONLY public.approvals
    ADD CONSTRAINT approvals_pkey PRIMARY KEY (id);



ALTER TABLE ONLY public.audit_events
    ADD CONSTRAINT audit_events_pkey PRIMARY KEY (id);



ALTER TABLE ONLY public.auth_sessions
    ADD CONSTRAINT auth_sessions_jti_key UNIQUE (jti);



ALTER TABLE ONLY public.auth_sessions
    ADD CONSTRAINT auth_sessions_pkey PRIMARY KEY (id);



ALTER TABLE ONLY public.baseline_metrics
    ADD CONSTRAINT baseline_metrics_pkey PRIMARY KEY (id);



ALTER TABLE ONLY public.deployments
    ADD CONSTRAINT deployments_pkey PRIMARY KEY (id);



ALTER TABLE ONLY public.duties
    ADD CONSTRAINT duties_pkey PRIMARY KEY (id);



ALTER TABLE ONLY public.leave_records
    ADD CONSTRAINT leave_records_pkey PRIMARY KEY (id);



ALTER TABLE ONLY public.model_outputs
    ADD CONSTRAINT model_outputs_pkey PRIMARY KEY (id);



ALTER TABLE ONLY public.outcomes
    ADD CONSTRAINT outcomes_pkey PRIMARY KEY (id);



ALTER TABLE ONLY public.person_skills
    ADD CONSTRAINT person_skills_pkey PRIMARY KEY (personnel_id, skill_id);



ALTER TABLE ONLY public.personnel
    ADD CONSTRAINT personnel_personnel_code_key UNIQUE (personnel_code);



ALTER TABLE ONLY public.personnel
    ADD CONSTRAINT personnel_pkey PRIMARY KEY (id);



ALTER TABLE ONLY public.personnel
    ADD CONSTRAINT personnel_pseudo_id_key UNIQUE (pseudo_id);



ALTER TABLE ONLY public.policy_config
    ADD CONSTRAINT policy_config_pkey PRIMARY KEY (id);



ALTER TABLE ONLY public.posting_history
    ADD CONSTRAINT posting_history_pkey PRIMARY KEY (id);



ALTER TABLE ONLY public.rest_records
    ADD CONSTRAINT rest_records_pkey PRIMARY KEY (id);



ALTER TABLE ONLY public.roster_scenarios
    ADD CONSTRAINT roster_scenarios_pkey PRIMARY KEY (id);



ALTER TABLE ONLY public.scenario_changes
    ADD CONSTRAINT scenario_changes_pkey PRIMARY KEY (id);



ALTER TABLE ONLY public.skills
    ADD CONSTRAINT skills_pkey PRIMARY KEY (id);



ALTER TABLE ONLY public.skills
    ADD CONSTRAINT skills_skill_code_key UNIQUE (skill_code);



ALTER TABLE ONLY public.staffing
    ADD CONSTRAINT staffing_pkey PRIMARY KEY (id);



ALTER TABLE ONLY public.support_requests
    ADD CONSTRAINT support_requests_pkey PRIMARY KEY (id);



ALTER TABLE ONLY public.training
    ADD CONSTRAINT training_pkey PRIMARY KEY (id);



ALTER TABLE ONLY public.units
    ADD CONSTRAINT units_pkey PRIMARY KEY (id);



ALTER TABLE ONLY public.units
    ADD CONSTRAINT units_unit_code_key UNIQUE (unit_code);



ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);



ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_username_key UNIQUE (username);



ALTER TABLE ONLY public.wellbeing_consent
    ADD CONSTRAINT wellbeing_consent_pkey PRIMARY KEY (id);



ALTER TABLE ONLY public.wellbeing_private
    ADD CONSTRAINT wellbeing_private_pkey PRIMARY KEY (id);



ALTER TABLE ONLY public.wellbeing_results
    ADD CONSTRAINT wellbeing_results_pkey PRIMARY KEY (id);



ALTER TABLE ONLY public.wsi_snapshots
    ADD CONSTRAINT wsi_snapshots_pkey PRIMARY KEY (id);



CREATE INDEX idx_alerts_personnel ON public.alerts USING btree (personnel_id);



CREATE INDEX idx_alerts_status ON public.alerts USING btree (status);



CREATE INDEX idx_alerts_unit ON public.alerts USING btree (unit_id);



CREATE INDEX idx_anomaly_personnel_date ON public.anomaly_events USING btree (personnel_id, event_date);



CREATE INDEX idx_anomaly_unit ON public.anomaly_events USING btree (unit_id);



CREATE INDEX idx_audit_actor ON public.audit_events USING btree (actor_user_id);



CREATE INDEX idx_audit_created ON public.audit_events USING btree (created_at);



CREATE INDEX idx_audit_resource ON public.audit_events USING btree (resource_type, resource_id);



CREATE INDEX idx_baseline_personnel_date ON public.baseline_metrics USING btree (personnel_id, metric_date);



CREATE INDEX idx_consent_personnel ON public.wellbeing_consent USING btree (personnel_id);



CREATE INDEX idx_deployments_personnel ON public.deployments USING btree (personnel_id);



CREATE INDEX idx_deployments_start ON public.deployments USING btree (start_date);



CREATE INDEX idx_deployments_unit ON public.deployments USING btree (unit_id);



CREATE INDEX idx_duties_date ON public.duties USING btree (duty_date);



CREATE INDEX idx_duties_personnel ON public.duties USING btree (personnel_id);



CREATE INDEX idx_duties_unit ON public.duties USING btree (unit_id);



CREATE INDEX idx_leave_dates ON public.leave_records USING btree (start_date, end_date);



CREATE INDEX idx_leave_personnel ON public.leave_records USING btree (personnel_id);



CREATE INDEX idx_model_personnel_date ON public.model_outputs USING btree (personnel_id, prediction_date);



CREATE INDEX idx_model_risk_level ON public.model_outputs USING btree (risk_level);



CREATE INDEX idx_personnel_code ON public.personnel USING btree (personnel_code);



CREATE INDEX idx_personnel_name ON public.personnel USING btree (full_name);



CREATE INDEX idx_personnel_pseudo ON public.personnel USING btree (pseudo_id);



CREATE INDEX idx_personnel_status ON public.personnel USING btree (status);



CREATE INDEX idx_personnel_unit ON public.personnel USING btree (unit_id);



CREATE INDEX idx_policy_key ON public.policy_config USING btree (policy_key);



CREATE INDEX idx_posting_personnel ON public.posting_history USING btree (personnel_id);



CREATE INDEX idx_posting_start ON public.posting_history USING btree (posting_start_date);



CREATE INDEX idx_posting_unit ON public.posting_history USING btree (unit_id);



CREATE INDEX idx_rest_personnel_date ON public.rest_records USING btree (personnel_id, record_date);



CREATE INDEX idx_sessions_expires ON public.auth_sessions USING btree (expires_at);



CREATE INDEX idx_sessions_jti ON public.auth_sessions USING btree (jti);



CREATE INDEX idx_sessions_user_revoked ON public.auth_sessions USING btree (user_id, revoked_at);



CREATE INDEX idx_staffing_unit_date ON public.staffing USING btree (unit_id, record_date);



CREATE INDEX idx_support_personnel ON public.support_requests USING btree (personnel_id);



CREATE INDEX idx_support_status ON public.support_requests USING btree (status);



CREATE INDEX idx_training_personnel ON public.training USING btree (personnel_id);



CREATE INDEX idx_units_active ON public.units USING btree (is_active);



CREATE INDEX idx_units_code ON public.units USING btree (unit_code);



CREATE INDEX idx_units_parent ON public.units USING btree (parent_unit_id);



CREATE INDEX idx_users_active ON public.users USING btree (is_active);



CREATE INDEX idx_users_personnel ON public.users USING btree (personnel_id);



CREATE INDEX idx_users_role ON public.users USING btree (role);



CREATE INDEX idx_users_unit ON public.users USING btree (unit_id);



CREATE INDEX idx_users_username ON public.users USING btree (username);



CREATE INDEX idx_wb_private_personnel ON public.wellbeing_private USING btree (personnel_id);



CREATE INDEX idx_wb_results_personnel ON public.wellbeing_results USING btree (personnel_id);



CREATE INDEX idx_wsi_personnel_date ON public.wsi_snapshots USING btree (personnel_id, snapshot_date);



CREATE INDEX idx_wsi_unit ON public.wsi_snapshots USING btree (unit_id);



ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_personnel_id_fkey FOREIGN KEY (personnel_id) REFERENCES public.personnel(id) ON DELETE CASCADE;



ALTER TABLE ONLY public.alerts
    ADD CONSTRAINT alerts_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES public.units(id) ON DELETE RESTRICT;



ALTER TABLE ONLY public.anomaly_events
    ADD CONSTRAINT anomaly_events_personnel_id_fkey FOREIGN KEY (personnel_id) REFERENCES public.personnel(id) ON DELETE CASCADE;



ALTER TABLE ONLY public.anomaly_events
    ADD CONSTRAINT anomaly_events_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES public.units(id) ON DELETE RESTRICT;



ALTER TABLE ONLY public.approvals
    ADD CONSTRAINT approvals_actor_user_id_fkey FOREIGN KEY (actor_user_id) REFERENCES public.users(id) ON DELETE RESTRICT;



ALTER TABLE ONLY public.approvals
    ADD CONSTRAINT approvals_scenario_id_fkey FOREIGN KEY (scenario_id) REFERENCES public.roster_scenarios(id) ON DELETE CASCADE;



ALTER TABLE ONLY public.audit_events
    ADD CONSTRAINT audit_events_actor_user_id_fkey FOREIGN KEY (actor_user_id) REFERENCES public.users(id) ON DELETE SET NULL;



ALTER TABLE ONLY public.auth_sessions
    ADD CONSTRAINT auth_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;



ALTER TABLE ONLY public.baseline_metrics
    ADD CONSTRAINT baseline_metrics_personnel_id_fkey FOREIGN KEY (personnel_id) REFERENCES public.personnel(id) ON DELETE CASCADE;



ALTER TABLE ONLY public.deployments
    ADD CONSTRAINT deployments_personnel_id_fkey FOREIGN KEY (personnel_id) REFERENCES public.personnel(id) ON DELETE CASCADE;



ALTER TABLE ONLY public.deployments
    ADD CONSTRAINT deployments_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES public.units(id) ON DELETE RESTRICT;



ALTER TABLE ONLY public.duties
    ADD CONSTRAINT duties_deployment_id_fkey FOREIGN KEY (deployment_id) REFERENCES public.deployments(id) ON DELETE SET NULL;



ALTER TABLE ONLY public.duties
    ADD CONSTRAINT duties_personnel_id_fkey FOREIGN KEY (personnel_id) REFERENCES public.personnel(id) ON DELETE CASCADE;



ALTER TABLE ONLY public.duties
    ADD CONSTRAINT duties_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES public.units(id) ON DELETE RESTRICT;



ALTER TABLE ONLY public.leave_records
    ADD CONSTRAINT leave_records_personnel_id_fkey FOREIGN KEY (personnel_id) REFERENCES public.personnel(id) ON DELETE CASCADE;



ALTER TABLE ONLY public.model_outputs
    ADD CONSTRAINT model_outputs_personnel_id_fkey FOREIGN KEY (personnel_id) REFERENCES public.personnel(id) ON DELETE CASCADE;



ALTER TABLE ONLY public.outcomes
    ADD CONSTRAINT outcomes_recorded_by_user_id_fkey FOREIGN KEY (recorded_by_user_id) REFERENCES public.users(id) ON DELETE RESTRICT;



ALTER TABLE ONLY public.outcomes
    ADD CONSTRAINT outcomes_scenario_id_fkey FOREIGN KEY (scenario_id) REFERENCES public.roster_scenarios(id) ON DELETE CASCADE;



ALTER TABLE ONLY public.person_skills
    ADD CONSTRAINT person_skills_personnel_id_fkey FOREIGN KEY (personnel_id) REFERENCES public.personnel(id) ON DELETE CASCADE;



ALTER TABLE ONLY public.person_skills
    ADD CONSTRAINT person_skills_skill_id_fkey FOREIGN KEY (skill_id) REFERENCES public.skills(id) ON DELETE RESTRICT;



ALTER TABLE ONLY public.personnel
    ADD CONSTRAINT personnel_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES public.units(id) ON DELETE RESTRICT;



ALTER TABLE ONLY public.policy_config
    ADD CONSTRAINT policy_config_updated_by_user_id_fkey FOREIGN KEY (updated_by_user_id) REFERENCES public.users(id) ON DELETE SET NULL;



ALTER TABLE ONLY public.posting_history
    ADD CONSTRAINT posting_history_personnel_id_fkey FOREIGN KEY (personnel_id) REFERENCES public.personnel(id) ON DELETE CASCADE;



ALTER TABLE ONLY public.posting_history
    ADD CONSTRAINT posting_history_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES public.units(id) ON DELETE RESTRICT;



ALTER TABLE ONLY public.rest_records
    ADD CONSTRAINT rest_records_personnel_id_fkey FOREIGN KEY (personnel_id) REFERENCES public.personnel(id) ON DELETE CASCADE;



ALTER TABLE ONLY public.roster_scenarios
    ADD CONSTRAINT roster_scenarios_created_by_user_id_fkey FOREIGN KEY (created_by_user_id) REFERENCES public.users(id) ON DELETE RESTRICT;



ALTER TABLE ONLY public.roster_scenarios
    ADD CONSTRAINT roster_scenarios_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES public.units(id) ON DELETE RESTRICT;



ALTER TABLE ONLY public.scenario_changes
    ADD CONSTRAINT scenario_changes_personnel_id_fkey FOREIGN KEY (personnel_id) REFERENCES public.personnel(id) ON DELETE CASCADE;



ALTER TABLE ONLY public.scenario_changes
    ADD CONSTRAINT scenario_changes_scenario_id_fkey FOREIGN KEY (scenario_id) REFERENCES public.roster_scenarios(id) ON DELETE CASCADE;



ALTER TABLE ONLY public.staffing
    ADD CONSTRAINT staffing_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES public.units(id) ON DELETE CASCADE;



ALTER TABLE ONLY public.support_requests
    ADD CONSTRAINT support_requests_assigned_to_user_id_fkey FOREIGN KEY (assigned_to_user_id) REFERENCES public.users(id) ON DELETE SET NULL;



ALTER TABLE ONLY public.support_requests
    ADD CONSTRAINT support_requests_personnel_id_fkey FOREIGN KEY (personnel_id) REFERENCES public.personnel(id) ON DELETE CASCADE;



ALTER TABLE ONLY public.training
    ADD CONSTRAINT training_personnel_id_fkey FOREIGN KEY (personnel_id) REFERENCES public.personnel(id) ON DELETE CASCADE;



ALTER TABLE ONLY public.units
    ADD CONSTRAINT units_parent_unit_id_fkey FOREIGN KEY (parent_unit_id) REFERENCES public.units(id) ON DELETE SET NULL;



ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_personnel_id_fkey FOREIGN KEY (personnel_id) REFERENCES public.personnel(id) ON DELETE SET NULL;



ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES public.units(id) ON DELETE SET NULL;



ALTER TABLE ONLY public.wellbeing_consent
    ADD CONSTRAINT wellbeing_consent_personnel_id_fkey FOREIGN KEY (personnel_id) REFERENCES public.personnel(id) ON DELETE CASCADE;



ALTER TABLE ONLY public.wellbeing_private
    ADD CONSTRAINT wellbeing_private_personnel_id_fkey FOREIGN KEY (personnel_id) REFERENCES public.personnel(id) ON DELETE CASCADE;



ALTER TABLE ONLY public.wellbeing_results
    ADD CONSTRAINT wellbeing_results_personnel_id_fkey FOREIGN KEY (personnel_id) REFERENCES public.personnel(id) ON DELETE CASCADE;



ALTER TABLE ONLY public.wellbeing_results
    ADD CONSTRAINT wellbeing_results_wellbeing_private_id_fkey FOREIGN KEY (wellbeing_private_id) REFERENCES public.wellbeing_private(id) ON DELETE CASCADE;



ALTER TABLE ONLY public.wsi_snapshots
    ADD CONSTRAINT wsi_snapshots_personnel_id_fkey FOREIGN KEY (personnel_id) REFERENCES public.personnel(id) ON DELETE CASCADE;



ALTER TABLE ONLY public.wsi_snapshots
    ADD CONSTRAINT wsi_snapshots_unit_id_fkey FOREIGN KEY (unit_id) REFERENCES public.units(id) ON DELETE RESTRICT;
