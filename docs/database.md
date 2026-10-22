# PRAHARI — Database, Migration and Import Contract

Status: The approved schema migrations are implemented in the single backend canonical lineage. Fresh/upgrade behavior, ORM parity and retained-data preservation are covered by the repository's migration and integration tests. Historical generated audit reports are non-authoritative and excluded from the release repository. [architecture.md](architecture.md) owns API/state machines, BALANCE and VERIFY; [rules.md](rules.md) owns disclosure/retention; [ml.md](ml.md) owns analytics.

The locked Stage-1 delta is limited to: new `welfare_case_actions`; new `notifications`; nullable `support_requests.request_key_hash` and `support_requests.request_hash` plus the approved partial unique index; and nullable `auth_sessions.refresh_secret_hash`. Existing rows remain NULL for new nullable fields with no backfill. No other table or column in this document is automatically approved for migration.

## 1. Schema conventions and migration authority

PostgreSQL 16. UUID primary keys generated server-side; timestamps are UTC TIMESTAMPTZ; business dates DATE. Use NOT NULL unless `?` is shown below. `id`, `created_at` are implicit on every entity except explicitly composite-key tables. Mutable entities also have `updated_at` and integer `revision` starting at 1. Text identifiers are bounded in API schemas (code 80, name 150, short label 120, narrative 2000); secrets are never returned. JSONB fields have versioned Pydantic schemas and are not arbitrary extension bags.

Nothing beyond the explicit Stage-1 delta above authorises a migration merely because a table/column is listed below. Existing implementation must first be inspected and every other proposed difference classified as KEEP / MODIFY / ADD / MERGE / REMOVE.

All references below are foreign keys with ON DELETE RESTRICT unless a documented privacy purge deletes a dependent private result/answer pair explicitly. No cascading deletion of personnel, historical decisions or source history. Index foreign keys and common `(unit_id,date)` / `(personnel_id,date)` retrievals. Checks reject NaN/infinity, invalid enums and reversed date intervals. Unique constraints include scope/date/version as stated. Derived values are nullable only alongside explicit non-VALID status; VALID rows require their required numeric payloads.

The existing authoritative active Alembic configuration is `backend/alembic.ini`: script_location=`%(here)s/alembic` and version_locations=`%(here)s/alembic/canonical`. The canonical chain is `b26186_baseline → c26186_implementation → d26186_leave_lifecycle`, whose terminal revision matches the previously verified applied head. Backend Docker WORKDIR is `/app`; Compose mounts backend there and invokes `alembic upgrade head`, and Railway uses the same backend build/start path. Stage 2 must create exactly one new revision in `backend/alembic/canonical` with `down_revision = "d26186_leave_lifecycle"`. The local and deployed databases share this lineage. `database/alembic.ini` selects the same canonical revisions and `database/migrations/env.py` delegates to the backend environment; these are compatibility bridges, not competing authorities. Historical directories remain history only. No moves, deletion, second lineage, reset or stamp is authorized. Fresh/upgrade migration verification remains a later implementation requirement, not a result claimed by this correction.

### Physical type and version conventions

Foreign-key IDs are UUID. Names/codes/enums/hashes/versions are TEXT with the bounded
validation described above; SHA-256 values require exactly 64 hexadecimal characters.
Counts, revisions and scenario_version are INTEGER. Scores/hours/ratios are NUMERIC
with domain checks; probabilities use NUMERIC(9,8), WSI/components NUMERIC(7,4) and
other analytic numeric values NUMERIC(18,6). WSI is rounded to two decimals for its
public value; contributions preserve precision. All `_at` timestamps, as_of,
effective_from/until and interval window/start/end fields are TIMESTAMPTZ, except
explicit business DATE fields and all `_date` fields, which are DATE. JSON payloads/arrays are JSONB, flags BOOLEAN.

`revision` is an optimistic concurrency counter incremented on a mutable row update.
`scenario_version` is the immutable proposal content version within a parent chain;
a revised proposal gets a new ID and parent.version+1. Approval records bind the
scenario ID/content version, not the mutable concurrency counter. Audit records and
immutable source manifests are append-only. Units/users/personnel/operational current rows, sessions,
consent/cases, scenarios, outcomes, alerts, imports, registry activation,
deletion requests and rate-limit buckets are mutable; historical events/results,
scenario changes, decisions and implementations are immutable. Write corrections as
new source events or proposal revisions, not altered evidence.

