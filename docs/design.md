# PRAHARI --- Final UI/UX + CSS Design Contract

**Version:** 7.0 --- Implementation contract\
**Project:** SIH 26186\
**Frontend:** Next.js + TypeScript + Tailwind CSS + shadcn/ui + PWA

## 1. Purpose

This is the final UI/UX and CSS contract for PRAHARI. The coding agent
must implement the screens, interaction behavior, visual hierarchy,
responsive behavior, accessibility states, and design tokens defined
here. It must not invent a different visual system page-by-page.

The approved visual direction is the existing warm cream and defence olive interface
with restrained gold accents, semantic green/amber/red
states, compact information-dense cards, clear charts and tables,
operational language, and a visually separated private Personnel
experience.

## 2. Locked Design Principles

### One screen = one decision

-   Unit Overview → understand unit health.
-   Priority List → choose what to inspect.
-   Strain Card → understand why the value is elevated.
-   What-if → explore an operational change.
-   Scenario Compare → compare alternatives.
-   Decision → approve, modify, or reject.
-   Outcome → verify what happened.
-   Personnel Self-check → privately complete a self-check.
-   Support → request confidential assistance.

### Core visual hierarchy

``` text
UNIT HEALTH
    ↓
WHERE IS STRAIN?
    ↓
WHY IS IT HAPPENING?
    ↓
WHAT CAN CHANGE?
    ↓
WHAT DOES THE SCENARIO DO?
    ↓
HUMAN DECISION
    ↓
OUTCOME
```

### Core loop

``` text
DETECT → EXPLAIN → BALANCE → HUMAN DECISION → VERIFY
```

## 3. Overall Visual Direction

PRAHARI should look modern, technical, calm, trustworthy, operational,
information-dense and premium enough for a competition/demo.

It must not look like a gaming HUD, cyberpunk interface, neon sci-fi
website, medical diagnosis dashboard, generic SaaS template,
glassmorphism showcase, or consumer fitness app.

Use polish through spacing, typography, hierarchy, subtle borders,
restrained gradients, charts and controlled status colors.

## 4. Application Shell

``` text
┌────────────────────────────────────────────────────────────────────┐
│ PRAHARI / SYSTEM TITLE       UNIT       DATE       USER / ALERTS   │
├──────────────┬─────────────────────────────────────────────────────┤
│              │                                                     │
│   SIDEBAR    │                    MAIN CONTENT                     │
│              │                                                     │
└──────────────┴─────────────────────────────────────────────────────┘
```

Desktop sidebar: `240px`. Collapsed: `72px`. Top bar: `64px`. Main
content padding: `24px`.

Mobile uses a drawer sidebar, 16px page padding, stacked layouts, and
touch-friendly actions.

## 5. Design Tokens

### Background

``` css
--background: #FBFBF8;
--background-secondary: #F3F2EB;
--surface: #FFFFFF;
--surface-raised: #F6F7F3;
--surface-hover: #ECF1EB;
```

### Text

``` css
--text-primary: #182417;
--text-secondary: #3B4B3A;
--text-muted: #677766;
--text-disabled: #9AA899;
```

### Primary

``` css
--primary: #2C5127;
--primary-hover: #1E3A1A;
--primary-muted: #EAF1E9;
```

### Semantic states

``` css
--state-normal: #15803D;
--state-normal-bg: #ECFDF5;

--state-elevated: #B45309;
--state-elevated-bg: #FFFBEB;

--state-critical: #B91C1C;
--state-critical-bg: #FEF2F2;

--state-info: #1D4ED8;
--state-info-bg: #EFF6FF;

--state-neutral: #4B5563;
--state-neutral-bg: #F3F4F6;
```

### Borders

``` css
--border-subtle: #E4ECE3;
--border-default: #CFDDCE;
--border-strong: #9EB19D;
--border-focus: #2C5127;
```

### Radius

``` css
--radius-sm: 6px;
--radius-md: 8px;
--radius-lg: 12px;
--radius-xl: 16px;
```

Default card radius: `16px`.

### Spacing

Use a 4/8-based scale:

``` text
4, 8, 12, 16, 20, 24, 32, 40, 48px
```

## 6. Typography

Recommended font:

``` css
font-family:
  Inter,
  ui-sans-serif,
  system-ui,
  -apple-system,
  BlinkMacSystemFont,
  "Segoe UI",
  sans-serif;
```

  Element          Size / Weight
  ---------------- ---------------
  Page title       24px / 600
  Section title    16px / 600
  Card title       14px / 600
  Body             14px / 400
  Secondary        12px / 400
  Small label      11px / 500
  KPI              28px / 700
  Decision value   32px / 700

