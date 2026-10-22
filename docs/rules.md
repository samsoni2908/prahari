# PRAHARI — Binding Product, Safety and Privacy Rules

This file is an active binding product/privacy contract under AGENTS.md. Detailed analytics definitions are owned by ml.md. Binding for every application role, API, query, job, export and screen. [AGENTS.md](../AGENTS.md) defines the locked solution; [architecture.md](architecture.md) supplies enforcement mechanics.

**Canonical rule set:** this file records binding product boundaries. Current implementation and verification status is tracked separately in [task.md](task.md).

## Product boundaries

Required: WSI, personal baseline, trend, peer anomaly, one operational prediction, explanations, feasible balancing, human approval, external implementation recording, outcome verification, private Personnel self-check/support, welfare follow-up and auditability.

Forbidden: diagnosis of depression/PTSD/anxiety/burnout or other disorders; suicide/self-harm prediction; labels of mental weakness or unfitness; automatic duty/leave decisions; promotion/posting/transfer/disciplinary recommendations; connecting scores to punitive endpoints; mandatory wearables/biometrics; live individual GPS/patrol/convoy/video tracking; synthetic accuracy presented as real-world validity. Biometrics are outside this MVP, including optional ingestion.

Do not describe missing information as healthy. Do not describe pseudonymization as irreversible anonymization. Pseudonymous detail can still identify people within a small unit and remains access-controlled.

## Exact disclosure matrix

| Data/capability | PERSONNEL | WELFARE_OFFICER | COMMANDER | ADMIN |
|---|---|---|---|---|
| Profile and service identity | Own | Named search/case handling in assigned unit, audited | Pseudonymous operational projection only | Master-data management |
| Operational history, WSI, Model A and explanations | Own | Assigned-unit pseudonymous lists; authorised cases | Assigned-unit aggregates and pseudonymous detail | Import/system health; no individual welfare scoring dashboard |
| Raw self-check answers | Own only | Never | Never | Never |
| Private scores/trends | Own | Specifically shared assessments in an authorised case only | Never | Never |
| Evidence convergence | Own | Same consent-scoped case only | Never | Never |
| Confidential support text and case notes | Own request and personnel-visible updates | Assigned-unit case workflow | Never | Never |
| Scenario proposals/comparisons | Own recorded action summary | Draft/recommend in assigned unit | Draft/decide/record implementation in assigned unit | Safe audit metadata only |
| Audit | Own permitted access history | Scoped case actions/access | Scoped scenario actions | Redacted governance metadata |

One assigned unit per Commander/Welfare account for MVP; no implicit parent-unit inheritance. Scope is checked on each request using current account assignment. Transfers revoke previous unit access to the person; existing cases are withdrawn/unassigned with reason UNIT_TRANSFER, and Personnel may explicitly open a new case in the new unit; past unit aggregates remain scoped and suppressed. Admin cannot impersonate Personnel or use role changes to inherit their private data; immutable account-person binding and account-change auditing are required.

Welfare priority lists use `pseudo_id`, never name/photo. Named search is a distinct authorised case-handling action requiring a purpose reason; search results contain identity and unit only, not risk/result fields. Opening/creating a case and identity access are audited. Commander never receives names/service codes through scenario exports or error messages. No general private-data export endpoint exists.

## Consent and private processing

Self-check collection consent and sharing consent are separate, unchecked by default, versioned and revocable. Declining either never affects operational scores, access to service records or eligibility for support.

Collection consent is per instrument/version and notice version. Submission requires active collection consent. Personnel can read their stored history after withdrawal; no new assessment/trend/convergence processing uses withdrawn collection data. Collection withdrawal also revokes its instrument-sharing grants immediately.

Sharing consent is for an explicit list of assessment IDs (including any previous result needed for a trend) and one support case. It never includes future assessments automatically. Confidential case contents require assigned-officer access. Recipient is the currently assigned Welfare Officer for that case; reassignment invalidates grants until Personnel renews them. A grant expires on withdrawal, case closure or reassignment, whichever is first. Sharing expiry, where used, is governed by an approved/versioned privacy policy; no fixed duration is locked by this document. API reads re-check grants; no stale shared cache remains visible. Withdrawal cannot undo a human's prior knowledge; say this in the notice.

Allowed shared fields: assessment ID, instrument/version, assessment date, raw-total score (instrument total, not item answers), instrument-specific derived percentage/display value where the approved instrument legitimately defines one, score direction, comparison date/total/delta, descriptive trend, availability and consent expiry. Never share item values, question text, free-text assessment answers or responses embedded in explanations. No score/trend copies in case notes; derive the shared panel live. Welfare notes must stay about action/follow-up and avoid copying private assessment content.

Engine B and convergence run in the private boundary. Operational job interfaces/repository queries must never access raw/private derived tables. Commander/Admin do not receive participation counts, consent state, private alerts or blended scores that could reveal private changes. Support requests work without any assessment or sharing consent.

Security enforcement is `APPLICATION_AUTHORIZATION_AND_QUERY_SCOPING`: FastAPI/server-side authentication and role/unit/person/case/purpose/consent enforcement, scoped repository queries and explicit response projections. PostgreSQL RLS is `DEFERRED_NOT_ACTIVE`; correctness and privacy cannot depend on inactive RLS. Stage 2 does not enable/FORCE RLS or introduce RLS-specific principals. Optional future RLS hardening requires separate user approval and does not relax these privacy requirements.