## 2. Identity and source tables

The following field/table definitions are the current reconciliation proposal/reference. They are NOT automatically approved migration requirements. During the dedicated database review, compare them against current schema/models/consumers and classify each as KEEP / MODIFY / ADD / MERGE / REMOVE. Integer quantities are nonnegative unless specified. Existing names are retained when semantics match; a migration must explicitly map renamed fields.

| Table | Fields and constraints |
|---|---|
| units | unit_code unique, unit_name, unit_type, parent_unit_id?→units, location_label?, sanctioned_strength integer, is_active boolean; no cyclic hierarchy |
| personnel | personnel_code unique, pseudo_id unique, full_name, unit_id→units, rank_or_grade, role_title, status ACTIVE/INACTIVE/SEPARATED, joining_date DATE, service_years? numeric >=0; code/name never in Commander projections |
| users | username case-insensitive unique, password_hash, role in PERSONNEL/WELFARE_OFFICER/COMMANDER/ADMIN, personnel_id?→personnel unique when set, unit_id?→units, is_active; PERSONNEL requires person, Commander/Welfare require unit; ADMIN person binding null; immutable person binding |
| auth_sessions | existing session fields plus approved nullable refresh_secret_hash CHAR(64); legacy rows remain NULL and must reauthenticate after refresh activation; no plaintext tokens or backfill |
| posting_history | personnel_id→personnel, unit_id→units, posting_start_date, posting_end_date?, posting_type, location_label?, hardship_level? integer 1–5; non-overlapping effective postings per person |
| deployments | personnel_id→personnel, unit_id→units, deployment_type, location_label?, start_date, end_date?, intensity_level? integer 1–5; no overlapping active deployment intervals; missing intensity blocks H during deployed days |
| duties | personnel_id→personnel, unit_id→units, duty_date, start_at, end_at, duty_type, shift_type, is_night boolean, hours numeric, deployment_id?→deployments; end>start, hours equals duration within 0.01 hour; no overlapping actual duty intervals |
| rest_records | personnel_id→personnel, record_date, rest_hours? numeric 0–24, rest_gap_hours? numeric >=0, source, data_quality_status; unique(personnel_id,record_date); no negative physical duration |
| leave_records | personnel_id→personnel, leave_type, start_date, end_date, days numeric >0, status PENDING/APPROVED/REJECTED/CANCELLED/COMPLETED, requested_at?, approved_at?, planning_class PLANNED/UNPLANNED/UNKNOWN; end>=start; days equals inclusive calendar length for MVP |
| leave_events | leave_id→leave_records, personnel_id→personnel, event_type REQUESTED/APPROVED/STARTED/COMPLETED/CANCELLED/SHORTENED/POSTPONED/CORRECTED, occurred_at, known_at, initiated_by PERSONNEL/SERVICE/ADMIN_CORRECTION/UNKNOWN, previous_start/end/status?, new_start/end/status?, supersedes_event_id?→leave_events, external_event_id unique; immutable chronology, no circular correction chains |
| training | personnel_id→personnel, training_name, training_type?, start_date, end_date, hours? numeric >=0, status PLANNED/COMPLETED/CANCELLED; end>=start; hours are total interval hours |
| staffing | unit_id→units, record_date, sanctioned_strength, available_strength, required_strength integers, coverage_percent? numeric >=0; unique(unit_id,record_date); coverage=100*available/required, null when required=0; values >100 are valid |
| skills | skill_code unique, skill_name, category?, is_active boolean |
| person_skills | composite key(personnel_id→personnel,skill_id→skills,valid_from DATE); proficiency_level integer 1–5, valid_until? DATE; no overlapping validity for the same person/skill |

Where fields already support it, operational/master source records preserve cutoff/known-at and source identity. `SOURCE_COVERAGE_POLICY_V1_SYNTHETIC_DEMO` uses immutable versioned manifests bound to deterministic database-derived source hashes and requires zero unknown gaps for mandatory windows. No `source_revisions` table is approved. Date-only leave events still require a source-supplied UTC occurrence time for labels; do not infer late-request/disruption semantics from leave_type.

