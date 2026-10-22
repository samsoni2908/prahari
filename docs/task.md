# PRAHARI — Implementation and Verification Status

Read [AGENTS.md](../AGENTS.md) first. This file records current implementation evidence and remaining release work; it does not override the canonical product, privacy, architecture, database, ML, or design contracts.

## Current implementation

The four-role application and complete human-controlled workflow are implemented through real API, service, repository and PostgreSQL paths:

`DETECT → EXPLAIN → BALANCE → ACCEPT / MODIFY / REJECT → IMPLEMENTATION → VERIFY`

Implemented boundaries include:

- exactly four application roles with server-side scope enforcement;
- truthful unavailable/error states rather than fabricated healthy values;
- source-gated WSI, baseline, EWMA, peer anomaly and governed Model-A inference;
- explainable, constraint-checked scenario generation with no automatic roster mutation;
- immutable human decision, implementation and verification records;
- a separate private Personnel wellbeing/support path with restricted Welfare projections;
- Admin master-data, import health, configuration, job/model status and audit governance;
- responsive web/PWA routes and one HTTPS Android wrapper using the same backend.

Engine B remains governed by its explicit instrument/consent availability state. Synthetic evidence must not be represented as real CAPF or Armed Forces validation.

## Verification evidence

Latest stabilization evidence supplied and executed before repository preparation:

| Check | Result |
|---|---|
| Backend suite against isolated PostgreSQL 16 | 233 passed |
| Frontend lint and TypeScript checks | Passed |
| Frontend production build | Passed; 39 routes |
| Four-role browser/responsive matrix | Passed; 12 role/viewport combinations and 28 navigation links |
| Unified release APK | Built and cryptographically verified |
| APK policy | `org.prahari.app`, min SDK 24, target SDK 34, cleartext disabled, v2 RSA-3072 signature |

These results do not claim cloud deployment or real-world model validation.

## Migration and artifact authority

- `backend/alembic.ini` selects only `backend/alembic/canonical/`.
- The canonical chain is `b26186_baseline → c26186_implementation → d26186_leave_lifecycle → e26186_stage2_schema → f26186_stage4_planning_sources`.
- `backend/alembic/history/` preserves superseded migration history without activating it.
- `backend/app/ml/saved/model_a_governed_artifact.joblib` and its manifest are the governed runtime artifact pair.
- Missing, corrupt, incompatible or uncertified model/source state remains explicitly unavailable.

## Repository release gate

Before the first GitHub commit:

- stage only the reviewed allowlist; never use `git add .`;
- retain `delete/` locally and keep it ignored;
- exclude secrets, signing keys, generated APKs/builds, raw archives and private-answer fixtures;
- verify the exact staged snapshot builds independently;
- run staged whitespace and secret-leak checks;
- confirm the Git remote targets the intended PRAHARI repository;
- obtain explicit user approval before committing or pushing.

## Remaining external limitations

- Physical installation/testing of the signed APK requires an available Android device.
- Cloud deployment, Neon migration, production secrets and external HTTPS rehearsal require deployment credentials and an approved environment.
- Repository identity verification confirmed that the renamed PRAHARI destination is the original repository; no remote correction is required.
- Real operational predictive validity is unverified; included data and validation are synthetic/demo evidence only.
- Model-A target provenance remains explicitly unresolved: reproducible metrics on the frozen v3.0-labelled validation cohort do not prove that its target contract is equivalent to the artifact/runtime `v2.1-approved-leave-lifecycle` identifier. Preserve the governed artifact and runtime gates unchanged pending authoritative evidence.
