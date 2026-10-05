# PRAHARI Frontend Connectivity Preservation Map (Chunk 0)

**Project:** SIH 26186 — PRAHARI  
**Scope:** Frontend Architecture & Connectivity Audit  
**Status:** FROZEN CONNECTIVITY CONTRACT — PRESENTATION UPGRADE ONLY

---

## 1. Absolute Preservation Directives

All existing frontend API consumers, state managers, handlers, query schemas, and session controls are **STRICTLY PROTECTED**. Visual upgrades must follow the safe refactoring pattern:
```
page.tsx (or view component)
  ├── SAME API hook / service call
  ├── SAME state variables & dispatchers
  ├── SAME event handlers & form submissions
  └── NEW / UPGRADED PRESENTATIONAL UI (<NewPrahariView ... />)
```

No existing API endpoint, payload structure, authentication session method, or role-guard logic may be modified or replaced with mock data in production paths.

---

## 2. File Classification Matrix

### Category A: PRESENTATION (Safe to Redesign / Upgrade)
- `frontend/app/globals.css` (Visual styling, color tokens, typography)
- `frontend/tailwind.config.ts` (Theme extensions, font families, radius tokens)
- `frontend/ui/styles.css` (Component-specific CSS rules)
- `frontend/ui/theme.ts` (Theme constants and design tokens)
- `frontend/ui/widgets/*` (StatCard, RiskBadge, Modal, Toast, Skeleton, EmptyState)
- `frontend/components/charts/*` (WsiTrendChart, WsiDonutChart, DriverBarChart, ScenarioCompareChart)

### Category B: MIXED UI + LOGIC (Preserve Logic & Handlers Exactly, Upgrade Presentation)
- `frontend/app/page.tsx` (Public Landing & Portal Entrypoint)
- `frontend/app/login/page.tsx` (Login page presentation)
- `frontend/app/commander/page.tsx` (Commander Operational Suite UI & charts)
- `frontend/app/welfare/page.tsx` (Welfare Officer Portal & Case Management UI)
- `frontend/app/personnel/page.tsx` (Personnel Member Self-facing Portal UI)
- `frontend/app/admin/page.tsx` (Admin Governance & Telemetry UI)
- `frontend/components/layout/AppShell.tsx` (Application navigation shell, topbar, mobile drawer)
- `frontend/ui/layout/Shell.tsx`, `frontend/ui/layout/Header.tsx`, `frontend/ui/layout/Sidebar.tsx`

### Category C: CONNECTIVITY / DATA LAYER [CONNECTIVITY_PROTECTED — READ ONLY]
- `frontend/lib/api.ts` (HTTP client, CSRF bootstrap, session persistence, typed endpoints: `authApi`, `commanderApi`, `welfareApi`, `personnelApi`, `adminApi`)
- `frontend/types/personnel.ts` (Personnel entity types)
- `frontend/types/risk.ts` (Risk and WSI entity types)
- `frontend/types/user.ts` (User identity types)
- `frontend/types/wellbeing.ts` (Wellbeing response types)

### Category D: AUTH / ROUTING / STATE INFRASTRUCTURE [CONNECTIVITY_PROTECTED — READ ONLY]
- `frontend/middleware.ts` (Edge session cookie guard & route redirection)
- `frontend/lib/auth-context.tsx` (React Context for authentication, mobile lockout, role routing)
- `frontend/lib/auth.ts` (Session types, role dashboard route resolver)
- `frontend/lib/permissions.ts` (Role-based access permissions & private wellbeing boundary check)
- `frontend/ui/auth/RoleGuard.tsx` (Client-side role protection wrapper)

---

## 3. Page Connectivity & Handler Inventory

### 1. Public Landing & Login
- **PAGE:** Public Landing & Secure Portal Entry
- **CURRENT ROUTE:** `/` and `/login`
- **CURRENT DATA SOURCE:** `authApi.login(username, password)`, `authApi.csrf`
- **API CLIENT / SERVICE:** `lib/api.ts` -> `authApi`
- **HOOK / STORE / CONTEXT:** `useRouter`, `useState`, `lib/auth-context.tsx`
- **FORM SUBMIT HANDLER:** `handleLogin(e?: React.FormEvent)`
- **SEARCH HANDLER:** None
- **FILTER HANDLER:** None
- **PAGINATION:** None
- **ROLE/ACCESS LOGIC:**
  - Automatic role redirect (`COMMANDER` -> `/commander`, `WELFARE_OFFICER` -> `/welfare`, `PERSONNEL` -> `/personnel`, `ADMIN` -> `/admin`).
  - Session stored via HttpOnly cookie `prahari_session` + localStorage `prahari_role`/`prahari_user`.
