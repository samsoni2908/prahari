# PRAHARI — Architecture and API Contract

This is the target implementation contract. Current code may differ; [task.md](task.md) records reconciliation work. Scope: [prd.md](prd.md); privacy: [rules.md](rules.md); persistence: [database.md](database.md); analytics: [ml.md](ml.md).

## 1. Runtime and ownership

Browser/PWA → same-origin Next.js `/api/v1` proxy → FastAPI → PostgreSQL 16. FastAPI calls pure typed analytics through services. Local PostgreSQL runs in Docker; deployed frontend/backend are Railway-compatible, with Neon over TLS. The optional Android wrapper loads the same HTTPS web application.

Frontend: Next.js/TypeScript, Tailwind/shadcn, Recharts. Backend: Python/FastAPI, Pydantic/OpenAPI, SQLAlchemy 2.x, Pandas/NumPy/scikit-learn, APScheduler. Keep backend business rules in services and database access in repositories; API routers never contain SQL. Analytics modules have no HTTP/session coupling. Maintain feature-oriented modules; reuse existing verified consumers instead of duplicating them.

Operational analytics and private wellbeing are distinct service/data boundaries. A single deployment may host both, but FastAPI/server-side authorization, scoped repository queries, explicit response projections and job interfaces must enforce the separation. Operational jobs cannot query private tables. Private scoring reads only the consenting person's assessment. Model C reads authorised derived outputs on demand, never raw answers or a broad join into operational reports. PostgreSQL RLS is DEFERRED / NOT ACTIVE and is optional future hardening requiring separate user approval.

## 2. Authentication and request security

Four roles only. Prepared accounts, no signup. Argon2id password hashes, no plaintext storage. `SESSION_SECURITY_POLICY_V1` fixes an 8-hour absolute session lifetime, 30-minute idle timeout and 15-minute access JWT lifetime. Server-side auth_sessions plus signed access JWT use a fixed permitted algorithm, issuer/audience, subject and session JTI. Reject inactive users and revoked/expired/idle sessions on every protected request, not only JWT signature validation. Role, scope and deactivation changes revoke all affected sessions; any future approved credential/password-change flow also revokes them.

Access JWT is stored in an HttpOnly Secure SameSite=Lax cookie, path `/api/v1`; a rotating opaque refresh secret uses a separate HttpOnly Secure SameSite=Lax cookie, path `/api/v1/auth`. Store only the refresh hash. Refresh locks the session, verifies and atomically rotates that hash, enforces current idle/absolute limits and never extends the original 8-hour absolute lifetime; stale/replayed refresh fails. Existing sessions without a refresh hash must reauthenticate, with no fabricated backfill. Logout revokes server-side immediately and repeated logout safely clears cookies. Session JTI stays bound to the session. Never store credentials/tokens/private answers in localStorage or URLs. Local HTTP development alone may disable Secure; deployment must reject that setting. Rate-limit values remain separately configurable.

Same-origin proxy is the default so cookie/CORS behavior is consistent. Mutating requests require a session-bound CSRF token in `X-CSRF-Token` plus exact allowed Origin validation. GET `/auth/csrf` issues a pre-login signed CSRF cookie/token; login validates it, then replaces it with session-bound CSRF state. Exclude health GET only. Configure a strict CORS allowlist for direct API development access; never wildcard credentialed origins. Limit login attempts per account/IP combination per window (configurable); return generic credentials failure without account enumeration. Rate limiting authenticated traffic and scenario generation are security capabilities; exact values are configurable and must not rely on process-local limits in a multiworker deployment. Server enforcement uses database-backed counters or equivalent shared mechanism for the demo.

Each protected operation: authenticate → enforce current role/unit/person/case scope and purpose/consent server-side → scoped repository query/service operation → explicit response projection → safe audit. Security enforcement is APPLICATION_AUTHORIZATION_AND_QUERY_SCOPING; it does not depend on PostgreSQL RLS or database session attributes. Out-of-scope resource IDs return 404; wrong role returns 403; missing/revoked session returns 401. Do not disclose hidden records in errors or counts. Sensitive reads/mutations fail closed if required audit persistence fails. Audit denial using safe metadata even when a business transaction rolls back.

