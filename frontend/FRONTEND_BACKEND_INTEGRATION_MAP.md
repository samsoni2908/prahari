# PRAHARI Frontend-Backend Integration Map

**Project:** SIH 26186 — PRAHARI  
**Scope:** UI View Models, Data Contracts & Action Handlers  
**Status:** UI_UPGRADE_COMPLETE — BACKEND_INTEGRATION_PENDING

---

## 1. Overview
This map documents the dynamic data requirements, view models, and user actions for every major screen in the upgraded PRAHARI frontend. All existing API connections, schemas, and endpoints have been strictly preserved.

---

## 2. Screen Integration Inventory

### Screen 1: Public Landing Page
- **Route:** `/`
- **Expected View Model:** Static public presentation with live session detection (`getStoredRole()`)
- **Backend Data Needed:** Client-side session state
- **User Actions:**
  - "Access Secure Portal" (routes to `/login`)
  - "Enter Your Portal" (if already authenticated, routes to designated role portal)
- **Integration Status:** `UI_COMPLETE`

---

### Screen 2: Portal Authentication & Login
- **Route:** `/login`
- **Expected View Model:** `AuthCredentialsViewModel` (username, password, showPassword, remember)
- **Backend Data Needed:**
  - `POST /api/v1/auth/csrf` (CSRF token handshake)
  - `POST /api/v1/auth/login` (username, password -> returns `{ access_token, user: { id, username, role, unit_id, personnel_id } }`)
- **User Actions:**
  - Demo fast-fill accounts
  - Credential input & password visibility toggle
  - Submit login (`handleLogin`)
- **Integration Status:** `PRESERVED_LIVE_AND_CONNECTED`

---

### Screen 3: Welfare Officer Portal & Case Management
- **Route:** `/welfare`
- **Sub-Tabs:** `search` (Authorized Personnel Roster), `cases` (Active Support Cases)
- **Expected View Models:**
  - `PersonnelSummaryViewModel`: `{ id, pseudo_id, rank_or_grade, role_title, unit_name, risk_band, risk_score, consent_status }`
  - `WelfareCaseViewModel`: `{ id, personnel_id, pseudo_id, rank_or_grade, unit_name, request_type, priority, status }`
  - `PersonnelDossier7TabViewModel`:
    - Overview: `{ status, joining_date, active_alerts_count, location, alerts: [] }`
    - Service History: `[{ id, posting_type, location_label, start_date, end_date, notes }]`
    - Deployment: `[{ id, deployment_type, location_label, start_date, end_date, intensity_level }]`
    - Leave & Rest: `{ leaves: [], rests: [] }`
    - Training: `[{ id, training_name, start_date, end_date, hours, status }]`
    - Wellbeing: `{ consent_status, assessments_count, recent_assessments: [] }` (Metadata only — zero raw answers)
    - Risk Analysis: `{ current_wsi, risk_band, baseline, prediction, contributing_factors: [] }`
- **Backend Data Needed:**
  - `GET /api/v1/welfare/personnel/search?query=...&risk_filter=...`
  - `GET /api/v1/welfare/cases`
  - `GET /api/v1/welfare/personnel/{id}`
  - `POST /api/v1/welfare/personnel/{id}/actions`
- **User Actions:**
  - Personnel query search input
  - Risk band filter buttons (`ALL`, `LOW`, `MEDIUM`, `HIGH`)
  - Review 7-tab personnel dossier in slide-out drawer
  - Record human welfare action (`MONITOR`, `CONTACT_PERSONNEL`, `WELFARE_FOLLOWUP`, `RECORD_OUTCOME`)
  - Open active case profile
- **Integration Status:** `PRESERVED_LIVE_AND_CONNECTED`

---

### Screen 4: Commander Operational Suite
- **Route:** `/commander`
- **Sub-Tabs:** `overview`, `workload`, `deployments`, `leave`, `trends`
- **Expected View Models:**
  - `CommanderOverview`: `{ unit, kpis, distribution, drivers }`
  - `UnitStatsViewModel`: `{ available_strength, required_strength, coverage_percent }`
  - `DeploymentsViewModel`: `{ active_field_count, static_base_count, sectors: [] }`
  - `LeaveViewModel`: `{ on_leave_count, pending_count, emergency_count, approval_rate }`
  - `WorkloadViewModel`: `{ avg_weekly_hours, night_shift_percentage, avg_consecutive_days, sub_units: [] }`
  - `RiskTrendsViewModel`: `[{ date, wsi, mean_wsi }]`