- **NAVIGATION DEPENDENCIES:** `useRouter`, `middleware.ts`
- **CURRENT WORKING ACTIONS:**
  - `fillCredentials(username, password)` (Demo test account fast-fill)
  - `handleLogin(e)` (Authenticates against backend endpoint `/api/v1/auth/login`)
  - Error banner display upon invalid credentials.

### 2. Commander Operational Suite
- **PAGE:** Commander Operational Suite & Readiness Monitoring
- **CURRENT ROUTE:** `/commander` (Aliases: `/commander/unit-overview`, `/commander/workload`, `/commander/risk-trends`, `/commander/deployment`, `/commander/leave`, `/commander/reports`, `/commander/settings`)
- **CURRENT DATA SOURCE:**
  - `commanderApi.getOverview()`
  - `commanderApi.getUnitStats()`
  - `commanderApi.getDeployments()`
  - `commanderApi.getLeave()`
  - `commanderApi.getWorkload()`
  - `commanderApi.getRiskTrends()`
- **API CLIENT / SERVICE:** `lib/api.ts` -> `commanderApi`
- **HOOK / STORE / CONTEXT:** `useState`, `useEffect`, `useRouter`, `useSearchParams`
- **FORM SUBMIT HANDLER:** None (Operational read-only decision support)
- **SEARCH HANDLER:** None
- **FILTER HANDLER:** Tab switcher (`overview`, `workload`, `deployments`, `leave`, `trends`)
- **PAGINATION:** None (Aggregates)
- **ROLE/ACCESS LOGIC:** Restricted to `COMMANDER` and `ADMIN`. Unit-level aggregates only. Strictly zero raw individual wellbeing data.
- **NAVIGATION DEPENDENCIES:** `AppShell.tsx`, `roleRouteMap`
- **CURRENT WORKING ACTIONS:**
  - `loadData()` (Fetches all unit operational metrics in parallel)
  - Refresh button trigger
  - Tab navigation
  - Interactive SVG WSI trend curves & Driver bar charts.

### 3. Welfare Officer Portal
- **PAGE:** Welfare Officer Portal & Case Management
- **CURRENT ROUTE:** `/welfare` (Aliases: `/welfare/search`, `/welfare/personnel`, `/welfare/personnel/[id]`, `/welfare/risk-monitor`, `/welfare/assessments`, `/welfare/alerts`, `/welfare/actions`, `/welfare/reports`, `/welfare/settings`)
- **CURRENT DATA SOURCE:**
  - `welfareApi.searchPersonnel(query, riskFilter)`
  - `welfareApi.getPersonnelProfile(personnelId)`
  - `welfareApi.getPersonnelHistory(personnelId)`
  - `welfareApi.getPersonnelRisk(personnelId)`
  - `welfareApi.getPersonnelWellbeing(personnelId)`
  - `welfareApi.getPersonnelFactors(personnelId)`
  - `welfareApi.recordWelfareAction(personnelId, payload)`
  - `welfareApi.listCases(status)`
  - `welfareApi.getCaseDetail(requestId)`
  - `welfareApi.updateCase(requestId, payload)`
- **API CLIENT / SERVICE:** `lib/api.ts` -> `welfareApi`
- **HOOK / STORE / CONTEXT:** `useState`, `useEffect`, `useRouter`, `useSearchParams`
- **FORM SUBMIT HANDLER:** `handleRecordAction(e: React.FormEvent)` (Submits `MONITOR`, `CONTACT_PERSONNEL`, `WELFARE_FOLLOWUP`, or `RECORD_OUTCOME`)
- **SEARCH HANDLER:** `handleSearch()` triggered by search input state
- **FILTER HANDLER:** `riskFilter` (`ALL`, `LOW`, `MEDIUM`, `HIGH`) and sub-tabs
- **PAGINATION:** Personnel list array rendering
- **ROLE/ACCESS LOGIC:** Restricted to `WELFARE_OFFICER`. Authorized individual case management; derived wellbeing status only (zero raw responses).
- **NAVIGATION DEPENDENCIES:** `AppShell.tsx`, `roleRouteMap`
- **CURRENT WORKING ACTIONS:**
  - Personnel search by query string
  - Risk tier filter buttons
  - `openProfile(personnelId)` (Opens 7-tab personnel dossier: overview, service, deployment, leave_rest, training, wellbeing, risk)
  - `handleRecordAction(e)` (Saves welfare action with audit trail)
  - `loadCases()` (Fetches active cases).