## 3. API conventions and types

Prefix `/api/v1` except the implemented health routes `/health` and `/ready`. Preserve these names unless a separate user approval changes them; later stages may improve their semantics. UUID resource IDs, RFC3339 UTC timestamps, ISO dates, snake_case fields, finite numbers only. Unknown request fields are rejected. List pagination uses opaque cursor, configurable limit and stable `(created_at,id)` ordering unless an endpoint defines date order. Lists return `{items,next_cursor}`; no unrestricted total count. Range filters are bounded; own historical instrument listing is paginated without bulk export. Exact default/max values for pagination and range are implementation-specific unless separately approved.

Errors: `{error:{code,message,request_id,field_errors?}}`; no SQL/stack traces/private values. 400 malformed query, 401 unauthenticated, 403 forbidden role, 404 absent/out-of-scope, 409 stale revision/state/idempotency collision, 422 validation or infeasible submission, 429 throttled, 503 unavailable dependency. GET analytics availability is generally HTTP 200 with explicit unavailable fields, not an invented score or blanket server error.

All create/action POSTs require `Idempotency-Key`, except authentication/CSRF bootstrap/refresh/logout, which use their explicit session semantics. Use domain-specific row locks, deterministic IDs, existing uniqueness, request hashes, idempotency digests and typed immutable receipts; no global idempotency table. Same key/payload replays the original safe result after current reauthorization; the same key with a different payload returns 409. Updates require server-derived `expected_revision`; transactions lock the target and verify it. Responses never serialize ORM objects directly.

Shared response contracts:

| Type | Required fields and meaning |
|---|---|
| Metric | `status`, nullable `value`, `reason_codes[]`, `as_of`, `calculated_at`, `policy_version`, `coverage` (required/observed days) |
| OperationalDetail | `pseudo_id`, `unit_id`, `as_of`, `wsi` (Metric plus seven components/contributions), `baseline`, `ewma`, `peer`, `prediction`, nullable `attention`, `attention_status`, `attention_reasons[]`, `data_quality`, `synthetic=true` |
| Prediction | Metric plus nullable `probability`, nullable `threshold`, `model_version`, `feature_version`, `target_version`, `artifact_hash`, `drivers[]`; value aliases probability only in this typed subtype |
| Driver | `feature`, `display_label`, `raw_value`, `unit`, `window`, `contribution`, `method`; method distinguishes WSI weighted points from model log-odds |
| PrivateResult | `assessment_id`, `instrument/version/language`, `assessment_date`, `total`, nullable `percentage`, `direction`, `status`, `trend` with reference assessment/date/total/delta/status |
| SharedCaseResult | Allowed subset of PrivateResult from rules.md plus `consent_id`, `expires_at`; never answers |
| Scenario | `id`, `revision`, `scenario_version`, `parent_id`, `unit_id`, `status`, `window_start/end`, `source_revision_hash`, `policy_version`, `assignments[]`, `changes[]`, `constraint_results[]`, `before_projection`, `after_projection`, `optimizer_status`, `warnings[]`, audit timestamps |
| Outcome | `scenario_id`, `implementation_id`, workflow `status`, independent `availability_status`, `reason_codes[]`, `policy_version`, `calculation_version`, explicit before/after windows, `coverage`, `observed_metrics`, `adherence`, `leave_followup_status`, nullable event result, human review fields |

Personnel own profile may contain their name; Commander OperationalDetail/Scenario never does. Welfare case identity is a separate CaseDetail field after case authorization. Missing sharing is NOT_SHARED without revealing whether an assessment exists. No API returns private participation to Commander/Admin.

## 4. Endpoint contract

The table describes required capabilities/target API behavior. Existing verified routes must be preserved or compatibility-mapped; this documentation task does not require wholesale route renaming/refactoring.

All routes below use the prefix. “Unit” means the authenticated assigned unit, rechecked on every access. Read sources and write transactions follow database.md table names. Sensitive reads and every mutation are audited; health and static metadata are exceptions. Every route requires role and negative access tests.