`rest_gap_hours` is elapsed recovery interval, not signed deficit. Legacy negative values are invalid for this field; retain them in rejected-row evidence and require a documented source transformation if the generator meant a different metric. Never apply abs() or silently clamp. A complete non-deployed day may have no deployment row; source coverage makes that absence meaningful.

## 3. Source provenance, imports and planning inputs

*The following planning/import structures are reference material pending implementation reconciliation. No source_revisions or source_coverage table is approved; coverage is supplied by immutable manifests bound to database-derived hashes.*

| Table | Fields and constraints |
|---|---|
| import_batches | dataset_type, file_name (sanitized), sha256, manifest_json, state VALIDATED/COMMITTED/REJECTED, row_count, error_count, validated_by→users, committed_by?→users, committed_at?, safe_errors_json; unique(dataset_type,sha256) for successful commits |
| shift_requirements | unit_id→units, start_at, end_at, required_count integer >0, required_skills_json, is_locked boolean; required_skills entries {skill_id,min_proficiency,count}, counts <= required_count, duplicate skill forbidden |
| roster_assignments | shift_id→shift_requirements, personnel_id→personnel, is_locked boolean, source_revision; unique(shift_id,personnel_id); existing published plan, not an optimizer output |
| availability_intervals | personnel_id→personnel, start_at, end_at, state AVAILABLE/UNAVAILABLE, reason_code LEAVE/TRAINING/DEPLOYMENT/OTHER, source_revision; no conflicting overlapping states |

Requirements, assignments and availability also use the source provenance convention. Missing availability coverage is unknown, not implicitly available. Approved leave and fixed deployments/training further restrict available intervals. Multi-skill quotas mean a person can satisfy each skill they hold, but counts for each required skill are independently checked; total staffing still counts distinct people.

## 4. Derived operational tables

Common analytic fields for per-person tables (not model_registry): personnel_id→personnel, unit_id→units (effective context), as_of, calculated_at, availability_status, reason_codes JSONB string array, policy_version, source_revision_hash, coverage_json. Immutable per version/source hash, no accidental overwriting of older results. Stored historical valid snapshots are not retroactively stale; current API freshness may wrap them as DATA_STALE with a separate last_valid reference.

| Table | Additional fields and uniqueness |
|---|---|
| wsi_snapshots | snapshot_date, wsi_score? numeric 0–100, d/r/c/n/l/h/s_component? each 0–100, contributions_json?, raw_inputs_json?; unique(personnel_id,as_of,policy_version,source_revision_hash); VALID requires score and all seven components |
| baseline_metrics | metric_name='WSI', median_value?, mad_value? >=0, z_score?, zero_mad boolean, direction? ABOVE/BELOW/EQUAL, ewma_value?, ewma_status, trend? RISING/FALLING/STABLE, trend_status, history_count integer, history_start/end, lambda_value; baseline availability independent of EWMA/trend availability |
| anomaly_events | algorithm='IsolationForest', anomaly_score?, is_anomaly? boolean, cohort_version, cohort_size, cohort_hash, feature_version, library_version; unavailable means null flag, not false |
| model_outputs | Reuse the existing physical table for VALID governed Model-A rows only. Discriminator: target_name=next_30d_leave_anomaly, approved Model-A identifier, model_version=1.0.0, feature_set_version=v2.1-SetB-15ops, training data version=v2.1-frozen-prototype, target contract=v2.1-approved-leave-lifecycle and approved artifact hash. hr_probability is Model-A only; wellbeing_probability and combined_probability are NULL. Typed explanation metadata binds cutoff/source hash/coverage/policy. Unavailable inference creates no fake valid row. Legacy 320 rows remain unchanged and non-authoritative |
| model_registry | model_version unique, target_version, feature_version, policy_version, artifact_path (server-controlled), artifact_sha256, manifest_json, evaluation_json, status REGISTERED/APPROVED/RETIRED/FAILED, is_active boolean DEFAULT FALSE, approved_by?→users, approved_at?; partial unique(target_name) WHERE is_active; target_name required; only APPROVED can be active |