## 7. Components

### Cards

``` css
background: var(--surface);
border: 1px solid var(--border-subtle);
border-radius: 16px;
padding: 16px;
```

Use raised surfaces only for meaningful elevation. Avoid heavy shadows
everywhere.

### Buttons

Primary: defence olive filled.\
Secondary: light surface + olive border.\
Destructive: red only for genuinely destructive actions.

Approval actions must visibly distinguish `Accept`, `Modify`, and
`Reject`.

### Status badges

``` css
display: inline-flex;
align-items: center;
gap: 6px;
padding: 3px 8px;
border-radius: 999px;
font-size: 11px;
font-weight: 600;
```

Operational attention uses `LOW`, `MEDIUM`, `HIGH`. Show availability separately
using [rules.md](rules.md): unavailable means neutral badge, null value and reason,
never a reassuring color or zero. Trend uses RISING/STABLE/FALLING. Scenario badges
use exact [architecture.md](architecture.md) states. No clinical CRITICAL band or
ambiguous fallback badge. CSS token names denote colors, not extra domain states.

## 8. Commander Screens

Commander-facing intelligence is operational Model A only. Do not show raw/private wellbeing, Engine B private trend, or a Model C/convergence output that could reveal a private self-check change.

### C01 Login

Minimal secure role-aware login with PRAHARI identity and institutional
sign-in with prepared credentials; production SSO is deferred.

### C02 Unit Overview

Required hierarchy:

``` text
COMMANDER DASHBOARD
Unit Health • Personnel Readiness • Operational Attention

KPI cards:
Strength | Staffing | Elevated Count | Alerts

Charts:
WSI 90-day trend | WSI distribution | Operational drivers
Rest-deficit heatmap | Night-duty pressure | Operational readiness

Bottom:
Priority personnel | Recent alerts | What-if entry
```

### C03 Priority List

Columns:

``` text
Pseudo ID | Rank | Unit | WSI | Trend | Main Driver | Status | Action
```

Risk-facing views use `pseudo_id`, not real names/photos.

### C04 Strain Card

Show:

``` text
Pseudonymous ID
WSI
Trend
Driver contributions
Personal baseline
EWMA
Operational context
Explain / What-if / Operational review
```

Drivers include duty load, rest deficit, consecutive duty, night-duty
concentration, leave gap, deployment/hardship and staffing pressure.

### C05 What-if

Current vs Proposed comparison:

``` text
WSI
Coverage
Skills
Night duties
Rest
Violations
Disruption
```

Flow:

``` text
Select change → Validate constraints → Calculate → Compare
```

No automatic roster change.

### C06 Optimise

Show optimization method, constraints, feasibility and binding
constraint.

MVP: greedy/hill-climb. Future CP-SAT must be explicitly labelled.

### C07 Scenario Compare

``` text
Metric | Current | Proposed
WSI peak
WSI average
Coverage %
Skills satisfied
Night-duty count
Rest-gap mean
Policy violations
Roster disruption
Projection assumptions and data coverage
```

### C08 Decision

Show recommendation, expected effects, constraints, warnings and:

``` text
[ Accept ] [ Modify ] [ Reject ]
```

Record actor, timestamp, revision, decision and reason. Acceptance records approval
only. A separate Record external implementation action collects actual assignments,
effective date and reference. Changed data requires revalidation and review.

### C09 Outcome

Show observed before/after metrics, WSI change, coverage/rest changes, actual
implementation/adherence and completeness. Separate projections from observations.
The approved versioned operational observation window and 30-day leave follow-up have independent
pending/complete states; show actual before/after dates. The 14-day scenario planning horizon does not set observation duration.
Separate outcome lifecycle from availability, and show approved/implementation-pending,
NOT_IMPLEMENTED and IMPLEMENTED truthfully. No instant outcome after approval.

## 9. Welfare Officer

Screens:

``` text
W01 Login
W02 Welfare Home
W03 Priority Cases
W04 Case Detail
W05 Support
W06 What-if
W07 Compare
W08 Recommendation
W09 Outcome
```

Welfare Home emphasizes priority cases, open alerts, pending follow-ups
and support requests.

Priority lists stay pseudonymous. Named search needs a case-handling purpose;
authorised named case access is audited. Only the assigned Welfare Officer receives
explicitly shared assessment results. Show each approved instrument separately with its own permitted result/trend and, where allowed, convergence. Never merge different instruments into a universal wellbeing score. NOT_SHARED reveals no participation. Welfare What-if,
Compare and Recommendation submit proposals; only Commander can approve or
record external implementation.

Raw private questionnaire answers are never shown.