| Method/path | Role/scope | Request → result; persistence |
|---|---|---|
| GET `/auth/csrf` | Public, rate-limited | CSRF bootstrap; no account data |
| POST `/auth/login` | Public with CSRF/Origin | username/password → safe user, cookies; users/auth_sessions |
| POST `/auth/refresh` | Active refresh session | CSRF → renewed access cookie |
| POST `/auth/logout` | Current session | revoke session, clear cookies; idempotent |
| GET `/auth/me` | Any active role | role, own safe profile, unit, session expiry, CSRF token |
| GET `/personnel/me` | Personnel self | own profile and permitted service history |
| GET `/personnel/me/operational` | Personnel self | optional as_of → OperationalDetail |
| GET `/personnel/me/history` | Personnel self | kind=duties/rest/leave/deployments/training/postings, date range → paginated own history |
| GET `/personnel/me/access-history` | Personnel self | date/cursor → redacted access/consent/action history, actor role/purpose/time, no security internals |
| GET `/wellbeing/instruments` | Personnel self | available versions, notices, recall periods and usage availability |
| POST `/wellbeing/consents` | Personnel self | purpose=COLLECTION or SHARING, notice_version, instrument/version for collection; case_id and assessment_ids for sharing → consent |
| POST `/wellbeing/consents/{id}/withdraw` | Owner | expected_revision → revoked grant/processing state |
| POST `/wellbeing/assessments` | Personnel with collection consent | instrument/version/language, consent_id, integer answers keyed by item IDs → private score; server sets submitted time |
| GET `/wellbeing/assessments` | Personnel self | instrument filter/cursor → own PrivateResults |
| GET `/wellbeing/assessments/{id}` | Owner | own answers and PrivateResult; re-read history allowed after withdrawal |
| GET `/wellbeing/convergence` | Personnel self | latest per-instrument private convergence; collection withdrawal blocks fresh computation |
| POST `/wellbeing/deletion-requests` | Personnel self | *candidate/deferred pending database/privacy lifecycle review* — selected assessment IDs or all_private=true → queued deletion reference and due date |
| POST `/support/requests` | Personnel self | request_type=DISCUSSION/WORKLOAD_REVIEW/REFERRAL/OTHER, optional bounded text → confidential case |
| GET `/support/requests` | Personnel self | own case status and personnel-visible updates |
| GET `/support/requests/{id}` | Owner | own request/updates; no officer-private notes |
| POST `/support/requests/{id}/withdraw` | Owner | expected_revision, optional reason → WITHDRAWN unless closed |
| GET `/commander/overview` | Commander unit | day/week → suppression-safe operational aggregates |
| GET `/commander/personnel` | Commander unit | attention=LOW/MEDIUM/HIGH or availability filter → pseudonymous list |
| GET `/commander/personnel/{pseudo_id}/operational` | Commander unit | as_of → OperationalDetail |
| GET `/welfare/overview` | Welfare unit | scoped operational/case queues, no unconstrained private summary |
| GET `/welfare/personnel` | Welfare unit | same operational filters → pseudonymous list |
| POST `/welfare/personnel/search` | Welfare unit, case-handling purpose | name/service_code/pseudo_id (bounded validated search), purpose_reason → bounded identity-only results; no sensitive query in URL |
| POST `/welfare/cases` | Welfare unit | personnel_id, purpose_reason → new case; can exist without self-check |
| GET `/welfare/cases` | Welfare unit | status/assigned_to_me → pseudonymous case list |
| GET `/welfare/cases/{id}` | Welfare unit | named case detail, operational context, authorised shared results/convergence only |
| POST `/welfare/cases/{id}/actions` | Assigned Welfare officer | expected_revision, action_type, bounded note, visibility=PERSONNEL/OFFICER, follow_up_date?, next_status?, priority?, priority_reason? → appended action and updated case |
| POST `/welfare/cases/{id}/assign` | Welfare unit | officer_user_id, reason, expected_revision → case assignment; invalidates existing sharing |
| GET `/scenarios` | Commander/Welfare unit | list scoped scenarios, cursor |
| POST `/scenarios` | Commander/Welfare unit | window_start, selected_pseudo_ids, proposed assignment replacements or optimize=true → evaluated revision |
| GET `/scenarios/{id}` | Commander/Welfare unit | Scenario with projections and constraints |
| POST `/scenarios/{id}/revise` | Commander/Welfare unit | expected_revision, replacements, reason → new child revision and revalidation |
| POST `/scenarios/{id}/decisions` | Commander unit only | expected_revision, decision=ACCEPT/MODIFY/REJECT, reason → approval record/state |
| POST `/scenarios/{id}/implementation` | Commander unit only | expected_revision, result=IMPLEMENTED/NOT_IMPLEMENTED; actual effective_at/assignments/external_reference for IMPLEMENTED, recorded_at/reason_code for NOT_IMPLEMENTED → audited action result; §11 |
| GET `/scenarios/{id}/outcomes` | Commander/Welfare unit | observed comparison and follow-up availability |
| POST `/scenarios/{id}/outcomes/review` | Commander unit only | expected_revision, implementation_id, review_note → human review; metrics calculated by server, never client-entered success |
| GET `/alerts` | Commander/Welfare scope; Personnel own support only | status/trigger/cursor → audience-filtered alerts |
| POST `/alerts/{id}/acknowledge` | Authorised Commander/Welfare | expected_revision → acknowledged |
| POST `/alerts/{id}/resolve` | Authorised Commander/Welfare | expected_revision, reason → resolved |
| GET `/notifications` | Any active role, self only | cursor/read filter → currently authorised recipient-safe notifications |
| POST `/notifications/{id}/read` | Recipient only | idempotently set first read_at after current resource reauthorization |
| GET/POST `/admin/users`, PATCH `/admin/users/{id}` | Admin | list/create/update username, role, unit/person binding, is_active; secrets never returned; invalidate changed sessions |
| GET/POST `/admin/units`, PATCH `/admin/units/{id}` | Admin | validated unit master fields from database.md |
| GET/POST `/admin/personnel`, PATCH `/admin/personnel/{id}` | Admin | validated master fields, no analytic/private payload |
| POST `/admin/imports/validate` | Admin | source CSV + dataset_type + manifest → dry-run counts, redacted row errors and checksum, no source rows committed |
| POST `/admin/imports/{id}/commit` | Admin | validated checksum + expected_revision → atomic import and recompute job |
| GET `/admin/imports`, GET `/admin/jobs` | Admin | source health, manifest/coverage, safe job state |
| GET/POST `/admin/policies`, POST `/admin/policies/{id}/activate` | Admin | immutable typed policy version; activation validates bounds and audits version |
| GET `/admin/models`, POST `/admin/models/{id}/activate` | Admin | server-registered artifact health/evaluation; activate only passing compatible artifact |
| GET `/admin/audit` | Admin | time/action/result filters → redacted governance records |