Baseline z may be null on VALID zero-MAD unequal input as defined in ml.md §8.1: median/MAD remain valid, direction/zero_mad and ZERO_MAD_NONZERO_DEVIATION reason must be populated; no finite standardized deviation is claimed. No other silent VALID/null exceptions. Outcome availability uses calculation states VALID/NOT_COMPUTED/INSUFFICIENT_HISTORY and explicit error states where applicable; workflow status PENDING/OBSERVED/REVIEWED is a separate required column, never INSUFFICIENT_HISTORY. Architecture.md §§10–11 own scenario/outcome calculations, observation policy and lifecycle. Explanation and feature JSON are strictly operational allowlists. Training/evaluation exports are offline de-identified artifacts, not web-queryable private tables.

## 5. Private wellbeing and welfare cases

| Table | Fields and constraints |
|---|---|
| instrument_registry | instrument_name, instrument_version, language, scoring_version, recall_days, wording_checksum, source_url, usage_evidence_ref?, enabled boolean; unique(name,version,language); enable requires evidence and scoring fixtures |
| wellbeing_consent | personnel_id→personnel, purpose COLLECTION/SHARING, instrument_id?→instrument_registry, case_id?→support_requests, recipient_user_id?→users, assessment_ids_json, notice_version, status ACTIVE/WITHDRAWN/EXPIRED, granted_at, expires_at?, withdrawn_at?, revision; sharing requires case/recipient/explicit assessment IDs; expiry is required only where the approved versioned sharing policy uses time-based expiry; collection requires instrument |
| wellbeing_private | personnel_id→personnel, instrument_id→instrument_registry, collection_consent_id→wellbeing_consent, assessment_date, submitted_at, answers_json with exact item IDs, language, idempotency_key; immutable completed assessment, unique(personnel_id,idempotency_key) |
| wellbeing_results | assessment_id unique→wellbeing_private, personnel_id→personnel, scoring_version, total numeric, percentage? numeric, direction HIGHER_BETTER/HIGHER_WORSE, availability_status; raw answers never copied here; trends computed from allowed results on read |
| support_requests | existing case fields plus request_key_hash CHAR(64) NULL and request_hash CHAR(64) NULL; partial unique(personnel_id,request_key_hash) WHERE request_key_hash IS NOT NULL; historical rows remain NULL with no backfill; request_text remains Personnel-visible and never stores officer-confidential notes |
| welfare_case_actions | NEW: id UUID PK; case_id UUID NOT NULL→support_requests; actor_user_id UUID NOT NULL→users; action_type bounded to CONTACT_ATTEMPT/DISCUSSION/WORKLOAD_REVIEW/REFERRAL/FOLLOW_UP/ASSIGN/REASSIGN/STATUS_CHANGE/CLOSE; note TEXT NULL max 2000; visibility PERSONNEL/OFFICER; follow_up_date DATE NULL; case_status bounded nullable; assigned_to_user_id UUID NULL→users; created_at TIMESTAMPTZ server-generated; idempotency_key CHAR(64) NOT NULL; request_hash CHAR(64) NOT NULL; unique(case_id,actor_user_id,idempotency_key); index(case_id,created_at,id); append-only |
| notifications | NEW: id UUID PK; recipient_user_id UUID NOT NULL→users; notification_type VARCHAR(40) bounded; message VARCHAR(255) server-template only; resource_type VARCHAR(50) NULL and resource_id UUID NULL as an allowlisted validated pair; created_at TIMESTAMPTZ server-generated; read_at TIMESTAMPTZ NULL; dedupe_key CHAR(64) NOT NULL; unique(recipient_user_id,dedupe_key); index(recipient_user_id,created_at,id); unread means read_at IS NULL |
| deletion_requests | *candidate — requires separate privacy/database approval* — personnel_id→personnel, requested_at, scope_json (selected IDs/all private), due_at, state QUEUED/COMPLETED/FAILED, completed_at?, safe_error_code? |
| deletion_tombstones | *candidate — requires separate privacy/database approval* — subject_key_hash, resource_kind, resource_key_hash, deleted_at, backup_expiry_at; no private contents; retained through backup expiry |

Sharing consent creation occurs after its referenced assessments/case exist. Validate every assessment owner/instrument and recipient scope, including JSON ID relationships in the service transaction. Expiry/reassignment/closure/withdrawal is checked at query time, not only a nightly job. Collection withdrawal prevents new processing, not the owner's reads of already stored results. Private purge deletes shared references/results/answers coherently and blocks orphaned access; minimal consent/audit evidence remains under rules.md retention.

