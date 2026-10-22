# PRAHARI — Coding Agent Entry Point

**Project:** SIH 26186 — PRAHARI
**Version:** 6.0
**Status:** FINAL — AUTHORITATIVE ENTRY POINT

---

## 1. Purpose

PRAHARI is a privacy-preserving personnel welfare and operational workload/recovery decision-support system for CAPFs, Armed Forces, and other uniformed services.

The system must:
1. detect elevated, unusual, or rising operational workload/recovery strain;
2. explain the operational drivers behind that signal;
3. predict one defined observable near-term organisational outcome;
4. generate feasible workload/roster alternatives under hard constraints;
5. require an authorised human to Accept / Modify / Reject;
6. verify what happened after the human-approved intervention;
7. provide Personnel with a separate private voluntary wellbeing/self-check and support path.

PRAHARI is **not** a clinical diagnosis system.

---

## 2. Read Order

Before changing implementation, read only the files relevant to the task, in this order:

1. `AGENTS.md` — entry point and operating rules.
2. `docs/rules.md` — absolute product, safety, privacy, and terminology constraints.
3. `docs/prd.md` — product scope, four roles, user capabilities, and success criteria.
4. `docs/architecture.md` — system architecture, security boundaries, data flow, APIs, deployment.
5. Relevant specialist contract:
   - `docs/database.md` for schema, migrations, data relationships and deferred optional RLS hardening.
   - `docs/ml.md` for WSI, baseline, anomaly, prediction, evaluation, explainability.
   - `docs/design.md` for UI/UX, routes, interactions, responsive behavior.
6. `docs/task.md` — approved implementation sequence and current task status.
7. If present locally, `MEMORY.md` — non-authoritative implementation history and continuation context only; it is intentionally excluded from the public repository.

Do not reread the whole repository when a focused task only requires a small set of files.

### Authority rule

- Canonical product files must agree with each other.
- `MEMORY.md`, audit reports, archived documents, generated reports, and historical model cards do **not** override current canonical product contracts.
- Files under `docs/archive/` or marked `HISTORICAL`, `LEGACY`, `EXPERIMENTAL`, or `SUPERSEDED` are non-authoritative.
- If two current canonical files conflict, **do not silently choose one or invent a compromise**. Report the conflict before implementing it.
- When the user explicitly approves a changed decision, update the affected canonical specification before changing code.

---

## 3. Core Product Loop

```text
DETECT
  ↓
EXPLAIN
  ↓
BALANCE
  ↓
HUMAN DECISION
  ↓
VERIFY
```

### DETECT
Use operational/service data to calculate:
- WSI/current operational strain;
- personal baseline deviation;
- EWMA trend;
- peer/context anomaly;
- defined 30-day leave-pattern anomaly prediction.

### EXPLAIN
Show understandable operational reasons such as:
- high duty load;
- night-duty concentration;
- recovery/rest deficit;
- deployment intensity;
- leave gap/disruption;
- staffing pressure;
- significant change from personal baseline.

### BALANCE
Generate **what-if** workload/roster alternatives.

Every proposed alternative must be checked against applicable constraints such as:
- staffing/coverage;
- required skill;
- approved leave;
- availability;
- minimum rest;
- consecutive-duty limits;
- deployment constraints.

The system may propose alternatives. It must never silently activate them.

### HUMAN DECISION
An authorised human reviews a proposal and chooses:

```text
ACCEPT
MODIFY
REJECT
```

A model or optimizer must never make a consequential operational decision by itself.

### VERIFY
After an approved intervention, record the action and compare appropriate before/after operational indicators over an approved observation window.

---

## 4. Exactly Four Application Roles

Only these application roles exist:

1. `PERSONNEL`
2. `WELFARE_OFFICER`
3. `COMMANDER`
4. `ADMIN`

There is **no fifth `AUDITOR` application role**.

Auditability remains a system capability. Authorised audit/governance records are handled through the Admin/system governance path and role-scoped access rules defined in the canonical specifications.

Do not add, restore, seed, route, test, or document an `AUDITOR` login/dashboard unless the user explicitly changes this locked decision.

### Role boundaries

#### PERSONNEL
May access:
- own profile and permitted operational history;
- own private voluntary wellbeing/self-check;
- own raw self-check answers;
- own private result/trend;
- own support requests;
- own permitted access history.

Must never access another person's private data.

#### WELFARE_OFFICER
May access authorised welfare cases and permitted operational context required for welfare support.

May receive only the wellbeing information explicitly permitted by the privacy contract.

Must not receive unrestricted raw question-by-question private wellbeing answers.