Current legacy role-prefixed scenario routes may temporarily delegate to the same service during migration; no duplicate business logic. New clients use this canonical endpoint set. Master-data create/update field allowlists are database.md fields excluding IDs/audit timestamps; users' personnel binding cannot be reassigned after creation. Deactivation replaces destructive user deletion. Password provisioning uses an out-of-band demo secret input, hashes immediately and never echoes it.

## 5. Workflow state machines

Support case (`support_requests` is the case table): OPEN → ASSIGNED → IN_PROGRESS → CLOSED; OPEN/ASSIGNED/IN_PROGRESS → WITHDRAWN by owner. A new Officer-created case starts OPEN and logs purpose. Assignment to a valid same-unit officer is required before confidential case-content reads, actions or derived access. Unassigned case queues expose only pseudonym, request type and age; assignment itself is audited. An assigned officer may set manual NORMAL/URGENT workflow priority with a mandatory reason; no automatic medical urgency inference. Action types CONTACT_ATTEMPT, DISCUSSION, WORKLOAD_REVIEW, REFERRAL, FOLLOW_UP, CLOSE; the last requires a nonempty outcome note, with Personnel-visible text separated from confidential officer notes. Only an explicit new request creates a new case after closure; no silent reopening or continued sharing. Unit transfer withdraws/unassigns existing cases with reason UNIT_TRANSFER and revokes sharing. Personnel retain their own history and may explicitly open a new case in the new unit; prior case text/notes are not copied.