## 10. Personnel PWA

The Personnel experience is visually separate, simpler, private and
mobile-first.

Screens:

``` text
P01 Login
P02 Privacy & Consent
P03 My Recovery
P04 Self-check
P05 Private Result
P06 My Trend
P07 Support
P08 Privacy / Data-use History
```

Private self-check results stay private. Do not create a command-facing
mental-health score.

Consent must clearly state collection, purpose, visibility and
optionality.

## 11. Admin

``` text
A01 Login
A02 Admin Home
A03 Units
A04 Personnel
A05 Data Sources
A06 Policies
A07 Roles & Access
A08 Models
A09 Audit
```

Admin focuses on system health, data freshness, jobs, policies,
configuration and governance. Raw private wellbeing, derived private results and confidential case contents are
never available to Admin.

## 12. Audit & Governance

Audit is a system capability handled through the authorized Admin/governance path; it is not a fifth application role.

Admin may review permitted:

-   audit records;
-   access history;
-   decision history;
-   security/compliance records.

This capability does not grant raw private wellbeing access or welfare-decision authority.

## 13. Charts

Use Recharts.

Recommended:

``` text
Line chart → WSI trend / EWMA
Bar chart → driver contribution
Donut → WSI distribution
Heatmap → rest deficit
Horizontal bars → operational drivers
Comparison bars → scenario before/after
```

Rules:

-   light chart surfaces;
-   subtle grid;
-   olive main series;
-   semantic colors only where meaningful;
-   readable legends and tooltips;
-   no rainbow palettes;
-   no 3D effects.

## 14. Responsive Design

Breakpoints:

``` text
Mobile:  < 640px
Tablet:  640–1023px
Desktop: ≥ 1024px
Wide:    ≥ 1440px
```

Mobile: single-column, drawer navigation, stacked cards,
scrollable/stacked tables, full-width charts, Current above Proposed.

Tablet: two-column layouts where useful.

Desktop: full sidebar, multi-column dashboard and optional right-side
detail panel.

## 15. Right-side Detail Panel

On wide screens, a focused detail panel may sit beside the main
dashboard:

``` text
MAIN DASHBOARD                         │ P1042
Unit Health                            │ WSI 84.2 ↑
WSI Trend                              │ Strain Card
Priority List                          │ Baseline
Alerts                                 │ EWMA
                                       │ Activity
                                       │ Explain
                                       │ What-if
                                       │ Operational review
```

On mobile this becomes a full-screen drawer/page.

## 16. Background Visual Treatment

A subtle defence/terrain visual may be used in the login, dashboard
header or sidebar footer.

It must be low contrast and never interfere with data.

No animated military vehicles, live video backgrounds or distracting
motion.

## 17. Motion

Allowed:

-   drawer/modal transitions;
-   tooltips;
-   loading;
-   chart entrance;
-   subtle hover transitions.

Not allowed:

-   flashing dashboards;
-   continuous pulsing;
-   rotating 3D objects;
-   decorative particle systems;
-   animated military vehicles.

Respect `prefers-reduced-motion`.

## 18. Loading / Empty / Error States

### No data

`No current data available. Showing the last successful sync when available.`

Never invent a score.

### Insufficient history

`Baseline unavailable. Not enough historical data for personal comparison.`

### No feasible roster

`No feasible roster found. Binding constraint: [constraint]`

### Model unavailable

`Prediction unavailable. Showing WSI, baseline and rule-based indicators.`

### Permission denied

`You do not have permission to view this information.`

Do not reveal hidden personnel details.

Never show raw stack traces to normal users.

## 19. Accessibility

Required:

-   keyboard navigation;
-   visible focus states;
-   sufficient contrast;
-   semantic HTML;
-   ARIA labels where required;
-   status not communicated by color alone;
-   readable button labels;
-   accessible chart values/tooltips;
-   table headings;
-   dialog focus management;
-   approximately 44px touch targets on mobile.

## 20. Privacy UI

Commander/Welfare:

``` text
Pseudonymous operational views
```

Personnel:

``` text
Private wellbeing view
```

Raw questionnaire responses are Personnel-only and must never appear in
command risk charts, WSI driver charts, Admin screens or operational
tables.

## 21. UI Language

### Use

``` text
Elevated workload/recovery strain
Rising trend
Recovery gap
Rest deficit
Night-duty concentration
Leave gap
Staffing pressure
Support requested
Operational driver
Data quality issue
Baseline unavailable
Scenario infeasible
Human approval
Outcome tracking
```

### Avoid

``` text
Mental-health score
Mentally unstable
Unfit
Psychologically weak
Diagnosis
Automatic career decision
```