### 4. Personnel Member Portal
- **PAGE:** Personnel Self-Facing Portal & Voluntary Wellbeing
- **CURRENT ROUTE:** `/personnel` (Aliases: `/personnel/profile`, `/personnel/wellbeing`, `/personnel/duties`, `/personnel/leave`, `/personnel/deployment`, `/personnel/risk`, `/personnel/support`, `/personnel/settings`)
- **CURRENT DATA SOURCE:**
  - `personnelApi.getProfile()`
  - `personnelApi.getConsent()`
  - `personnelApi.updateConsent(action)`
  - `personnelApi.getMyRisk()`
  - `personnelApi.getMyDeployments()`
  - `personnelApi.getMyDuties()`
  - `personnelApi.getMyLeave()`
  - `personnelApi.listSelfChecks()`
  - `personnelApi.submitSelfCheck(answers)`
  - `personnelApi.listSupportRequests()`
  - `personnelApi.createSupportRequest(payload)`
  - `personnelApi.getPrivacyHistory()`
- **API CLIENT / SERVICE:** `lib/api.ts` -> `personnelApi`
- **HOOK / STORE / CONTEXT:** `useState`, `useEffect`, `useAuth`
- **FORM SUBMIT HANDLER:**
  - `handleSubmitSelfCheck(e)` (Submits 4-factor voluntary ratings)
  - `handleCreateSupport(e)` (Submits confidential assistance request)
  - `handleToggleConsent()` (Activates/withdraws voluntary consent)
- **SEARCH HANDLER:** None
- **FILTER HANDLER:** Tab navigation (`dashboard`, `profile`, `duties`, `leave`, `wellbeing`, `support`, `privacy`)
- **PAGINATION:** Array lists for checkins and requests
- **ROLE/ACCESS LOGIC:** Restricted to `PERSONNEL` (Service Member). Strict private self-check boundary.
- **NAVIGATION DEPENDENCIES:** `AppShell.tsx`, `roleRouteMap`
- **CURRENT WORKING ACTIONS:**
  - Consent toggle
  - 4-slider self-check submission
  - Support request filing
  - Personal duty/leave/deployment ledger inspection
  - Privacy access history review.

### 5. System Administration & Governance
- **PAGE:** Admin Governance & Telemetry Portal
- **CURRENT ROUTE:** `/admin` (Aliases: `/admin/users`, `/admin/personnel`, `/admin/units`, `/admin/data`, `/admin/system`, `/admin/settings`)
- **CURRENT DATA SOURCE:**
  - `adminApi.getHealth()`
  - `adminApi.listUsers(limit, offset)`
  - `adminApi.createUser(payload)`
  - `adminApi.updateUser(userId, payload)`
  - `adminApi.listPersonnel(limit, offset)`
  - `adminApi.listUnits()`
  - `adminApi.listPolicies()`
- **API CLIENT / SERVICE:** `lib/api.ts` -> `adminApi`
- **HOOK / STORE / CONTEXT:** `useState`, `useEffect`, `useAuth`
- **FORM SUBMIT HANDLER:**
  - `handleCreateUser(e)` (Creates new user with role and Argon2id hash)
  - `handleToggleUserActive(userId, currentActive)`
- **SEARCH HANDLER:** In-memory user filter
- **FILTER HANDLER:** Tab switcher (`dashboard`, `users`, `personnel`, `units`, `data`, `system`)
- **PAGINATION:** Query params `limit` and `offset`
- **ROLE/ACCESS LOGIC:** Restricted to `ADMIN`. System governance only; no clinical/welfare decisions from model outputs. Desktop console only.
- **NAVIGATION DEPENDENCIES:** `AppShell.tsx`, `roleRouteMap`
- **CURRENT WORKING ACTIONS:**
  - System health check telemetry refresh
  - Create user form submission
  - User status toggle (activate/deactivate)
  - Personnel master records inspection
  - Unit master records inspection
  - Policy configuration inspection.

---

## 4. Protected Files Registry (CONNECTIVITY_PROTECTED)
The following files contain core connectivity, session cookies, route guards, or endpoint mappings and **MUST NOT BE MODIFIED** during the presentational redesign:
1. `frontend/lib/api.ts`
2. `frontend/lib/auth-context.tsx`
3. `frontend/lib/auth.ts`
4. `frontend/lib/permissions.ts`
5. `frontend/middleware.ts`
6. `frontend/types/*`
7. `frontend/ui/auth/RoleGuard.tsx`
