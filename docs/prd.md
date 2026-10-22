# PRAHARI — Product Requirements

Status: Canonical implementation contract. The current verified implementation state is tracked in [task.md](task.md). Challenge and scope mapping: [problem-statement.md](problem-statement.md). Binding safety/privacy: [rules.md](rules.md).

## Product and success

PRAHARI brings fragmented operational records into one explainable workflow: **DETECT → EXPLAIN → BALANCE → HUMAN DECISION → VERIFY**, alongside voluntary private wellbeing and support. It must answer what operational pattern changed, why it matters, what feasible alternative exists, who decided, what was actually implemented and what was observed afterward.

The controlled SIH prototype uses synthetic records and prepared accounts. It demonstrates software behavior and synthetic prediction, not diagnosis or real-world efficacy. A leave-pattern event is a limited organisational proxy; it does not establish psychological distress or fully satisfy a clinical interpretation of the challenge's stress/burnout language.

## Required capabilities

| ID | Requirement | Acceptance evidence |
|---|---|---|
| R01 | Exactly four authenticated roles and unit/person scope | Cross-role/cross-unit/pooled-connection isolation tests |
| R02 | Validated operational ingestion with as-of provenance | Atomic import, duplicate replay, invalid-row rejection and completeness tests |
| R03 | Seven-factor WSI with current drivers | 77.50 reference, normalization boundaries, missing/invalid input tests |
| R04 | Personal baseline, EWMA and peer anomaly | Prior-only history, signed zero-MAD handling, sparse cohort/gap tests |
| R05 | One 30-day leave-pattern prediction | Event/eligibility tests, leakage checks, persisted pipeline and chronological evaluation |
| R06 | Explanations and truthful availability | Separate WSI contributions/model attribution; no fabricated LOW on failure |
| R07 | Feasible 14-day what-if/optimizer alternatives | Constraint checks, deterministic replay, infeasible and missing-input cases |
| R08 | Human Accept/Modify/Reject | Revision checks, mandatory reason, stale proposal refusal and audit |
| R09 | External implementation record and outcome verification | Approval has no roster side effect; actual-action timestamp and complete observation windows |
| R10 | Approved instrument-specific voluntary private self-checks | Instrument-specific scoring, consent, separate results/trends and rights/version prerequisites |
| R11 | Optional support and scoped derived sharing | Support without assessment; consent expiry/withdrawal/reassignment tests |
| R12 | Welfare follow-up and evidence convergence | Named case handling, pseudonymous lists, private-only convergence and immutable action history |
| R13 | Explainable review alerts | Deduplication, cooldown, acknowledgement/resolution and no automatic operational action |
| R14 | Admin governance and data/model health | No private result access; audited imports, role changes and policy/model activation |
| R15 | Responsive PWA and controlled cloud demo | Four external-browser flows, static-only offline behavior, same backend/database |

## Role journeys

**Personnel:** login → own recovery/operational history → privacy notice → optional instrument choice/consent → private answers/result/trend → optional support → request status and access history. Show separate operational and private sections. Personnel can withdraw sharing/collection consent. They cannot browse another person. No compulsory assessment/reminders or participation penalty.

**Commander:** assigned-unit overview → LOW/MEDIUM/HIGH and unavailable operational lists → pseudonymous strain card → operational explanation → 14-day what-if/optimizer → compare → Accept/Modify/Reject → separately record external implementation → review outcomes. No wellbeing, support-request contents or convergence fields. Names/service codes are not returned in this journey.

**Welfare Officer:** assigned-unit pseudonymous attention filters → authorised named case search/open with purpose → operational context → explicitly shared derived instrument results, if any → explanatory convergence → support/action/follow-up → case closure. Welfare can draft a workload scenario and send it for Commander review, but cannot accept or activate one. Action suggestions are workload review, discussion/support contact and referral to configured support services; no automated treatment recommendations.

**Admin:** users/roles/unit assignments → personnel/unit master data → source import/validation → policy versions → model/job health → redacted audit. Admin has no private scoring screen, no personnel impersonation, and no welfare/roster approval power.

## Scope and interface ownership