## Aggregation and inference limits

Operational aggregates require a versioned/configurable minimum eligible-person threshold defined by the approved privacy policy. Count people, not records; show eligible denominator and missing-data count only when disclosure-safe. Suppress small cells and complementary totals that would reveal them. A suppressed value is `null` with `SUPPRESSED`, never zero. If complementary suppression cannot protect a partition, suppress the whole partition.

Aggregate dimensions must be explicitly allowlisted and must not permit combinations that defeat minimum-cell suppression or reveal private/individual information. Restrict adjacent comparisons that reconstruct suppressed cells. Authorised individual operational access is a separate capability, not granted by satisfying the aggregation floor. Never aggregate private wellbeing into Commander/Admin analytics.

## Truthful state and language

Availability is separate from operational attention. Canonical analytics states (owned by ml.md): `VALID`, `REST_DATA_MISSING`, `INSUFFICIENT_HISTORY`, `BASELINE_UNAVAILABLE`, `PEER_COHORT_INSUFFICIENT`, `MODEL_UNAVAILABLE`, `DATA_STALE`, `NOT_COMPUTED`, `COMPUTATION_ERROR`, `WELLBEING_NOT_COMPLETED`, `CONSENT_WITHDRAWN`. Privacy/workflow/display states (not replacements for analytics states): `NOT_SHARED`, `INSTRUMENT_UNAVAILABLE`, `SUPPRESSED`.

`LOW`, `MEDIUM`, `HIGH` are operational attention bands, not availability or medical categories. Invalid/unavailable calculation values are `null` with a reason. Historical last-valid values, if shown, are separately labelled with their original timestamp. No catch-all zero, hardcoded probability, fallback healthy badge or silent default input.

Use operational workload/recovery strain, rising trend, rest gap, night-duty concentration, staffing pressure, support requested and model unavailable. Instrument names and the quoted problem statement may retain their original language. Product screens must not imply clinical diagnosis or a universal mental-health percentage.

## Actions, alerts and audit

Every proposed scenario is checked against coverage, skills, availability, approved leave, fixed training, locked assignments, overlap, deployment restrictions, minimum rest, rolling duty hours and consecutive duty constraints. Under `BALANCE_SYNTHETIC_DEMO_POLICY_V1`, the planning horizon is 14 days, minimum inter-duty rest is 8 hours, maximum duty is 60 hours in 7 days and maximum consecutive duty days is 6. These are synthetic-prototype governance values, not Indian Armed Forces doctrine, CAPF regulation, law, medical guidance or real deployment policy. No silent relaxation. Missing mandatory input is `INPUT_UNAVAILABLE`; a proven violation with complete input is `INFEASIBLE`. Neither state may be accepted. Accept/Modify/Reject requires actor, reason, revision and time. Approval alone never changes operational source records.

Alerts are explainable, source-linked, dated, versioned, deduplicated and scoped. Under `OPERATIONAL_ATTENTION_POLICY_V1_SYNTHETIC_DEMO`, MEDIUM remains visible without automatic alert/notification emission. HIGH emits only after two consecutive valid daily cutoffs. Invalid/unavailable cutoffs break that streak without becoming LOW or resolving an alert. An unresolved OPEN/ACKNOWLEDGED alert suppresses the same trigger family; after resolution, a seven-day cooldown applies before another emission. These values are controlled synthetic-demo policy, not real-force doctrine. Alerts request human review, not automatic action. [ml.md](ml.md) owns calculation details; [architecture.md](architecture.md) defines transitions. Audit reads of private/case data, decisions, imports, consent, account/scope changes and model/policy activation. Never log passwords, tokens, raw answers, private totals or confidential request/note text.

Operational inference, BALANCE and VERIFY require immutable, versioned, operational-only coverage manifests bound to deterministic database-derived source hashes. Required windows have zero unknown gaps. Empty source data never means zero activity. Private wellbeing data never enters these manifests. If required coverage cannot be proved, return the applicable `NOT_COMPUTED`, `INSUFFICIENT_HISTORY` or `DATA_STALE` state.

Per-user notifications contain bounded server-template text and reauthorize their referenced resource at list, count, detail and navigation time. They never contain raw wellbeing answers, private scores, support narratives, private participation or Commander-visible private convergence. Loss of resource authorization must not leak existence through notification content or counts.

## Data and prototype claims

Targets are observable operational events in the synthetic world; no fabricated clinical labels or labels derived from WSI/model output. Version features, target rules, preprocessing, model artifact and policy. Separate chronological fitting, calibration, selection and testing. Historical models are not current until compatibility and evaluation gates pass.

Demo policies are engineering defaults, not CAPF-approved duty standards or clinically validated thresholds. Only synthetic/demo personnel records and prepared accounts may be deployed. Withdrawal blocks new private processing as applicable and does not itself erase history. Deletion and retention of private answers, results, support text, consent and audit evidence must follow an approved privacy policy; no fixed durations are locked by this document. Backups and private data must respect the approved privacy lifecycle. No automatic deletion of existing repository/user data is authorised by this documentation task.

## Scope cuts

Cut visual polish, advanced explainers, advanced optimizer, speculative forecasting and production-only infrastructure first. Never cut the core loop including VERIFY, privacy, role isolation, truthful states, private support or audit. If a required model/instrument is unavailable, expose that limitation and mark the corresponding acceptance gate incomplete.