`welfare_case_actions` is the only approved store for confidential officer action/follow-up narrative. Personnel read their own request and PERSONNEL-visible actions only. The currently assigned authorized Welfare Officer may read OFFICER and appropriate PERSONNEL-visible actions. Commander receives no case narrative/action. Admin receives governance metadata without note content. audit_events records actor/role, action, case/action opaque resource IDs, timestamp, result and safe reason code only—never note, request narrative, raw answer, private score or participation.

`notifications.message` is server-template text, never caller narrative. Resource type/ID must be allowlisted and reauthorized for list, count, detail and navigation. A user who loses current authorization receives no existence/content leak. Dedupe identity is recipient plus immutable business event/revision. No redundant read boolean, payload JSON or expiry field is approved.

## 6. Scenario, decision, outcome and governance tables

These are proposed persistence mappings, not an approved schema/migration freeze. An IMPLEMENTED scenario, decision and implementation remain immutable; parent_id links unimplemented proposal revisions only. A fresh later scenario may reference an earlier implementation for context using a mapping approved in the table-by-table review; do not add a mandatory table from this clarification. NOT_IMPLEMENTED is an audited terminal action result without a fabricated implementation entry. Sharing withdrawal, case closure and reassignment revoke access regardless of whether expires_at is null; optional time expiry never removes those boundaries.

| Table | Fields and constraints |
|---|---|
| roster_scenarios | unit_id→units, created_by_user_id→users, parent_id?→roster_scenarios, scenario_version integer, revision, status from architecture.md, window_start/end, source_revision_hash, policy_version, current_snapshot_json, proposed_snapshot_json, before_metrics_json, after_metrics_json, constraint_results_json, optimizer_method, optimizer_status; snapshots immutable after evaluation; exact assignment IDs/pseudonyms, no private case contents |
| scenario_changes | scenario_id→roster_scenarios, personnel_id→personnel, shift_id→shift_requirements, change_type REASSIGN/SWAP, from_value_json, to_value_json, reason; unique(scenario_id,shift_id,personnel_id,change_type) |
| approvals | scenario_id→roster_scenarios, scenario_version, actor_user_id→users, decision ACCEPT/MODIFY/REJECT, reason, decided_at, source_revision_hash; one terminal decision per scenario_id/scenario_version; no private reasons |
| scenario_implementations | scenario_id unique→roster_scenarios, approval_id→approvals, actor_user_id→users, effective_at, recorded_at, actual_assignments_json, external_reference, reason, source_revision_hash; requires matching ACCEPT and constraints; no automatic write to duties |
| outcomes | reuse the existing table and validated versioned observed_metrics_json for workflow, independent availability, exact matched windows, frozen group, coverage, metrics/adherence, source/policy/calculation hashes and review receipt. Deterministic UUID plus implementation lock provides retry safety; no duplicate outcome table or new columns are approved. Historical rows are not silently reinterpreted |
| alerts | reuse existing operational attention rows and global unique dedupe_key. Occurrence identity includes personnel + trigger family + policy + qualifying cutoff; row/family locks suppress unresolved OPEN/ACKNOWLEDGED duplicates and enforce cross-version cooldown. Do not rewrite legacy statuses/keys |
| audit_events | actor_user_id?→users, actor_role?, subject_personnel_id?→personnel, unit_id?→units, action, resource_type, resource_id?, purpose_code?, result ALLOWED/DENIED/FAILED, request_id, metadata_json allowlist; append-only and content-free |
| policy_config | reuse existing table for immutable typed versions/effective intervals/content hashes. The physical baseline has no unique policy_key constraint; use advisory locks and reject duplicate/overlapping active policies. No uniqueness DDL is approved in Stage 1 |
| rate_limit_counters | bucket_key_hash, window_start, request_count integer; composite key(bucket_key_hash,window_start), expires_at; no username/IP plaintext |

Artifact registration/approval is separate from live model inference. Audit metadata allowlist: action IDs, version IDs, reason codes, safe counts, source hashes and request ID. No score/answer/narrative text. Append-only audit is MVP; full hash-chain is deferred. Personnel access history projects role/time/purpose and resource kind only.

## 7. Application authorization and query scoping