## 22. WSI Display

WSI is the Workload Strain Index, a decision-support measure of
workload/recovery strain, not a clinical diagnosis.

``` text
WSI = 0.25D + 0.20R + 0.15C + 0.15N + 0.10L + 0.10H + 0.05S
```

Each component is normalized 0--100.

Reference example:

``` text
D=78, R=85, C=90, N=80, L=70, H=65, S=40
WSI = 77.50
```

Do not use 76.25.

## 23. Baseline / EWMA

``` text
z = (x - Median(X)) / (1.4826 * MAD(X))

S_t = λX_t + (1-λ)S_(t-1)
```

These are historical context indicators, not clinical measurements.

If history is insufficient, show `Baseline unavailable`.

## 24. Prediction UI

MVP: Logistic Regression.

Target:

``` text
Y = 1 if a defined leave-pattern anomaly occurs within the next 30 days;
otherwise Y = 0.
```

Prediction must be labelled as a prototype/model output and must not
trigger career, disciplinary or automatic roster decisions.

## 25. Explanation UI

Every strain result should answer:

``` text
What is elevated?
Why is it elevated?
What changed?
What operational factor contributes most?
What can be changed?
```

Example:

``` text
WSI 77.50

Weighted contributions (WSI points)
Duty load          +19.50
Rest deficit       +17.00
Consecutive duty   +13.50
Night duty         +12.00
Leave gap           +7.00
Deployment          +6.50
Staffing            +2.00

Context:
Baseline comparison appears only when valid history is available.
```

## 26. Component Architecture

``` text
components/
├── ui/
├── layout/
│   ├── AppShell
│   ├── Sidebar
│   ├── TopBar
│   └── MobileNav
├── dashboard/
│   ├── KpiCard
│   ├── WsiTrend
│   ├── WsiDistribution
│   ├── RestHeatmap
│   ├── NightDutyPressure
│   └── OperationalDrivers
├── commander/
│   ├── PriorityTable
│   ├── StrainCard
│   ├── WhatIfSimulator
│   ├── ScenarioCompare
│   ├── DecisionPanel
│   └── OutcomePanel
├── welfare/
├── personnel/
└── shared/
    ├── EmptyState
    ├── ErrorState
    ├── LoadingState
    ├── DataFreshness
    └── PermissionDenied
```

Do not create one giant dashboard component.

## 27. CSS Architecture

Use:

``` text
Tailwind CSS
+
shadcn/ui
+
central design tokens
```

Global rules belong in:

``` text
frontend/app/globals.css
```

Prefer Tailwind utilities and shared components over page-specific CSS.

Do not create a separate stylesheet for every screen unless a genuine
specialized case requires it.

Do not scatter arbitrary hex values through JSX.

Do not use `!important` except for documented integration issues.

## 28. Final Interaction Rules

``` text
Protected screen
→ authentication
→ role check
→ purpose check
→ server-side unit/person/case authorization and scoped repository query
```

``` text
Priority row
→ detail
→ explanation
→ action
```

``` text
WSI
→ definition
→ value
→ normalization
→ contribution
```

``` text
Trend point
→ date
→ duty/rest/leave context
```

``` text
What-if
→ select change
→ validate coverage/skills/rest
→ calculate
→ compare
```

``` text
Approve
→ confirm
→ actor/time/reason
→ approval recorded
→ separately confirmed external implementation
→ observed window
→ outcome review
```

``` text
Private self-check
→ score privately
→ wellbeing_private
→ raw answers never copied to command tables
```

## 29. Final Acceptance Checklist

-   [ ] Locked role screens exist.
-   [ ] Commander dashboard follows Unit Health → Drivers → What-if →
    Approval.
-   [ ] Strain Card exposes operational drivers and baseline.
-   [ ] What-if uses Current vs Proposed.
-   [ ] Human approval is explicit.
-   [ ] Outcome tracking exists.
-   [ ] Personnel private flow is visually separated.
-   [ ] Raw private wellbeing data is not rendered in command views.
-   [ ] Commander/Welfare risk views use pseudonymous identifiers.
-   [ ] Warm cream and defence olive design system is consistent.
-   [ ] Semantic colors retain fixed meaning.
-   [ ] No arbitrary page-specific color system.
-   [ ] Responsive desktop/tablet/mobile behavior works.
-   [ ] PWA uses the same Next.js frontend.
-   [ ] Loading, empty, error and permission states exist.
-   [ ] Accessibility/focus states exist.
-   [ ] Charts follow the defined rules.
-   [ ] No clinical language appears in operational screens.
-   [ ] No automatic roster action is presented.
-   [ ] CSS is centralized and maintainable.
-   [ ] Components are reusable.
-   [ ] Commander, Welfare, Personnel and Admin feel like one product.
-   [ ] No Auditor login/dashboard exists.