#### COMMANDER
Receives authorised unit operational/readiness information, workload trends, operational strain indicators, explanations, and permitted what-if scenarios.

Must not receive raw private wellbeing answers.

Commander-facing functionality is operational decision support, not clinical assessment.

#### ADMIN
Manages:
- users and the four role assignments;
- personnel/unit master data;
- system configuration;
- data/import health;
- policies;
- model/job status;
- authorised audit/governance records.

Admin is not a welfare superuser and must not make personnel welfare decisions from model outputs.

---

## 5. Locked Technology and Runtime Direction

### Application
- Frontend: Next.js + TypeScript.
- UI: Tailwind CSS + shadcn/ui.
- Charts: Recharts.
- Web experience: responsive PWA-first application.
- Backend: Python + FastAPI.
- ORM: SQLAlchemy 2.x.
- Validation/contracts: Pydantic / OpenAPI.
- Database engine: PostgreSQL 16.
- Schema migrations: Alembic.
- Analytics: Pandas + NumPy + scikit-learn.
- Scheduler: APScheduler.

### Analytics
- WSI: deterministic seven-factor operational index.
- Personal baseline: Median/MAD.
- Trend: EWMA.
- Peer anomaly: Isolation Forest.
- Prediction MVP: regularized Logistic Regression with governed preprocessing/calibration.
- Optimizer MVP: deterministic greedy/hill-climb or equivalent transparent constraint-aware approach.

Stretch technology must not become an MVP dependency:
- LightGBM + SHAP;
- OR-Tools CP-SAT;
- production-grade OIDC/SSO;
- full tamper-evident/hash-chained audit.

---

## 6. Database and Deployment Decision

### Local development/testing

```text
Next.js
   ↓
FastAPI
   ↓
PostgreSQL 16 in Docker
```

Docker PostgreSQL remains the reproducible local development/test database.

### SIH deployed demo

```text
Invigilator Browser / Unified App Wrapper
                ↓ HTTPS
           Next.js Web/PWA
                ↓ HTTPS
              FastAPI
                ↓ SSL
         Neon PostgreSQL
```

Locked deployment direction:
- Frontend/backend: Railway-compatible cloud deployment.
- Deployed demo database: **Neon PostgreSQL**.
- Local database: **Docker PostgreSQL**.
- Local and cloud databases must be created from the **same authoritative Alembic migration chain**.
- Do not manually create a separate cloud schema in the Neon dashboard.
- `database/schema.sql`, if retained, is a reviewable snapshot/reference, not a second migration authority.

The deployed SIH system is a controlled demo, not a public service:
- authentication is required;
- no public signup;
- prepared demo accounts only;
- synthetic/demo personnel data only;
- web and mobile wrapper use the same deployed backend/database.

The optional Android wrapper must point to the deployed HTTPS application and must not become a separate business-logic codebase.

---

## 7. WSI Contract

Locked reference formula:

```text
WSI = 0.25D + 0.20R + 0.15C + 0.15N + 0.10L + 0.10H + 0.05S
```

All components are normalized to `0–100`.

Reference test:

```text
D = 78
R = 85
C = 90
N = 80
L = 70
H = 65
S = 40

WSI = 77.50
```

Non-finite, invalid, or insufficient inputs must produce an explicit unavailable/invalid state rather than a fabricated valid score.

---

## 8. Prediction Contract

The supervised operational prototype target is:

```text
Y = 1
if a defined leave-pattern anomaly occurs
within the next 30 days after prediction cutoff,
else 0.
```

Rules:
- features use only information available at or before the prediction cutoff;
- future leave fields must never become input features;
- target/future/hidden-process columns must never enter the feature matrix;
- synthetic hidden recovery-deficit variables may be used to generate a synthetic world but must never become model features;
- the target must never be generated from the model's own score;
- training, evaluation, and inference must use the same persisted preprocessing contract;
- missing/unavailable model state must be shown explicitly;
- synthetic validation must never be presented as real CAPF/Armed Forces predictive validity.

---

## 9. Private Wellbeing Contract

Private wellbeing is a separate path:

```text
PERSONNEL
   ↓
NOTICE / CONSENT
   ↓
VOLUNTARY SELF-CHECK
   ↓
PRIVATE RAW ANSWERS
   ↓
PRIVATE RESULT / TREND
   ↓
OPTIONAL SUPPORT REQUEST
```

Rules:
- raw answers remain Personnel-private;
- no raw private wellbeing answers in Commander analytics;
- no raw private wellbeing answers in Admin operational analytics;
- Welfare Officer receives only information explicitly permitted by the privacy contract;
- missing wellbeing participation must not increase operational risk;
- do not create a fake universal mental-health score;
- do not fabricate wellbeing prediction labels when longitudinal data is insufficient.