Scenario: DRAFT → FEASIBLE / INFEASIBLE / INPUT_UNAVAILABLE after evaluation. Only FEASIBLE with current source hash and policy may receive ACCEPT → APPROVED. REJECT → REJECTED; MODIFY → REVISION_REQUIRED. Revision creates an immutable child linked to the parent, which becomes SUPERSEDED; it must be evaluated/reviewed again. DRAFT/FEASIBLE/INFEASIBLE/INPUT_UNAVAILABLE/REVISION_REQUIRED may be revised; APPROVED can be superseded only before implementation. Decision endpoints allow MODIFY/REJECT on evaluated nonterminal states but ACCEPT only on FEASIBLE. No acceptance of a timeout result without a validated feasible incumbent.

Before approval and again before implementation: lock revision, compare roster/leave/skill/availability/policy hashes, re-check scope and constraints. Changed evidence returns 409 SOURCE_CHANGED and requires re-evaluation, not silent reuse of prior approval. Approval is an immutable record and never writes assignments. Duplicate requests return the same decision via idempotency.

Recording external action: requires APPROVED state, actual affected assignments, actual effective UTC time and an external reference. If actual differs from approved, require a new reviewed revision first. Confirmed record → IMPLEMENTED and links an immutable implementation entry; it does not manufacture observed duties. Ingestion of actual operational history supplies later outcomes. Historical-demo confirmation can be backdated only within the approved horizon with a visible synthetic-replay label and audit. Future effective dates are rejected: this endpoint records an actual external action, not a scheduled intention. Use wall clock, or the visibly configured synthetic replay clock, for this check. IMPLEMENTED is immutable and cannot be superseded by a revision; later changes require a fresh scenario with separately recorded temporal effects under §11. An authorised NOT_IMPLEMENTED result terminates an approved proposal without inventing actual action.

Outcome: PENDING until observation window complete, then OBSERVED; Commander acknowledgement → REVIEWED, preserving independent availability (including INSUFFICIENT_HISTORY). A 30-day leave follow-up has its own pending/complete/insufficient state. Scenario/outcome formula and window ownership is architecture.md §§10–11; event semantics remain ml.md §12.1. Case outcomes and operational scenario outcomes are distinct.

## 6. Jobs, errors and reliability

One APScheduler owner performs completed-day operational processing daily in UTC, with 00:15 UTC as the recommended operational run time. Startup registers the job only and never processes historical backlog automatically. An authorized manual/catch-up trigger calls the same orchestration service. Advisory/domain locks, governed outputs, alerts and safe audit_events provide bounded-MVP execution evidence; no `job_runs` table is introduced. Duplicate cutoff/input has no duplicate business effect. Per-person failure does not roll back unrelated successes; partial failure and retry are explicitly audited. Scheduler code never trains, seeds, migrates or activates a questionnaire. An error never changes a historical value to zero.

Imports validate fully before transaction, enforce configurable file-size and row-count limits, allowlisted CSV types/UTF-8 headers, date/FK/duplicate checks. Do not accept arbitrary server paths, executable files or ZIP extraction via public API. Exact file-size and row limits are implementation-specific unless separately approved. Private synthetic fixtures use a restricted offline seed path with explicit consent, never Admin raw-answer upload/readback. Derived fixtures must be rebuilt or explicitly isolated and labelled; ordinary ingestion never imports a fake successful model output.

Audit append and business mutations commit atomically. Sensitive read audit commits before returning payload. Data reconciliation, analytics and service errors use stable codes; no secrets in exceptions. `/health` returns process status; `/ready` checks database and migration compatibility, not optional model availability. Model/instrument availability is visible separately, so independent operational capabilities remain usable.

## 7. Deployment and configuration

