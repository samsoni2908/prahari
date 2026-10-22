# PRAHARI — SIH 26186

PRAHARI is a privacy-preserving operational workload and recovery decision-support prototype for uniformed services. It implements the human-controlled workflow:

`DETECT → EXPLAIN → BALANCE → DECISION → IMPLEMENTATION → VERIFY`

The application has exactly four roles: `PERSONNEL`, `WELFARE_OFFICER`, `COMMANDER`, and `ADMIN`. Private voluntary wellbeing data is kept separate from command analytics. PRAHARI does not diagnose mental-health conditions or automate consequential personnel decisions.

## Repository layout

| Path | Purpose |
|---|---|
| `backend/` | FastAPI application, SQLAlchemy models, Alembic migrations, analytics and tests |
| `frontend/` | Next.js responsive web/PWA application |
| `mobile/` | Unified Android WebView wrapper for the deployed HTTPS application |
| `data/seed26186/` | Synthetic, non-operational demo and model-governance fixtures |
| `database/` | Reviewable schema/reference SQL; Alembic remains the migration authority |
| `docs/` | Canonical product, architecture, database, ML, design and task contracts |
| `.github/workflows/` | CI, secret scanning and secure Android release build |

`delete/`, local environment files, signing keys, APKs and generated build output are intentionally excluded from version control.

## Prerequisites

- Docker Desktop with Docker Compose
- Node.js 20 for native frontend development
- Python 3.14 for native backend development

## Run locally with Docker

1. Copy `.env.example` to `.env`.
2. Replace all development passwords and `SECRET_KEY`; never commit `.env`.
3. Start the stack:

```bash
docker compose up --build
```

The backend applies the authoritative Alembic migration chain before starting. Open the frontend at `http://localhost:3000`; backend health is available at `http://localhost:8000/health`.

To stop the services without deleting database data:

```bash
docker compose stop
```

## Development checks

Backend dependencies are reproducibly constrained by both manifests:

```bash
python -m pip install -r backend/requirements.txt -c backend/requirements.lock
cd backend
python -m pytest -q
```

Database-backed tests require an isolated PostgreSQL 16 database and must never target retained development or production data.

Frontend checks:

```bash
cd frontend
npm ci
npm run lint
npm run typecheck
npm run build
```

## Database authority

`backend/alembic.ini` and `backend/alembic/canonical/` are the single migration authority for local PostgreSQL and hosted PostgreSQL deployments. Files under `backend/alembic/history/` and `database/` are retained references, not a second active migration chain.

## Android release

The unified Android wrapper contains no separate business logic and must use an HTTPS deployment URL. Signed releases are built by `.github/workflows/build-apks.yml` with repository secrets; keystores and credentials must never be committed. Local debug builds use `mobile/build-apks.ps1`.

## Canonical documentation

Read [AGENTS.md](AGENTS.md) first, followed by [rules](docs/rules.md), [product requirements](docs/prd.md), [architecture](docs/architecture.md), [database](docs/database.md), [analytics/ML](docs/ml.md), [design](docs/design.md), and the current [task status](docs/task.md).

All included datasets are synthetic and support software demonstration only. They do not establish real-world predictive or clinical validity.
