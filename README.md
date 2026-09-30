# SWASTI — AI-Powered Personnel Stress & Welfare Monitoring System

> **Smart India Hackathon 2024 · Problem Statement SIH 26186**  
> *Advanced Welfare Decision-Support & Fatigue Monitoring Platform for Defence & Armed Forces Personnel*

---

## 1. System Overview

**SWASTI** is an AI-powered welfare decision-support system designed to monitor operational stressors and voluntary well-being indicators for armed forces personnel. It provides early-warning risk detection to welfare officers and aggregate organizational readiness insights to unit commanders while strictly preserving individual privacy through cryptographic and architectural isolation.

### Exactly Four Roles (Role-Based Access Control)

| Role | Access Scope | Operational Responsibilities |
|---|---|---|
| **Personnel** | Own Records Only | Personal profile, duties, deployments, leave balance, voluntary confidential well-being check-in, personal risk trend, and welfare support requests. |
| **Commander** | Unit-Level Aggregates Only | Battalion overview, personnel availability, leave & workload distributions, aggregate risk trends, and operational reporting. **Zero access to private individual well-being answers.** |
| **Welfare Officer** | Authorized Personnel Cases | Search authorized personnel, individual 8-tab welfare dossier (service, deployments, duties, leave, rest, training, well-being, risk factors), and welfare action logging. |
| **Admin** | System Master Data | User management, personnel records, unit configuration, audit trail inspection, and data synchronization. **Zero involvement in welfare intervention decisions.** |

---

## 2. Evaluation Credentials

The system provides demonstration accounts for evaluation across all four roles:

| Role | Username | Default Password | Primary Dashboard Route |
|---|---|---|---|
| **Personnel** | `personnel` | `prahari123` | `/personnel` |
| **Commander** | `commander` | `prahari123` | `/commander` |
| **Welfare Officer** | `welfare` | `prahari123` | `/welfare` |
| **Administrator** | `admin` | `prahari123` | `/admin` |

*Unified Login*: All users authenticate through the single common login page at `/login`. The system inspects credentials, issues an HttpOnly session cookie, and routes users to their authorized operational console.

---

## 3. Architecture & Privacy Safeguards

```
[ Browser / Unified Mobile APK ]
              │
              ▼
[ Next.js 14 Frontend (:3000) ]
   └── Next.js Rewrites Proxy (/api/* ──► Backend Internal URL)
              │
              ▼
[ FastAPI Backend Gateway (:8000) ]
   ├── Authentication & RBAC (Argon2id + PyJWT + HttpOnly Cookie)
   ├── SlowAPI Rate Limiter (--proxy-headers --forwarded-allow-ips=*)
   ├── Dual-Track ML Inference Engine (Track A: HR, Track B: Wellbeing)
   └── APScheduler (Nightly batch inference with daily idempotency guard)
              │
              ▼
[ PostgreSQL 16 Database (:5432) ]
   ├── Operational & HR Tables (Units, Personnel, Duties, Deployments, Leaves)
   ├── Derived Risk Scores & Alerts (ModelOutput, Alert, Outcome)
   └── Quarantined Vault (wellbeing_private — strictly isolated from Commander & Welfare)
```

### Privacy Firewall
- **Raw Survey Quarantine**: Responses to voluntary assessments (`wellbeing_private`) remain exclusively accessible to the individual soldier.
- **Welfare Officer Access**: Receives only derived risk categories, trend trajectories, and objective contributing factors.
- **Commander Access**: Receives unit-level aggregates with an aggregation floor ($N \ge 5$) to prevent re-identification.
- **No Automatic High-Stakes Decisions**: Risk indicators inform human welfare review; the platform never automatically denies leave, alters duty rosters, or initiates administrative actions.

---

## 4. Quick Start (Docker Compose)

The entire full-stack system can be brought up locally in one command:

### Prerequisites
- Docker Engine 24+ & Docker Compose v2+
- Ports `3000`, `8000`, and `5432` available

### Running the System
```bash
# 1. Clone repository
git clone https://github.com/samsoni2908/Prahari.git
cd Prahari

# 2. Configure environment
cp .env.example .env

# 3. Boot full-stack services
docker compose up --build -d
```

### Accessing Services
- **Web Application**: [http://localhost:3000](http://localhost:3000)
- **Backend API & Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- **Liveness Health Probe**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 5. Cloud Deployment Ready

SWASTI is pre-configured for production container deployment:
- **`railway.toml`**: Configured with automated migrations (`alembic upgrade head`), production Uvicorn worker, proxy headers, and `/health` probe.
- **Next.js Reverse Proxy**: Uses `rewrites()` in `next.config.mjs` to proxy `/api/*` to the private backend, allowing `SameSite=lax` HttpOnly cookies to operate seamlessly across microservices.
- **Dual-Track ML Engine**: Pre-calibrated risk models enable real-time risk classification and objective contributing factor breakdown.

---

## 6. License & Compliance

Developed for the Smart India Hackathon (SIH 26186). Designed in alignment with Armed Forces welfare monitoring standards and data protection principles.