## 30. Coding-Agent Rule

This document is a visual and interaction contract.

If an implementation detail is not explicitly defined here, prefer:

``` text
existing design token
→ existing shadcn component
→ existing shared component
→ existing layout pattern
```

Do not redesign the PRAHARI UI while implementing functionality.

Do not replace the locked screen structure.

Do not remove screens to simplify implementation.

Do not introduce a second frontend framework.

Do not create a separate mobile application for v1.

The target is:

``` text
ONE PRAHARI DESIGN SYSTEM
        ↓
ONE NEXT.JS FRONTEND
        ↓
RESPONSIVE DESKTOP + TABLET + PWA
        ↓
FOUR ROLE EXPERIENCES
        ↓
CONSISTENT COMPONENTS + CSS TOKENS
```


## 31. Route and interaction contract

All role login IDs share `/login`, with server-session-based routing. Backend paths
below use `/api/v1`; API details are owned by [architecture.md](architecture.md).

| Screens | Frontend route | Backend capability |
|---|---|---|
| C02 | `/commander` | `/commander/overview`, scoped `/alerts` |
| C03 | `/commander/personnel` | pseudonymous attention/availability filters |
| C04 | `/commander/personnel/[pseudo_id]` | operational detail |
| C05–C06 | `/commander/scenarios/new` | create `/scenarios`, manual/optimize mode |
| C07–C08 | `/commander/scenarios/[id]` | compare, revise, decisions, implementation |
| C09 | `/commander/scenarios/[id]/outcomes` | outcomes/review |
| W02–W03 | `/welfare`, `/welfare/personnel` | overview/pseudonymous operational lists |
| W04 | `/welfare/cases/[id]` | named case detail/actions/consent-scoped results |
| W05 | `/welfare/cases` | cases, assignment/follow-up |
| W06–W08 | `/welfare/scenarios/new`, `/welfare/scenarios/[id]` | draft/compare/recommend only |
| W09 | `/welfare/cases/[id]/outcome` | case closure and linked permitted operational outcome |
| P02 | `/personnel/privacy` | consent, sharing, withdrawal |
| P03 | `/personnel` | own operational/history |
| P04 | `/personnel/self-check` | instrument choice/assessment |
| P05 | `/personnel/assessments/[id]` | private answer/result detail |
| P06 | `/personnel/trends` | results, per-instrument convergence |
| P07 | `/personnel/support` | own support/status/withdrawal |
| P08 | `/personnel/access-history` | own permitted access history; deletion request deferred |
| A02–A09 | `/admin`, `/admin/units`, `/admin/personnel`, `/admin/data`, `/admin/policies`, `/admin/users`, `/admin/models`, `/admin/audit` | corresponding Admin resources/jobs |

Deletion request controls are DEFERRED / REQUIRES SEPARATE PRIVACY + DATABASE APPROVAL;
P08 does not require an active deletion endpoint or a deletion/tombstone table for MVP.

Personnel bottom tabs: My Recovery, Self-check, Support, Privacy; results/trends/
access history are child screens. Other roles use sidebar/drawer. Touch targets
at least 44px. Normal text contrast >=4.5:1; large text/essential UI boundaries
>=3:1. Verify actual states; disabled colors never style essential active text.

Every analytic card shows synthetic label, source date and coverage. No chart
bridges missing observations with invented values; provide a textual data table.
Distinguish probability percentages, WSI points and private instrument-specific percentage/display value where that instrument defines one.

Self-check shows instrument/version, recall period and collection notice first.
Sharing is a separate explicit action listing selected assessments, case, recipient
and time expiry only where used by approved versioned policy; never invent a mandatory duration. No prechecked consent. Withdrawal/reassignment clears shared panels
and refetches permissions. An unavailable instrument shows the missing prerequisite
and keeps Support usable; no substitute quiz or fabricated result.

Mutations disable duplicate submission and reuse the idempotency key on retries.
A 409 stale revision requires reload/re-evaluation. Session expiry clears sensitive
content before login redirect. No offline assessment/approval queue or sensitive
browser persistence. Render permissions before content, not after a private flash.

Scenario comparisons label the rest proxy “projected off-duty opportunity”, not
measured sleep. Show recipient/whole-unit effects, changed assignments, constraints
and assumptions. “No feasible solution found” does not prove impossibility. Missing
planning input is INPUT_UNAVAILABLE. Outcome charts show observation dates and
completeness; no causal claim or cost-of-inaction forecast in MVP.