Security enforcement: `APPLICATION_AUTHORIZATION_AND_QUERY_SCOPING`. PostgreSQL RLS: `DEFERRED_NOT_ACTIVE`. FastAPI authentication dependencies and server-side services enforce current role/unit/person/case/purpose and applicable consent; repositories apply explicit scoped query predicates and response schemas project only permitted fields. Stage 2 neither enables/FORCEs RLS nor creates RLS-specific runtime principals. RLS may be considered only in a separately user-approved future hardening stage.

Authenticated identity and scope come from the current server-side account/session, never caller-supplied headers/body. Missing or malformed required scope denies access. Any transaction-local metadata is supplementary and cannot replace application checks. Test successive requests from different roles/units through reused pooled connections to prove no scope leakage.

- Personnel queries restrict own person and permitted operations; account-person binding cannot be reassigned.
- Commander queries restrict the current assigned unit and operational/scenario data. Explicit response projections exclude names/service codes, private wellbeing and support content.
- Welfare unit operational projections remain pseudonymous. Identity requires audited named-search/case purpose. Confidential content requires current case assignment; derived private results additionally require matching active consent/recipient/assessment. Raw answers never enter Welfare projections.
- Admin queries permit master/import/policy/system records and redacted governance metadata, never private answers/results or confidential case notes. Master identity access does not authorize individual welfare scoring.
- Operational jobs use dedicated operational repository interfaces and never query private tables. Private scoring, if separately activated, remains owner/consent scoped. Support services enforce case authorization in the same transaction as their scoped reads/writes.

Privacy tests exercise authorized/denied HTTP operations, services, repository predicates and explicit projections with runtime-equivalent sessions. Inactive RLS supplies no direct-SQL isolation guarantee; database-owner or session-setting tests cannot be cited as privacy enforcement. All existing privacy/disclosure requirements remain binding.

## 8. Import mapping and ordering

Actual CSV header inventory is in the appendix below, captured from repository files without reading private row content. Header agreement alone does not certify row validity or target provenance. Existing V2 inputs are legacy source fixtures and require an adapter; do not silently interpret them as V1 event-complete data.

Default same-name columns map directly after type/enum validation. Explicit transforms: dates to UTC/business DATE as appropriate; password to Argon2id password_hash then discard plaintext; duration-derived duty hours checked against timestamps; derived coverage recomputed allowing >100; private instrument_name/version maps to instrument_registry; score_json is ignored and recomputed in private scoring; missing source known_at uses receipt time and forbids retrospective reconstruction; missing leave planning metadata maps UNKNOWN and target ineligible. Missing required field is a row error, never a invented default.

CSV enums that differ from this schema need an explicit versioned mapping in the adapter and rejection of unknown values. Ignore only documented non-source artifacts (feature_dictionary, data_dictionary, manifest, split_manifest, target_audit and ml_training) in application ingestion; these are offline metadata/training artifacts, not runtime operational tables. Unknown columns produce a validation error until a mapping is documented. Do not drop unknown data silently.

*Illustrative/candidate pending database reconciliation* — Dependency order for clean synthetic seeding: units → personnel → users → instrument/policy registry → import provenance/coverage → postings/skills/person_skills → deployments → duties/rest/leave_records/leave_events/training/staffing → requirements/availability/assignments → collection consent → private assessment/results through private scorer → support cases → explicit sharing consent → operational derived jobs → scenarios/changes → approvals → implementation records → outcomes → alerts. Parent units precede children; cases precede sharing. Only seed prior decisions/outcomes with consistent dated history. No outcomes referencing absent scenarios.

A batch validates headers/types/FKs/dates/enums/duplicates/coverage before any source mutation, commits atomically and audits row counts/hash. Replay of the same batch is idempotent; a correction produces new source evidence and a new immutable manifest/hash without a `source_revisions` table. Rejected rows are reported by row number/field/error without sensitive values. Derived CSVs (WSI/baseline/anomaly/model outputs/alerts/outcomes) never override runtime calculations; historical fixtures are isolated and visibly labelled if used for a rehearsal.

## 9. Acceptance gates

After table-by-table database review is locked, test the approved schema/migration plan on a disposable fresh PostgreSQL database and representative upgrade path. This documentation-only task does not authorise migrations or data deletion.

## 10. Inspected CSV header inventory

These headers are evidence of current inputs, not an alternative schema or a promise that the files contain sufficient data.

### alerts.csv

`id, personnel_id, unit_id, alert_type, severity, source_type, source_id, status, dedupe_key, message, created_at, resolved_at`