The authoritative active Alembic configuration is `backend/alembic.ini`, with script_location `backend/alembic` and version_locations `backend/alembic/canonical`. Backend startup runs from `/app` using this configuration; the current chain is `b26186_baseline → c26186_implementation → d26186_leave_lifecycle`, matching the recorded applied head. Stage 2 must create exactly one new canonical revision in `backend/alembic/canonical` with down_revision `d26186_leave_lifecycle`. `database/alembic.ini` and `database/migrations/env.py` are compatibility bridges to the same backend lineage; historical migration directories remain history only. Do not create another lineage, move/delete history, reset or stamp a database. RLS activation and new RLS-specific runtime/worker/private principals are deferred optional hardening requiring separate user approval; application authorization and scoped queries remain authoritative. No production fallback to development secrets or SQLite.

Required environment configuration: secrets from environment, database URL/config, allowed origins as needed, no committed credentials, Neon TLS, production/demo safe configuration. Exact variable names follow the existing repository unless separately approved. Do not make new env vars mandatory solely from this documentation. Neon connections require provider-compatible TLS validation; migration/release job uses the direct migration connection, runtime pooling uses transaction-local scope and is tested for leakage.

Release sequence: build → run reviewed migration once → explicit one-time validated synthetic seed → register approved artifact/instruments → start API and single scheduler → start frontend → readiness/security/rehearsal checks. Never train or seed every API startup. No manual Neon schema edits. No migrations with runtime credentials. Roll back application only to schema-compatible versions; prefer a forward corrective migration over destructive downgrade. Backups/restoration and deletion tombstones must be verified before any later real-data deployment; this contract does not authorise one.

PWA caches versioned static assets only; authenticated HTML, API responses and questionnaire drafts use no-store and bypass service-worker caching. Logout clears in-memory state and any accidental sensitive cache. Offline pages show reconnect instructions; no queued assessment/approval mutations. Trust forwarded headers only from configured reverse proxies. Ship prepared accounts securely out of band, no committed demo passwords.

## 8. Acceptance

Cover every endpoint with response-schema and server-side role/unit/person/case/purpose authorization tests, including scoped repository projections, reused pooled connections, revoked sessions, unit changes, missing authenticated scope and expired consent. Verify that application endpoints/jobs never return unauthorized private data; do not claim direct SQL is protected by inactive RLS. Exercise mutation replay, failed audit, invalid input, cross-unit IDs, CSRF, cookie flags and no-store. Test scenario stale approval/implementation and source hashes, concurrent decisions, actual-vs-proposed mismatch and partial outcomes. External-browser release rehearsal must cover all four roles and demonstrate unavailable-model and privacy-denial paths.


## 9. Remaining payload details

Scenario creation accepts `window_start` at a UTC midnight not before the current
operational/demo date, and `window_end=window_start+14 days`. Selected pseudonyms
must all be in the assigned unit. Each manual replacement is `{shift_id,
from_pseudo_id,to_pseudo_id}`; optimization uses the selected group for candidate
moves but checks whole-unit effects. Returned assignment entries are `{shift_id,
pseudo_id,start_at,end_at,locked}`. Duplicate/conflicting replacements are rejected.
No identity or private fields are accepted in scenario reasons/inputs. All references
are resolved server-side inside unit scope.

User creation accepts username, one role, required unit/person binding and a secret
password provisioned out of band. User PATCH permits username, is_active, role and
unit_id only, never password_hash or personnel_id; validate role/binding compatibility.
There is no Admin login-as/reset-to-read-private-data capability. Prepared account
recovery is an operator-controlled process outside the public API with audited
revocation, not unrestricted Admin impersonation.

Audit API returns no case text, private assessment IDs/scores or sensitive source
row values. Own access history may identify the owner's own assessment resource;
Admin receives only resource kind, safe opaque reference and action metadata.
Collection withdrawal also revokes active sharing grants for that instrument and
invalidates new convergence reads. Previously stored owner results remain readable.
Model registry activation and policy activation are audited compare-and-swap actions;
new policy versions never mutate old results. Policy changes affecting model features
require a matching evaluated artifact before prediction can resume.