[architecture.md](architecture.md) owns API routes, payloads, authentication, state transitions, BALANCE/scenario constraints, VERIFY/outcome measurement and deployment. [database.md](database.md) locks the Stage-1 minimal schema delta and records remaining physical reconciliation requirements. [ml.md](ml.md) owns analytics, target/feature definitions and versioned analytics policies. [design.md](design.md) owns screens/tokens and interaction states. [task.md](task.md) owns implementation dependencies and evidence status.

The target MVP includes locked Model A operational intelligence and a separate voluntary private wellbeing/support path. Current Engine B state is `INSTRUMENT_NOT_ACTIVATED`, `NOT_TRAINED`, `NOT_SHARED`; historical wellbeing rows are `LEGACY_UNGOVERNED` and cannot activate or validate it. Model C is locked to `v1.1-truthful-source`: no weighted combined score/probability and no private convergence for Commander. If B is unavailable/unshared while A is available, report `OPERATIONAL_EVIDENCE_ONLY`. `NO_ELEVATED_EVIDENCE` is allowed only when both governed sources are available/shared and independently non-elevated.

The controlled demo uses `OPERATIONAL_ATTENTION_POLICY_V1_SYNTHETIC_DEMO`, `BALANCE_SYNTHETIC_DEMO_POLICY_V1`, `SOURCE_COVERAGE_POLICY_V1_SYNTHETIC_DEMO`, `BALANCE_SOFT_OBJECTIVE_POLICY_V1`, `VERIFY_POLICY_V1_SYNTHETIC_DEMO` and `SESSION_SECURITY_POLICY_V1`. These are locked target contracts awaiting implementation. Their numeric duty/rest, alert and observation values are synthetic prototype governance values, not real-force doctrine or validated welfare-effect claims.

Only approved/validated instrument-version-language combinations may be enabled. Additional languages require appropriate validated/approved wording and usage evidence. Secure validated CSV ingestion is the HRMS integration boundary for the demo; a live HRMS connector is deferred. Browser PWA is required; native Android wrapper is optional. No mandatory external notification provider or biometric integration.

## Non-functional acceptance

- Authenticated sensitive responses use `Cache-Control: no-store`; offline mode offers only the static shell and reconnect guidance.
- No secret/token/private content in URLs, browser storage, logs, analytics telemetry or error messages.
- Dataset/analytics views show synthetic status, as-of date, coverage and version provenance. Loading, empty, denied, stale, unavailable and suppressed states are distinct.
- Performance must be measured and documented against the actual controlled demo dataset/environment. Exact performance thresholds are not locked by this documentation reconciliation.
- Accessibility includes keyboard access, visible focus, labelled forms, chart text equivalents and readable contrast at mobile/tablet/desktop sizes.
- Deployed access requires HTTPS, revocable sessions, tested server-side authorization and scoped repository/query projections, and prepared accounts. Enforce role/unit/person/case/purpose/consent boundaries; PostgreSQL RLS remains deferred/not active and is not a correctness dependency. No public signup or real personnel data.

## End-to-end release demonstration

Run and record the end-to-end controlled demo rehearsal against a reproducible seed, resetting only disposable test/demo state with explicit operator action:

1. Import valid synthetic source history; show malformed input rejection without partial records.
2. Open a pseudonymous rising-workload example and explain real computed WSI, baseline and prediction.
3. Generate a feasible alternative and an intentionally infeasible one; explain binding constraints.
4. Accept a valid revision; demonstrate no source roster change. Record an actual external implementation and show a separate completed historical observation example.
5. Complete available approved private instrument assessment(s), where prerequisites are satisfied, share selected results into a support case, then revoke sharing and prove access stops.
6. Demonstrate Commander/Admin private-data denial, unit isolation and safe audit history.
7. Remove the model artifact in an isolated test; prediction becomes unavailable while independently valid WSI remains visible.

A current proposal cannot instantly acquire observed outcomes. Historical synthetic before/after records may demonstrate VERIFY with dates visibly labelled. Outcomes describe association, not causal proof of welfare improvement.

## Release claims and prerequisites

Use “synthetic-data prototype” and state what was actually tested. Required prerequisites are approved instrument wording/version/usage prerequisites, a compatible evaluated Model A artifact, complete source/event history, configured support contact, and a successfully tested canonical migration chain. An unavailable prerequisite is a tracked release limitation; it must not be replaced with a fake success state.