### anomaly_events.csv

`id, personnel_id, unit_id, event_date, algorithm, anomaly_score, is_anomaly, feature_set_version, created_at`

### approvals.csv

`id, scenario_id, actor_user_id, decision, reason, decided_at`

### baseline_metrics.csv

`id, personnel_id, metric_date, metric_name, current_value, median_value, mad_value, z_score, ewma_value, history_count, baseline_status, created_at`

### data_dictionary.csv

`table, column, description, dtype`

### deployments.csv

`id, personnel_id, unit_id, deployment_type, location_label, start_date, end_date, intensity_level, created_at`

### duties.csv

`id, personnel_id, unit_id, duty_date, start_at, end_at, duty_type, shift_type, is_night, hours, deployment_id, created_at`

### feature_dictionary.csv

`feature, source_table, lookback, description, available_at_prediction_date`

### leave_records.csv

`id, personnel_id, leave_type, start_date, end_date, days, status, created_at`

### manifest.csv

`dataset_version, generator_version, schema_version, seed, generation_period, generation_date, validation_status`

### ml_training.csv

`pseudo_id, prediction_date, future_window_start, future_window_end, target_leave_anomaly, target_eligibility, split, dataset_version, duty_hours_7d, duty_hours_30d, night_duty_count_14d, night_duty_ratio_30d, consecutive_duty_days, min_rest_hours_14d, avg_rest_hours_30d, quick_return_count_30d, deployment_days_30d, training_days_30d, staffing_ratio_7d, workload_change_14v14, ewma_workload, baseline_z_workload, leave_frequency_90d, leave_gap_variability_90d, peer_deviation_workload`

### model_outputs.csv

`id, personnel_id, prediction_date, target_name, prediction_probability, predicted_class, model_name, model_version, feature_set_version, training_data_version, evaluation_metrics_json, explanation_json, created_at`

### outcomes.csv

`id, scenario_id, recorded_by_user_id, observation_date, observed_metrics_json, wsi_change, operational_event_observed, notes, created_at`

### person_skills.csv

`personnel_id, skill_id, proficiency_level, valid_from, valid_until`

### personnel.csv

`id, personnel_code, pseudo_id, unit_id, rank_or_grade, role_title, status, joining_date, service_years, created_at, updated_at`

### posting_history.csv

`id, personnel_id, unit_id, posting_start_date, posting_end_date, posting_type, location_label, created_at`

### rest_records.csv

`id, personnel_id, record_date, rest_hours, rest_gap_hours, source, data_quality_status, created_at`

### roster_scenarios.csv

`id, unit_id, created_by_user_id, scenario_name, status, current_snapshot_json, proposed_snapshot_json, before_metrics_json, after_metrics_json, constraint_results_json, optimizer_method, created_at`

### scenario_changes.csv

`id, scenario_id, personnel_id, change_type, from_value, to_value, reason, created_at`

### skills.csv

`id, skill_code, skill_name, category, is_active`

### split_manifest.csv

`split, n_rows, boundary_start, boundary_end`

### staffing.csv

`id, unit_id, record_date, sanctioned_strength, available_strength, required_strength, coverage_percent, created_at`

### support_requests.csv

`id, personnel_id, request_type, status, priority, assigned_to_user_id, request_text, follow_up_date, closed_at, created_at, updated_at`

### target_audit.csv

`pseudo_id, prediction_date, future_window_start, future_window_end, target_leave_anomaly, target_eligibility, target_rule_version`

### training.csv

`id, personnel_id, training_name, training_type, start_date, end_date, hours, status, created_at`

### units.csv

`id, unit_code, unit_name, unit_type, parent_unit_id, location_label, sanctioned_strength, is_active, created_at, updated_at`

### users.csv

`id, username, password_hash, role, personnel_id, unit_id, is_active, created_at, updated_at`

### wellbeing_consent.csv

`id, personnel_id, consent_version, purpose, status, consented_at, withdrawn_at, created_at`

### wellbeing_private.csv

`id, personnel_id, assessment_date, instrument_name, instrument_version, answers_json, score_json, created_at`

### wsi_snapshots.csv

`id, personnel_id, unit_id, snapshot_date, wsi_score, d_component, r_component, c_component, n_component, l_component, h_component, s_component, policy_version, created_at`