## 10. BALANCE / Scenario Contract

**Reconciliation revision 1 — 2026-10-04.** Architecture owns scenario constraints, objective, projections and workflow; ml.md owns the analytics called by this workflow. These are reconciled contract definitions, not previously locked optimizer implementation choices.

Under `BALANCE_SYNTHETIC_DEMO_POLICY_V1`, the planning horizon is 14 days. Required inputs are effective unit/operational-role context, published shift requirements and assignments, availability/approved leave, fixed training, skills, locked assignments, deployment restrictions and complete boundary history. Source coverage manifests and source/policy hashes bind a scenario snapshot. Missing constraints or planning inputs return INPUT_UNAVAILABLE, not a feasible empty plan. Existing duties alone do not establish staffing demand or future availability.

Hard constraints dominate all improvement objectives: required coverage per shift, required skill, effective service/unit eligibility, availability/approved leave, fixed training unavailability, no overlapping assignments, locked assignments and deployment restrictions. The locked synthetic-demo limits are minimum inter-duty rest 8 hours, maximum 60 duty hours in a rolling 7-day window and maximum 6 consecutive duty days. These values are prototype governance only, not military doctrine, CAPF regulation, law or medical guidance. Validate whole-unit effects, including every recipient of moved work; do not reduce one person's load by silently violating another's constraints. Validate temporal boundaries outside the planning window needed for rest/consecutive checks. A known violation is INFEASIBLE; missing required evidence is INPUT_UNAVAILABLE. No unknown check may be returned as PASS.

Use the MVP transparent deterministic greedy/feasibility-repair and hill-climb approach. `BALANCE_SOFT_OBJECTIVE_POLICY_V1` fixes this lexicographic order after every hard constraint passes: (1) maximize recovery opportunity, (2) improve workload/night-duty distribution, (3) minimize assignment movement/disruption. Stable ID-based ties are allowed. Hard constraints are never traded for a soft improvement. Do not invent numerical weights, combined scores, guaranteed WSI/wellbeing improvement or global optimality. Return a validated feasible incumbent separately from a timeout/no-feasible-result; failure to find a plan is not proof that none exists. A valid unchanged plan has zero change, not fabricated improvement.

Evaluate current and proposed schedules through the same projection adapter/policy and horizon. Show duty-hour/night-duty distributions, consecutive-duty runs, projected inter-duty/off-duty opportunities and coverage/constraint results for the selected group and whole unit. State assumptions and affected recipients. Forecast WSI only when all seven component projection rules and required inputs are approved and available, with consistent before/after normalization; otherwise projected WSI is null with reasons while valid schedule measures remain visible. Never apply a fixed percentage reduction to WSI, reuse one snapshot as both schedules, or present off-duty opportunity as measured sleep.

Returned projections include metric definitions, current/proposed/difference (proposed minus current), denominators, coverage, assumptions, constraint evidence and source/policy/calculation versions. Approval and external implementation require fresh revalidation. No optimizer or scenario endpoint changes the published roster, approved leave or actual duty records.

Scenario metadata uses the existing typed JSON fields and includes schema_version, immutable scenario_version, parent_id for MODIFY, planning_window, source_hash, policy_hash, generated_at, coverage/provenance and normalized planning inputs. A modified proposal is a new immutable child. `expected_revision` is a server-derived stable hash/ETag. Before ACCEPT and before implementation, lock and reauthorize the scenario, verify the revision, recompute its source hash and recheck policy. Changed evidence returns 409 SOURCE_CHANGED and requires regeneration/review; no silent reapproval.

## 11. VERIFY / Outcome Measurement Contract

For an exact-as-approved external action, Commander may explicitly attest `confirm_approved_assignments=true` instead of resending assignment identifiers. The server derives the complete approved assignment list, records that attestation, and still performs all freshness and constraint checks. This mode is mutually exclusive with `actual_assignments`; it never changes the published roster.