- **Backend Data Needed:**
  - `GET /api/v1/commander/overview`
  - `GET /api/v1/commander/unit/stats`
  - `GET /api/v1/commander/unit/deployments`
  - `GET /api/v1/commander/unit/leave`
  - `GET /api/v1/commander/unit/workload`
  - `GET /api/v1/commander/unit/risk-trends`
- **Privacy Boundary:** Unit-level aggregates only. Strictly zero raw individual psychometric responses.
- **User Actions:**
  - Tab navigation
  - Refresh telemetry trigger
  - Chart interactions & hover inspection
- **Integration Status:** `PRESERVED_LIVE_AND_CONNECTED`

---

### Screen 5: Personnel Member Portal
- **Route:** `/personnel`
- **Sub-Tabs:** `dashboard`, `profile`, `duties`, `leave`, `wellbeing`, `support`, `privacy`
- **Expected View Models:**
  - `PersonnelProfileViewModel`: `{ pseudo_id, personnel_code, rank_or_grade, service_years, unit, postings: [] }`
  - `ConsentViewModel`: `{ consented, status }`
  - `RiskViewModel`: `{ current_risk_score, risk_band, current_ewma, baseline_mean, trend: [] }`
  - `DutyViewModel`: `[{ id, duty_date, duty_type, shift_type, is_night, hours }]`
  - `LeaveViewModel`: `[{ id, leave_type, days, start_date, end_date, status }]`
  - `SelfCheckViewModel`: `[{ id, assessment_date, instrument_name, score }]`
  - `SupportRequestViewModel`: `[{ id, request_type, priority, request_text, status }]`
  - `PrivacyLogViewModel`: `[{ id, timestamp, action, result }]`
- **Backend Data Needed:**
  - `GET /api/v1/personnel/me`
  - `GET /api/v1/personnel/consent`
  - `POST /api/v1/personnel/consent` (Toggle consent)
  - `GET /api/v1/personnel/me/risk`
  - `GET /api/v1/personnel/me/deployments`
  - `GET /api/v1/personnel/me/duties`
  - `GET /api/v1/personnel/me/leave`
  - `GET /api/v1/personnel/self-checks`
  - `POST /api/v1/personnel/me/wellbeing` (Submit voluntary self-check answers)
  - `GET /api/v1/personnel/support-requests`
  - `POST /api/v1/personnel/support-request` (Submit confidential support request)
  - `GET /api/v1/personnel/privacy-history`
- **User Actions:**
  - Toggle voluntary consent
  - Submit 4-factor self-check ratings
  - File confidential support request
  - Inspect personal service and privacy access history
- **Integration Status:** `PRESERVED_LIVE_AND_CONNECTED`

---

### Screen 6: System Administration & Governance
- **Route:** `/admin`
- **Sub-Tabs:** `dashboard`, `users`, `personnel`, `units`, `data`, `system`
- **Expected View Models:**
  - `SystemHealthViewModel`: `{ database_status, table_record_counts: {} }`
  - `UserAccountViewModel`: `[{ id, username, role, is_active, created_at }]`
  - `UnitMasterViewModel`: `[{ id, unit_name, unit_code, unit_type, location_label, sanctioned_strength }]`
  - `PolicyViewModel`: `[{ id, name, details, active }]`
- **Backend Data Needed:**
  - `GET /api/v1/admin/health`
  - `GET /api/v1/admin/users`
  - `POST /api/v1/admin/users`
  - `PATCH /api/v1/admin/users/{id}`
  - `GET /api/v1/admin/personnel`
  - `GET /api/v1/admin/units`
  - `GET /api/v1/admin/policies`
- **User Actions:**
  - Create user with Argon2id hash and designated role
  - Toggle user active/inactive status
  - Review live PostgreSQL table record counts
  - Audit RLS policy configurations
- **Integration Status:** `PRESERVED_LIVE_AND_CONNECTED`