---

## 10. Absolute Product Boundaries

PRAHARI must not:
- diagnose depression, PTSD, anxiety, burnout, or any mental-health disorder;
- predict suicide or self-harm;
- label personnel as mentally weak, unfit, or psychologically unsafe;
- expose raw private wellbeing answers to command/admin analytics;
- automatically change duty/roster assignments;
- automatically approve or reject leave;
- make promotion, posting, transfer, disciplinary, or punitive decisions;
- connect risk outputs to such career/disciplinary endpoints;
- require wearables or mandatory biometrics;
- track live individual GPS, patrol movement, convoy movement, or live field video;
- fabricate healthy/LOW states when data or models are unavailable;
- present synthetic performance as real-world operational validation.

Use operational language such as:
- operational workload/recovery strain;
- rising trend;
- recovery/rest gap;
- night-duty concentration;
- workload increase;
- staffing pressure;
- support requested;
- insufficient history;
- model unavailable.

---

## 11. Truthful State Rule

Never convert missing/error/unavailable state into a reassuring numeric value.

Valid examples:

```text
VALID
LOW
MEDIUM
HIGH

INSUFFICIENT_HISTORY
MODEL_UNAVAILABLE
DATA_STALE
COMPUTATION_ERROR
NOT_COMPUTED
```

A missing model must never silently become `LOW`.

A missing dashboard metric must never silently become a hardcoded healthy value.

Demo/synthetic values must come through the normal data/API path or be clearly marked as demo fixtures.

---

## 12. Code Ownership and Maintainability

Use:

```text
API → Service → Repository → Database
          ↘
          Analytics
```

Responsibilities:
- API: authentication dependency, validation, response/error translation.
- Service: business rules, authorization, state transitions, transaction orchestration.
- Repository: scoped persistence/query logic.
- Database: relational constraints, indexes and grants. PostgreSQL RLS remains deferred/not active; optional future hardening requires separate user approval. Current access enforcement belongs to server-side authorization and scoped repository/query projections.
- Analytics: deterministic typed inputs/outputs; no HTTP/session coupling.
- Frontend: render state and collect user actions; do not own backend business rules.

Rules:
- no SQL inside API routers;
- no substantive business rules in React;
- no giant generic `utils.py`, `services.py`, or `models.py` dumping grounds;
- do not duplicate active implementations;
- preserve compatibility shims only when a real consumer still requires them;
- do not delete files merely because they are empty without proving they are obsolete;
- every important module should have clear purpose, inputs, outputs, security/privacy behavior, errors, and tests.

---

## 13. Implementation Operating Rule

Before any meaningful implementation task:

```text
1. Read AGENTS.md.
2. Read only the relevant canonical specifications.
3. Inspect the actual current implementation.
4. Identify exact files and consumers involved.
5. Classify changes: KEEP / MODIFY / MOVE / DELETE / CREATE.
6. Make the smallest coherent change that satisfies the contract.
7. Run relevant tests.
8. Report what actually passed and what was not verified.
9. Update task/MEMORY only with truthful implementation state.
```

Never:
- rewrite the whole repository merely because one subsystem is wrong;
- delete historical/user data without explicit instruction;
- claim a test/build/deployment passed when it was not executed successfully;
- use old audit reports as implementation requirements;
- reintroduce the fifth Auditor role from historical specifications;
- replace real missing functionality with hardcoded success/fallback values.

---

## 14. Current Documentation Rule

The canonical documentation set is intended to be:

```text
AGENTS.md
docs/rules.md
docs/prd.md
docs/architecture.md
docs/database.md
docs/ml.md
docs/design.md
docs/task.md
README.md
```

`MEMORY.md` is optional local agent history, not part of the public canonical documentation set. It remains ignored because it may contain obsolete implementation history, machine-specific context and superseded decisions.

Old or conflicting specifications should be moved to `docs/archive/` and clearly marked:

```text
HISTORICAL — NOT AUTHORITATIVE
```

Do not keep multiple active files that claim to be the final contract for the same subsystem.

---

## 15. Goal

Build a stable SIH prototype that demonstrates:

```text
fragmented operational data
        ↓
early detection
        ↓
clear explanation
        ↓
feasible human-reviewed action
        ↓
measured outcome
```

while preserving the separate private Personnel wellbeing/support path.

The goal is a trustworthy, explainable, privacy-preserving decision-support prototype — not maximum feature count and not artificial architectural complexity.