**Reconciliation revision 1 — 2026-10-04.** Approval means accepted, implementation pending. The existing implementation endpoint accepts a tagged result: IMPLEMENTED requires the actual effective time, assignments and external reference; NOT_IMPLEMENTED requires an authorised recorded-at timestamp and bounded reason_code, without fabricated actual assignments or an implementation record. An APPROVED scenario may become NOT_IMPLEMENTED; this is a terminal action outcome, not observed improvement. Retain immutable approval/audit evidence. No new mandatory table is introduced; persistence mapping remains subject to database review. Idempotency/revision/security rules apply to both results.

IMPLEMENTED history cannot be revised, rejected or superseded retroactively. A later change is a fresh scenario against the current published plan, with optional same-unit context_scenario_id referring to earlier implementation for context; parent_id is only an unimplemented proposal revision chain. Record any later actual change separately with its own effective time. Check temporal overlaps and identify which approved assignments are effective in each interval; never overwrite previous implementation/outcome evidence.

`VERIFY_POLICY_V1_SYNTHETIC_DEMO` fixes W=14 days. For actual implementation effective time u, use matched UTC intervals before=[u-14 days,u) and after=[u,u+14 days). OBSERVED is forbidden until the full after window exists and mandatory manifest-certified operational coverage has zero unknown gaps. Clip actual duty intervals; date-only daily records contribute only fully contained UTC days, with omitted boundary days and coverage disclosed. Bind the implementation, frozen affected group, source hashes/coverage manifest and calculation policy. Whole-unit summaries are separately labelled; never select only people with improving records after seeing the outcome.

| Observed metric | Calculation and interpretation |
|---|---|
| Duty/night load | Sum actual duty hours and count actual night duties per window; show per-person/observed-person-day denominators for comparisons |
| Recovery opportunity | Mean valid rest_hours and rest_gap_hours, separately labelled with source/proxy meaning and coverage |
| WSI | Mean and peak of valid daily WSI using compatible seven-factor policies; per-person deltas before any group aggregate |
| Coverage/constraints | Actual fulfilled required slots / required slots, with validated constraint violations; zero demand has no ratio |
| Adherence | Approved changed assignments actually fulfilled in ingested duty history / approved changed assignments with observable evidence in the window; no approved changes means not applicable, not automatic success |
| Difference | After minus before for the same metric/units/group; no clipping of deterioration and no automatic claim of benefit |

Mandatory categories are duty-hours load, night-duty load/distribution, measured rest opportunity/rest gaps, valid compatible WSI mean/peak/per-person change where available, staffing/required-slot coverage and approved-change adherence/actual execution evidence. An optional metric may be individually NOT_COMPUTED. Missing mandatory evidence keeps VERIFY overall unavailable. Do not zero-fill missing people/days or report incomplete WSI as improvement. A zero activity measure is valid only with confirmed complete coverage. Return metric-specific availability/reasons, eligible/excluded counts and window coverage. Required wording: “Observed operational indicators changed after implementation; this comparison does not establish that the intervention caused the change.”

Outcome workflow is PENDING while the observation clock has not completed, then OBSERVED after the window closes, and REVIEWED on authorised human review. Availability is independent: NOT_COMPUTED while pending; VALID only for required complete comparable evidence; INSUFFICIENT_HISTORY for insufficient comparable observations. Computational/source errors retain canonical error states and reasons. REVIEWED preserves availability and measured values; INSUFFICIENT_HISTORY is never a workflow enum. Missing implementation or NOT_IMPLEMENTED has no invented observation window/improvement.

Independent leave follow-up uses (u,u+30 days] and the exact qualifying event/eligibility rules in ml.md §12.1, including event-specific occurrence times. It may remain PENDING or insufficient after operational observation completes. Follow-up results are observed events, not a retrospective model probability or causal success claim. Synthetic replay uses a visibly declared clock and historical data; a new approval cannot instantly produce observed outcomes.

The named Stage-1 policies and values are locked versioned synthetic-demo policy under ml.md §8.1. Runtime configuration must match them exactly; missing/mismatched policy yields explicit unavailable output. The Model-A 30-day prediction horizon remains separate. ACCEPTED != IMPLEMENTED remains unchanged.
