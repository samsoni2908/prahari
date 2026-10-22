# PRAHARI — ML, Analytics & Evidence Fusion Specification

**Project:** SIH 26186 — PRAHARI
**Version:** 4.0
**Status:** FINAL — AUTHORITATIVE ML / ANALYTICS CONTRACT
**Scope:** SIH prototype / controlled demo using synthetic data
**Core Principle:** DETECT → EXPLAIN → BALANCE → VERIFY

---

# 1. Purpose

PRAHARI uses operational analytics, explainable machine learning, private wellbeing analysis, and human-reviewed evidence fusion to identify patterns that may deserve welfare or workload attention.

The ML/analytics system is intentionally designed around **multiple independent signals** rather than one opaque “stress score”.

The system must answer questions such as:

- Is current operational workload/recovery strain elevated?
- Is the current pattern unusual compared with the person's own history?
- Is the pattern unusual compared with relevant peers?
- Is there an elevated probability of the defined observable leave-pattern anomaly within the next 30 days?
- Has the person's voluntary private wellbeing trend changed?
- Do operational and private wellbeing signals point in the same direction?
- Is there enough valid evidence to make any of these calculations?

The system must **not** answer:

- “Does this person have depression?”
- “Does this person have PTSD?”
- “Is this person mentally weak or unfit?”
- “Will this person self-harm?”
- “What is this person's mental-health percentage?”
- “Should this person be punished, transferred, denied leave, or removed from duty?”

PRAHARI is an operational welfare decision-support system, not a clinical diagnostic system.

## Stage-1 locked model state

Model A is `MODEL_A_FINAL_LOCKED`: regularized calibrated logistic regression, Feature Set B with exactly 15 operational features, classifier threshold 0.15, risk bands LOW 0–39 / MEDIUM 40–69 / HIGH 70–100, and approved artifact SHA-256 `2e540b4ca0c3db9cf32b7601ac23319ead74db5c18ac5fd7c466b2ef4ae290b9`. Runtime uses that persisted artifact and never trains. Missing, corrupt or incompatible artifact is `MODEL_UNAVAILABLE`.

### Unresolved Model-A target provenance limitation

The governed artifact and runtime contract identify the target as `v2.1-approved-leave-lifecycle`, while both frozen Model-A CSVs identify their rows as `model-a-target-v3.0-canonical`. The governed manifest binds the 2,100-row frozen validation CSV by SHA-256 `359904e8c4e544640cce7b7406f1ac4155206785e91a3494bdc2d75969853530`. Read-only verification reproduced that cohort's 237 positive and 1,863 negative labels and the recorded ROC-AUC, PR-AUC, Brier, precision, recall and F1 values. Those results establish reproducibility of evaluation against that frozen v3.0-labelled cohort; they do **not** establish which target implementation produced the artifact's training labels or prove that v2.1 and v3.0 are semantically equivalent.

No authoritative v2.1 target-function snapshot or approval record is present in repository history. The current generator also produces six more positive development labels than the frozen canonical development CSV, which is further provenance drift rather than evidence of equivalence. This mismatch remains explicitly `UNRESOLVED` pending authoritative evidence and is a release/reproducibility risk. Do not relabel either dataset, rewrite the governed manifest, retrain or replace the artifact, disable an otherwise valid artifact solely for this mismatch, or weaken runtime governance checks. The existing artifact hash, calibration, thresholds, inference behavior and unavailable-state gates remain authoritative for runtime use. Engine B and Model C are unaffected. Any future provenance correction or model lifecycle action requires separate explicit approval.

Engine B is `ENGINE_B_FRAMEWORK_FINAL_LOCKED` but currently `INSTRUMENT_NOT_ACTIVATED`, `NOT_TRAINED` and `NOT_SHARED`; existing historical wellbeing records are `LEGACY_UNGOVERNED`. No questionnaire or private sharing is activated by this contract.

Model C is `MODEL_C_FRAMEWORK_FINAL_LOCKED` at `v1.1-truthful-source`. It has no weighted combined score/probability and no private convergence for Commander. B unavailable/unshared plus A available produces `OPERATIONAL_EVIDENCE_ONLY`. `NO_ELEVATED_EVIDENCE` is valid only when both governed sources are available/shared and independently non-elevated.

---

# 2. Final Intelligence Architecture

PRAHARI uses three clearly separated intelligence layers:

```text
                         PRAHARI INTELLIGENCE

        ┌─────────────────────────────────────────────┐
        │ MODEL A — OPERATIONAL / HR INTELLIGENCE    │
        │ Duty, Rest, Leave, Deployment, Staffing... │
        └─────────────────────┬───────────────────────┘
                              │
                              ▼
                    Operational Signal
                              │
                              │
                              ├─────────────────────┐
                              │                     │
                              │                     ▼
                              │          ┌─────────────────────┐
                              │          │ MODEL C / FUSION    │
                              │          │ Evidence Convergence│
                              │          └──────────┬──────────┘
                              │                     │
                              │                     ▼
                              │          Welfare Attention Signal
                              │
                              │
        ┌─────────────────────┴───────────────────────┐
        │ ENGINE B — PRIVATE WELLBEING INTELLIGENCE  │
        │ Voluntary self-check + private trend       │
        └─────────────────────────────────────────────┘
```

The three layers have different purposes:

| Layer | Main purpose | Primary audience |
|---|---|---|
| Model A | Operational/HR strain and future observable event prediction | Commander, Welfare Officer, Personnel as permitted |
| Engine B | Private wellbeing result and personal trend | Personnel; permitted Welfare workflow only |
| Model C / Convergence | Determine whether independent operational + wellbeing evidence strengthens welfare attention | Welfare workflow; Personnel where appropriate |

**Commander does not receive Model B raw/private outputs and does not receive privacy-leaking Model C details.**

---

# 3. Final Product Logic

The final intelligence flow is:

```text
Operational HR Data
        ↓
Feature Engineering
        ↓
WSI + Baseline + EWMA + Peer Anomaly
        ↓
Model A: 30-Day Operational Prediction
        ↓
Operational Explanation
        │
        │
        ├──────────────────────────────────────────────┐
        │                                              │
        │                                              ▼
        │                                  Evidence Convergence
        │                                              ▲
        │                                              │
        │                                              │
Voluntary Private Wellbeing                            │
        ↓                                              │
Consent                                                │
        ↓                                              │
Self-check                                             │
        ↓                                              │
Engine B: Result + Trend ──────────────────────────────┘
        ↓
Optional Support Request
```

Model C does not replace Model A or Engine B.

It asks:

> Are independent operational and private wellbeing signals converging strongly enough to justify greater welfare attention?

---

# 4. Terminology

Use:

- operational workload/recovery strain;
- operational attention;
- wellbeing trend;
- evidence convergence;
- recovery deficit;
- night-duty concentration;
- workload change;
- staffing pressure;
- welfare review suggested;
- support requested;
- insufficient history;
- model unavailable.

Avoid:

- stress percentage;
- depression probability;
- mental-health score;
- psychologically weak;
- unfit;
- suicide risk;
- clinical severity score.

The SIH problem statement may use “stress monitoring”, but PRAHARI's implementation output remains operational and non-diagnostic.

---

# 5. Model A — Operational / HR Intelligence

Model A is the main production ML path.

It uses only governed operational/service information.

## 5.1 Data sources

Typical inputs:

```text
duties
rest_records
leave_records
deployments
training
staffing
posting_history
skills / person_skills where relevant
historical WSI
historical baseline
historical anomaly outputs
```

Model A must not use:

```text
raw wellbeing answers
wellbeing question text
future leave information
future WSI
future outcomes
hidden synthetic variables
target columns
uncontrolled free text
```

---

# 6. Model A Feature Windows

Every feature is calculated at a prediction cutoff `t`.

Allowed windows may include:

```text
7 days
14 days
30 days
90 days
180 days where explicitly required
```

Representative operational features:

```text
duty_hours_7d
duty_hours_14d
duty_hours_30d

duty_count_7d
duty_count_30d

night_shift_count_14d
night_shift_ratio_30d

consecutive_duty_max_14d

mean_rest_hours_7d
min_rest_gap_7d
mean_rest_gap_14d
rest_deficit_days_30d

days_since_leave
leave_days_90d
leave_frequency_180d

deployment_days_30d
deployment_days_90d
deployment_intensity_30d

training_hours_30d

unit_staffing_pressure

wsi_current
wsi_7d_mean
wsi_30d_mean
wsi_7d_slope

baseline_z
ewma
peer_anomaly
```

The actual runtime feature set must be an **explicit allowlist**.

Never select “all numeric columns”.

---

## 6.1 Model A ordered feature contract — approved scope, source-gated activation

**Decision reconciliation revision 2 — 2026-10-04.** The user approved only the following 15 names in this order, subject to read-only verification. No substitution or additional Model A feature is authorised. Section 6's earlier representative concepts are not an active supervised feature allowlist.

Common rules: UTC cutoff t; trailing windows [t-k days,t); completed actual intervals only; validated timestamps/hours and clipped window contributions; fully contained UTC days for date-only data with boundary exclusions disclosed. Use only source versions known by t. Explicit coverage is required to distinguish zero activity from missing reporting. Conflicting duplicates, overlaps, non-finite/invalid values and missing history remain unavailable. created_at is not proof of historical availability. Features are calculated from source history, not trusted precomputed CSV columns; any persisted snapshot binds source/feature/policy versions. Increasing workload/count/ratio means more of the named exposure, increasing rest means more recovery opportunity; these are meanings, not assumed model coefficients. No target/future/private/hidden-process/identifier fields enter this vector.

**Live-integration status:** the repository, source-gated adapter and orchestration path are implemented and have passed isolated PostgreSQL 16 end-to-end verification using certified synthetic fixtures. Retained historical sources without an approved cutoff-bound coverage/known-at manifest remain unavailable; no eligibility is inferred from existing rows or CSV flags. This does not change the locked builder, vector or artifact. `available_at_prediction_date=True` in feature_dictionary.csv is not independent provenance evidence. The retained analytics and integration tests are the executable evidence.

| Approved order / feature | Source, calculation contract and units | Current result / specific requirements beyond common provenance and shared-pipeline gaps |
|---|---|---|
| 1. duty_hours_7d | duties.start_at/end_at/hours; sum valid completed duty hours clipped to prior 7 days; hours | DEFERRED / REQUIRES SOURCE FIELD: source receipt/revision/coverage history and tested common builder; raw columns exist |
| 2. duty_hours_30d | Same calculation over prior 30 days; hours | DEFERRED / REQUIRES SOURCE FIELD: same gaps as feature 1 |
| 3. night_duty_count_14d | duties.is_night plus actual intervals; count distinct completed night duties with end in (t-14 days,t]; count | DEFERRED / REQUIRES SOURCE FIELD: authoritative night classification, complete duty coverage and cutoff-safe builder |
| 4. night_duty_ratio_30d | Completed night-duty count / all completed-duty count with end in (t-30 days,t]; fraction 0–1 | DEFERRED / REQUIRES SOURCE FIELD: same provenance; no-duty denominator yields null/unavailable, not fabricated 0 |
| 5. consecutive_duty_days | duties actual date overlaps; consecutive on-duty UTC dates ending on the last completed date before t; days | DEFERRED / REQUIRES SOURCE FIELD: coverage through a verified preceding off-duty date to bound the streak; incomplete prehistory cannot truncate it silently |
| 6. min_rest_hours_14d | Minimum valid daily rest_hours in prior 14 days; hours 0–24 | DEFERRED / REQUIRES SOURCE FIELD: valid complete daily reporting/quality and historical knowledge; negative/missing source rest must be resolved, not clamped |
| 7. avg_rest_hours_30d | Arithmetic mean of valid daily rest_hours in prior 30 days; hours 0–24 | DEFERRED / REQUIRES SOURCE FIELD: same as feature 6; missing days cannot become zero or a silently smaller denominator |
| 8. quick_return_count_30d | Count eligible daily rest_gap_hours below features.quick_return_threshold_hours in prior 30 days; count | DEFERRED / REQUIRES SOURCE FIELD: validated nonnegative gap records and complete coverage; threshold is required versioned configuration, never legacy 11 hours by default |
| 9. deployment_days_30d | Union count of confirmed deployed UTC dates overlapping prior 30 days; days | DEFERRED / REQUIRES SOURCE FIELD: actual/effective ongoing or completed deployment status and cutoff-visible revisions/coverage; planned end must not become future actual truth |
| 10. training_days_30d | Union count of actual attended UTC training dates overlapping prior 30 days; days | DEFERRED / REQUIRES SOURCE FIELD: historical actual attendance/completion-day evidence; aggregate dates/hours and final COMPLETED status do not prove availability at an earlier t |
| 11. staffing_ratio_7d | Most recent staffing record in prior 7 days known by t for effective unit: available_strength/required_strength; fraction, may exceed 1 | DEFERRED / REQUIRES SOURCE FIELD: historical effective unit context and staffing knowledge/coverage; required=0 yields unavailable, not a fixed ratio |
| 12. workload_change_14v14 | 100 × (duty hours [t-14d,t) - duty hours [t-28d,t-14d)) / duty hours [t-28d,t-14d); percent | DEFERRED / REQUIRES SOURCE FIELD: both completed/known/covered duty windows; zero prior total yields unavailable, not an invented finite change |
| 13. ewma_workload | EWMA of daily actual duty hours through the last completed day, using approved lambda=0.30 and §8.1 segment/gap rules; hours | DEFERRED / REQUIRES SOURCE FIELD: coverage-certified daily workload series and shared implementation; legacy 0.20 is incompatible; this is duty-hour EWMA, not WSI EWMA |
| 14. baseline_z_workload | Robust z of current completed daily duty hours against prior daily duty-hour median/MAD; dimensionless; lookback/minimum from policy | DEFERRED / REQUIRES SOURCE FIELD: valid prior daily series and shared versioned calculation; §8.1 zero-MAD rules apply; unequal zero-MAD z remains unavailable, not 3; legacy 56-day constant not inherited |
| 15. peer_deviation_workload | Signed robust z of duty_hours_30d against effective unit + operational-role eligible peer median/MAD, including subject; dimensionless | DEFERRED / REQUIRES SOURCE FIELD: historical role/unit/service membership and valid peers' source windows; minimum from policy, no unit-only widening or legacy >=8 default; zero-MAD follows §8.1; not a renamed Isolation Forest score |

The exact 15 names and order are locked as Feature Set B. Live eligibility remains gated by provenance/coverage validation, including the known invalid/missing rest-source evidence; do not repair invalid values with abs/clamping or rely on export flags.

The approved runtime vector is exactly all 15 rows in their original relative order, identified as `v2.1-SetB-15ops`. Live inference is permitted only when `SOURCE_COVERAGE_POLICY_V1_SYNTHETIC_DEMO` proves every mandatory builder input/window at the explicit cutoff with zero unknown gaps. A failed eligibility check produces an unavailable state; it does not shrink, substitute, impute or reinterpret the locked vector.

Leave-gap/frequency/variability features remain deferred until trustworthy actual leave-history provenance exists; they are outside this approved MVP vector. The earlier representative WSI/peer/rest features do not silently join it.

Stage-3 runtime integration reuses `backend/app/ml/features_hr.py::compute_operational_features_at_cutoff`; no second feature implementation is permitted. `backend/app/analytics/operational_feature_adapter.py` owns repository retrieval and coverage/cutoff/known-at/finite-input validation, then calls that builder. `backend/app/services/operational_attention_service.py` owns coverage → inference → persistence → attention → audit. Isolated verification passed; retained processing still requires valid explicit source certification.

Persist VALID governed predictions in the existing model_outputs only when the discriminator includes target_name `next_30d_leave_anomaly`, the approved Model-A identifier, model_version `1.0.0`, feature_set_version `v2.1-SetB-15ops`, training data version `v2.1-frozen-prototype`, target contract `v2.1-approved-leave-lifecycle` and the approved artifact hash. hr_probability is Model-A only; wellbeing_probability and combined_probability remain NULL. The existing 320 legacy rows stay unchanged and non-authoritative. Unavailable inference creates no fake valid row.

Runtime loads the approved persisted preprocessing, estimator and calibration from the locked artifact. Required source gaps remain unavailable even if the frozen pipeline contains an imputer. Extra/missing/reordered features produce MODEL_UNAVAILABLE with reasons. No startup/runtime fitting, substitute artifact or legacy fallback probability is authorized. Future retraining or feature semantic changes require a new explicitly approved model contract and do not alter this lock.

---

# 7. Time / As-Of Rule

Every analytics calculation must have an explicit `as_of` time.

```text
PAST / PRESENT DATA <= t
            ↓
      FEATURE BUILD
            ↓
       MODEL AT t
            ↓
 FUTURE TARGET WINDOW
      (t, t + 30d]
```

No feature may contain information from after the prediction cutoff.

Every persisted prediction should preserve:

```text
as_of
calculated_at
feature_version
model_version
target_version
policy_version
source_window / source reference
```

---

# 8. WSI — Workload / Recovery Strain Index

WSI remains deterministic and explainable.

```text
WSI =
0.25D +
0.20R +
0.15C +
0.15N +
0.10L +
0.10H +
0.05S
```

Where:

```text
D = Duty Load
R = Rest / Recovery Deficit
C = Consecutive Duty
N = Night-Duty Concentration
L = Leave Gap / Disruption
H = Deployment / Hardship Intensity
S = Staffing Pressure
```

All components are normalized to `0–100`.

Reference:

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

WSI is:

```text
operational
deterministic
versioned
explainable
```

WSI is not:

```text
a psychiatric score
a wellbeing questionnaire score
a supervised-model probability
```

Invalid or non-finite input must never be silently converted into a valid score.

---

## 8.1 MVP Analytics Calculation Contract

**Reconciliation revision 2 — 2026-10-04.** Calculation definitions were reconciled in the earlier pass; the user now confirms versioned/configurable operational policies with explicit keys and no silent fallback. Unset values are capability activation gates, not documentation blockers. Existing code constants do not supply approved policy values.

### Inputs, windows and seven-factor normalization

Daily cutoff `t` is UTC midnight. Under `SOURCE_COVERAGE_POLICY_V1_SYNTHETIC_DEMO`, use completed known-at-cutoff source versions and immutable manifest-certified complete required windows with zero unknown gaps. Manifests are versioned, operational-only, contain no private wellbeing data and bind deterministic database-derived source hashes. Empty source does not mean zero activity. Historical synthetic execution uses an explicitly approved manifest cutoff rather than blindly using machine wall-clock today. All raw values must be finite and physically valid before normalization. For a nonnegative raw measure `m` and approved positive reference `r`, normalization is `100 × min(1,max(0,m/r))`; clipping reflects saturation of a valid raw measure, never repair of invalid input. Reject already-normalized components outside 0–100.

| Component | Raw measure and window | Normalization / required policy |
|---|---|---|
| D — duty load | Completed actual duty hours in prior 7 days | Reference duty hours >0 |
| R — recovery deficit | Mean daily max(0,rest_reference_hours-rest_hours) in prior 7 days | Divide by rest_reference_hours, approved in (0,24]; valid rest_hours 0–24; DERIVED_FROM_DUTY remains an off-duty proxy |
| C — consecutive duty | Longest actual consecutive-duty date run within prior 14 days | Reference consecutive days >0 |
| N — night concentration | Night completed duty count / all completed duty count in prior 30 days | Multiply fraction by 100; explicit complete no-duty coverage permits 0, not missing classification |
| L — leave gap | Elapsed days since last verified actual leave completion before t | Reference leave-gap days >0; approved/requested leave or joining date cannot substitute for actual completion |
| H — deployment intensity | Day-weighted deployed intensity in prior 30 days; confirmed nondeployment days=0; deployed intensity 1–5 | Reference exposure >0 within source scale; no invented posting hardship value or missing intensity |
| S — staffing pressure | Mean daily max(0,1-available/required) over positive-demand days in prior 7 days | Multiply fraction by 100; available >=0, required >0; disclose excluded zero-demand days; no eligible days is unavailable |

Compute the locked weighted sum using unrounded components; contribution=weight×component. Round presentation only, to two decimal places. The reference remains 77.50. No redistribution of weights when a component is missing.

Each component carries `input_state=VALID|COMPONENT_INPUT_UNAVAILABLE`, raw measure, unit/window, coverage, normalization policy and reason codes. This component detail does not add a dashboard-level availability state. Any unavailable component makes WSI value/contributions unavailable. Use REST_DATA_MISSING for missing required rest, INSUFFICIENT_HISTORY for insufficient observed history, NOT_COMPUTED for absent required source/policy, and COMPUTATION_ERROR for invalid input/calculation; preserve all component reasons. If several causes coexist, status precedence is COMPUTATION_ERROR, REST_DATA_MISSING, INSUFFICIENT_HISTORY, then NOT_COMPUTED. Complete verified zero activity differs from absent data.

Current-source capability: duties.start_at/end_at/hours/is_night support D/C/N only after overlap/coverage/knowledge validation; rest_records.rest_hours/source/data_quality_status support R only after invalid/missing/DELAYED records are resolved and complete daily coverage exists. L currently returns COMPONENT_INPUT_UNAVAILABLE: actual leave completion history/timestamps are absent. deployments.start_date/end_date/intensity_level support H only with confirmed interval/ongoing/nondeployment coverage. staffing.available_strength/required_strength support S only with effective unit history and complete daily reporting. All components currently lack certifiable historical source revisions/known_at/coverage and required approved normalization policy; no seven-factor runtime readiness is inferred from CSV headers.

### Baseline, EWMA and peer context

Baseline uses prior valid daily WSI under compatible calculation/policy versions, excluding current cutoff. Approved lookback and minimum valid-history count are required. Order/deduplicate by cutoff and compatible source revision; conflicting duplicates are errors, not averaging. Use median and MAD of unrounded values and the §9 scale 1.4826. When MAD=0 and current=median, z=0, direction=EQUAL, zero_mad=true. When MAD=0 and current differs, z=null, direction=ABOVE/BELOW, zero_mad=true, reason ZERO_MAD_NONZERO_DEVIATION; median/MAD remain valid, but no finite standardized deviation is claimed. Never substitute an epsilon, infinity or fabricated z=3. Attention must explicitly handle the direction-only case rather than apply numeric z thresholds to null. Missing current WSI or insufficient history prevents a valid deviation.

EWMA uses §10 lambda=0.30, unless a separately approved version changes it. Initialize each consecutive valid daily segment at its first WSI. A missing/invalid day or incompatible policy breaks the segment; resume with a new initialization, never silently compress time or carry an old value as current. Current invalid WSI makes current EWMA unavailable. Trend needs a configured minimum segment length (at least two points) and approved nonnegative stability tolerance: delta=current EWMA minus preceding daily EWMA; RISING if above tolerance, FALLING if below negative tolerance, otherwise STABLE. A lone point has no trend; historical last-valid values may be displayed only with their actual date/unavailable-current label.

Baseline with insufficient valid prior points is INSUFFICIENT_HISTORY; absent baseline policy/current valid input is BASELINE_UNAVAILABLE with cause. Trend value is null with INSUFFICIENT_HISTORY when a valid segment is too short, NOT_COMPUTED when required trend policy is absent, or the current upstream error/availability cause when current EWMA cannot be calculated. Order segments chronologically; missing history is not a valid zero point.

Peer cohort is effective unit + governed operational/service `role_title` at cutoff, with confirmed eligible service status and complete, valid peer inputs. **role_title is not PERSONNEL/COMMANDER/WELFARE_OFFICER/ADMIN RBAC.** Missing historical unit/role/status context cannot be repaired with a current assignment. The approved minimum eligible cohort size is configurable (at least two); insufficient valid unit+operational-role membership returns PEER_COHORT_INSUFFICIENT. Never widen to unit-only, other units or RBAC peers.

The separate Isolation Forest peer vector uses prior 30-day duty hours, prior 30-day night-duty fraction, mean valid daily rest_hours over 7 days, union of confirmed deployment dates over 30 days, and mean max(0,1-available/required) on positive-demand days over 7 days. Require complete coverage and effective context; zero duties with confirmed complete coverage permits a peer night fraction of zero, while no positive-demand staffing days is unavailable. This is the peer anomaly input contract, not additional supervised Model A features or a substitute for peer_deviation_workload. Fit Isolation Forest once for the eligible cohort, including the queried member, using stable pseudonymous ordering and a recorded source hash. Persist preprocessing, seed, library/estimator parameters and configured contamination; no private data, peer-score recursion or arbitrary zero imputation. Define anomaly strength as negative score_samples (larger means more unusual); apply only the versioned calibrated peer rule, not a prevalence claim or automatic HIGH. Missing required policy/model or computation errors remain explicit.

### Operational attention and alert policy

Attention is a versioned rule evaluation, not a numeric fusion. `OPERATIONAL_ATTENTION_POLICY_V1_SYNTHETIC_DEMO` retains LOW/MEDIUM/HIGH from locked operational risk. WSI is required; the policy declares other required/optional signals, valid-input predicates, zero-MAD direction handling, freshness and provenance. HIGH has precedence over MEDIUM; LOW is allowed only when all required signals are valid and no predicate matches. A missing required signal makes attention unavailable; optional missing inputs stay disclosed and cannot be interpreted as normal. Do not convert missing model probability to LOW or use private participation/Engine B/Model C as operational predicates.

MEDIUM remains visible in operational attention views and does not automatically emit an alert/notification. HIGH becomes emission-eligible only after two consecutive valid daily cutoffs. Invalid/unavailable cutoffs break the qualifying streak, are never LOW and never auto-resolve an alert. An unresolved OPEN/ACKNOWLEDGED alert suppresses duplicate family emission. After resolution, a seven-day cooldown from the last emission applies to the same person/trigger family across policy versions. Dedupe uses the existing global alert key with a deterministic qualifying-cutoff occurrence token so a later post-cooldown event remains possible. Acknowledge/resolve are authorized human actions with audited reason codes. These sustain/cooldown values are controlled synthetic-demo policy, not real-force doctrine. The locked Model-A 0.15 threshold remains a classifier threshold, not an alert rule.

### Versioned operational policy configuration interface

The following are configuration contracts for later implementation. Stage-1 policy rows below carry their locked synthetic-demo values; other rows remain separately governed configuration. Each active policy is an immutable typed snapshot with version, effective_from/until, provenance and content hash. Resolve the snapshot effective at as_of (and bind the observation policy at implementation); never read today's policy to reinterpret history. Validate required keys before enabling the dependent capability; absent, invalid or mismatched configuration yields the explicit unavailable state/reason, never a silent fallback.

| Exact key(s) | Type / validation | Contract |
|---|---|---|
| baseline.lookback_days; baseline.min_valid_observations | Positive integers; minimum cannot exceed eligible daily lookback | Prior-only median/MAD for the named metric; no legacy 5/8/56-day defaults |
| trend.min_valid_observations; trend.stability_tolerance | Integer >=2; finite nonnegative tolerance in named metric units | Consecutive valid segment and signed delta classification |
| ewma.lambda | Finite in (0,1] | Explicit approved prototype default 0.30, persisted in the resolved snapshot; no legacy 0.20 |
| peer.min_valid_members | Integer >=2 | Effective unit + operational/service-role cohort only |
| peer.iforest.n_estimators; peer.iforest.max_samples; peer.iforest.max_features; peer.iforest.contamination; peer.iforest.random_state; peer.iforest.n_jobs; peer.iforest.library_version; peer.preprocessing_version | Positive tree/worker counts; max_samples positive integer <= eligible cohort size or fraction in (0,1]; max_features positive integer <= vector width or fraction in (0,1]; contamination in (0,0.5]; integer seed; registered library/preprocessing versions | All execution settings bound to peer model/cohort evidence; no library defaults silently selected |
| wsi.d.reference_hours; wsi.c.reference_days; wsi.l.reference_days | Finite positive values in specified units | Saturation references for D/C/L |
| wsi.r.reference_hours; wsi.h.reference_intensity | Finite respectively in (0,24] and (0,5] | Recovery/deployment references; N/S fraction-to-percent remains defined by formula |
| analytics.coverage_policy; analytics.freshness_policy | `SOURCE_COVERAGE_POLICY_V1_SYNTHETIC_DEMO`: immutable per-cutoff manifests, deterministic source hashes and zero unknown gaps for every mandatory source/window; no arbitrary source-age tolerance in V1 | Required source families where applicable: duties, rest, leave, deployments, training, staffing, effective unit/person membership, skills/person_skills, planning demand, boundary context and peer context; no inferred COMPLETE |
| attention.required_signals; attention.optional_signals; attention.predicates | Disjoint declared signal lists; WSI required; typed HIGH/MEDIUM conditions with units, threshold provenance and zero-MAD handling | Missing required input prevents a valid label; private signals prohibited |
| alerts.rules | `OPERATIONAL_ATTENTION_POLICY_V1_SYNTHETIC_DEMO`: HIGH-only automatic emission; 2 consecutive valid daily cutoffs; 7-day cooldown after resolution; MEDIUM view-only | §8.1 sustained/dedupe/human resolution; synthetic-demo values only |
| features.quick_return_threshold_hours | Finite positive hours | Required only when quick_return_count_30d is enabled; no automatic 11-hour threshold |
| balance.constraints; balance.objective_priorities; balance.execution_budget; balance.projection_policy | `BALANCE_SYNTHETIC_DEMO_POLICY_V1`: 14-day horizon; 8-hour minimum rest; max 60 hours/7 days; max 6 consecutive days; all structural constraints. `BALANCE_SOFT_OBJECTIVE_POLICY_V1`: recovery, then workload/night distribution, then movement | Architecture §10; hard constraints dominate; synthetic-demo values; no opaque weights or promised improvement |
| verify.observation_duration_seconds; verify.coverage_policy | `VERIFY_POLICY_V1_SYNTHETIC_DEMO`: W=14 days and zero-unknown-gap mandatory after-window coverage | Architecture §11 matched [u-14d,u) / [u,u+14d); availability separate from workflow |

The baseline metric binding distinguishes duty-hours feature baseline from WSI baseline; trend tolerances likewise retain metric units. Isolation Forest policy applies to the separate peer anomaly calculation, not the signed robust peer-deviation feature. Policy activation follows existing audited governance; specifying keys neither authorises a schema change nor supplies operational values. Feature/policy/source/calculation versions bind outputs and artifacts, and compatibility changes require recomputation/evaluation.

---

# 9. Personal Baseline

The personal baseline answers:

> Is this person's current operational pattern unusual compared with their own history?

Default robust deviation:

```text
z = (x - Median(X)) / (1.4826 × MAD(X))
```

Rules:

- use only history before the as-of date;
- define a minimum-history requirement;
- preserve direction;
- handle zero-MAD cases deterministically;
- never treat insufficient history as normal.

Possible state:

```text
INSUFFICIENT_HISTORY
```

---

# 10. EWMA Trend

Default:

```text
S_t = λX_t + (1 - λ)S_(t-1)
```

Prototype default:

```text
λ = 0.30
```

EWMA answers:

> Is strain persistently rising, falling, or stable?

Rules:

- validate `0 < λ <= 1`;
- use ordered history;
- store/version the lambda value;
- do not infer a trend from a single current score.

---

# 11. Peer Anomaly

Prototype method:

```text
Isolation Forest
```

It answers:

> Is this operational feature combination unusual compared with an appropriate peer cohort?

Rules:

- peer cohort definition must be explicit;
- cohort definition must be versioned;
- private wellbeing must not be part of peer anomaly;
- sparse/invalid cohorts return unavailable state;
- contamination is a configuration value, not a claim about true prevalence;
- anomaly does not automatically mean HIGH attention.

---

# 12. Model A Prediction Target

Exactly one supervised operational target is locked for the MVP:

```text
Y_A = 1
if a defined leave-pattern anomaly occurs
within the next 30 days after prediction cutoff t,
else 0.
```

The label must be created from future observed leave records through a versioned target-definition function.

The target definition must specify:

- qualifying events;
- forward 30-day window;
- handling of cancellations/changes;
- eligibility;
- incomplete follow-up/censoring;
- version.

Never derive the target from:

```text
WSI
model output
wellbeing score
hidden synthetic variable directly
manual stress label
```

---

## 12.1 Target Definition Contract

**Reconciliation revision 1 — 2026-10-04.** Apply one versioned event function to labels, inference descriptions and VERIFY follow-up. Qualifying event occurrence must be in `(t,t+30 days]` in UTC: exactly t is excluded and exactly the end is included. The window is not a feature window.

| Event | Required evidence | Occurrence time |
|---|---|---|
| Unplanned/unscheduled leave | Authoritative actual STARTED event with explicit unplanned/unscheduled classification; an approval/request alone is insufficient | Actual leave start |
| Service-directed cancellation | Previously approved leave genuinely cancelled by SERVICE, linked to the authoritative approved version | Authoritative occurrence/effective timestamp of cancellation |
| Service-directed postponement | Previously approved leave start genuinely postponed by SERVICE, with before/after versions | Authoritative occurrence/effective timestamp of postponement |
| Service-directed recall/shortening | SERVICE ends/recalls previously approved leave earlier than its approved end; recall may map to SHORTENED with preserved source meaning | Authoritative occurrence/effective timestamp of recall/shortening |

Do not force disruptions to use the original or changed leave-start time. A service disruption inside the window can qualify even if the affected planned leave starts outside it. Routine planned leave, unchanged administrative updates, personnel-requested cancellation/postponement, denied requests and unspecified sick/long-leave heuristics are not qualifying events. ADMIN_CORRECTION corrects/retracts an underlying event; it is not itself a new disruption. Unknown initiator/classification/occurrence or missing approved reference makes eligibility uncertain, never automatically Y=0.

**REQUIRED DATA FOR FINAL TARGET:** stable personnel/leave/event IDs, planning classification, authoritative occurrence/effective timestamp and timezone, event type, initiator, approved-before/changed-after references, source revision/known_at and correction/retraction lineage. Preserve the authoritative event timestamp rather than import/created_at time. Reconcile redundant records by stable event identity; multiple qualifying events still yield one positive label.

A labelled row requires an eligible active person at t and complete observable follow-up through t+30 days, trustworthy coverage and resolved event metadata/corrections. Transfer/end-of-service/source loss censors a row if follow-up cannot be reconstructed; a fully observed authorised transfer does not itself create a positive. Incomplete/uncertain rows have null label plus eligibility/censor reason, even when partial follow-up contains a candidate event. Y=1 means at least one confirmed qualifying event in a fully eligible row; Y=0 means no such event with complete eligible follow-up. Neither missing records nor an unfinished clock means zero.

Features reconstruct source knowledge at t only. Future events are label-only and may be adjudicated at a separately recorded target_extraction_as_of. Corrections produce a new label/source revision and compatibility review, not silent alteration of old training evidence. Persist rule/document revision, event mapping, target version/hash, extraction timestamp and eligibility logic in the training manifest; legacy target version strings are not certification of equivalence.

**CURRENT LIVE-SOURCE TARGET CAPABILITY:** current leave_records fields do not by themselves establish actual starts/completions, planning classification, SERVICE initiator, event-effective timestamps, prior approvals or complete coverage. Existing precomputed labels/target_audit flags are therefore not automatically authoritative for live inference. The approved Model-A artifact remains locked; live eligibility stays unavailable until the adapter and manifest evidence pass boundary/correction/censoring and source-coverage checks at an approved cutoff. Synthetic generation must remain visibly generated. No hidden synthetic process, WSI/model score, private result or future column enters the feature vector.

---

# 13. Model A Algorithm

MVP pipeline:

```text
Explicit operational feature allowlist
        ↓
Train-fitted missing-value handling
        ↓
Train-fitted StandardScaler
        ↓
Regularized Logistic Regression
        ↓
Probability Calibration
        ↓
Calibrated 30-day event probability
```

Model A output means:

> Probability of the defined observable leave-pattern anomaly within the next 30 days.

It does not mean:

> Probability that the person is stressed.

---

# 14. Model A Outputs

Model A should expose separate outputs:

```text
operational_probability
operational_attention_state
top_operational_drivers
model_status
data_quality
as_of
model_version
```

Example:

```text
30-Day Leave-Pattern Probability: 0.63
Operational Attention: HIGH
Trend: Rising

Top Drivers:
- Night-duty concentration
- Recovery deficit
- Duty load above personal baseline
```

---

# 15. Engine B — Private Wellbeing Intelligence

Engine B is separate from Model A.

Current locked state is `INSTRUMENT_NOT_ACTIVATED`, `NOT_TRAINED`, `NOT_SHARED`. Historical wellbeing records are `LEGACY_UNGOVERNED`; they cannot be treated as current validated assessments, training evidence or shared results. The flow below is a target framework only and remains unavailable until a separate instrument/version/language/use/privacy approval.

A stronger and more defensible design is:

```text
Validated / approved self-check
        ↓
Instrument-specific scoring
        ↓
Current result
        ↓
Personal wellbeing trend
        ↓
Change from previous valid assessments
```

This avoids creating weak or artificial wellbeing ML simply to claim “two models”.

---

# 16. Engine B Inputs

Engine B may use:

```text
current voluntary self-check
previous valid self-checks
instrument version
assessment timestamps
consent status
```

Derived private trend features may include:

```text
current_valid_score
previous_score
score_change
rolling_mean
trend_slope
time_since_last_assessment
assessment_count
instrument-specific category
```

Do not combine different instruments into one fake universal mental-health score.

---

# 17. Engine B Privacy Boundary

Raw wellbeing answers remain private.

```text
PERSONNEL
    ↓
RAW WELLBEING ANSWERS
    ↓
PRIVATE STORAGE
```

Never copy raw answers to:

```text
Commander analytics
Admin dashboard
WSI
peer anomaly
operational feature matrix
general audit text
```

Welfare Officer may receive only information explicitly permitted by the privacy/consent contract.

Missing wellbeing participation must never penalize a person.

---

# 18. Engine B Output

Engine B should return an explicit private state such as:

```text
STABLE
IMPROVING
DECLINING
INSUFFICIENT_HISTORY
WELLBEING_NOT_COMPLETED
CONSENT_WITHDRAWN
```

where those labels are supported by the chosen instrument/workflow.

WELLBEING_NOT_COMPLETED is the sole machine-readable noncompletion state. The UI may display “Not completed”; NOT_COMPLETED is not a second machine state.

Example:

```text
Private Wellbeing Trend: DECLINING
Valid assessments: 3
Trend window: 30 days
```

Do not convert this into:

```text
Stress = 82%
```

---

# 19. Optional Future Model B

A trained wellbeing prediction model is optional and **not required for the MVP**.

If repeated valid observations are insufficient:

```text
WELLBEING_MODEL = NOT_TRAINED
```

Do not fabricate target labels.

Any future wellbeing ML requires a separately approved:

- instrument;
- target;
- purpose;
- consent basis;
- privacy boundary;
- validation strategy;
- output audience.

---

# 20. Model C — Evidence Fusion / Convergence

Model C connects the operational and wellbeing paths.

Its purpose is not to “average two scores”.

The locked rules version is `v1.1-truthful-source`. It produces no weighted combined score or combined probability, and Commander receives no private convergence. If Model A is available while Engine B is unavailable or unshared, the result is `OPERATIONAL_EVIDENCE_ONLY`. `NO_ELEVATED_EVIDENCE` requires both governed sources to be available/shared and independently non-elevated.

It asks:

> Do independent operational and private wellbeing signals converge strongly enough to strengthen the evidence that welfare review may be useful?

Model C must be designed as an **evidence fusion layer**, not a psychiatric “stress predictor”.

---

# 21. Two Complementary Forms of Model C

PRAHARI supports two clearly separated concepts.

## 21.1 Convergence Engine — MVP workflow

For the SIH prototype, the locked v1.1 convergence mechanism is deterministic and explainable, but it is currently unavailable because Engine B is not activated/shared.

Inputs:

```text
Model A operational attention
Model A trend / explanation
Engine B wellbeing trend
data availability
```

Output:

```text
Evidence Convergence State
```

This is not a probability.

## 21.2 Incremental-Value Model — research / validation

A second experimental classifier may compare:

```text
Model A:
Operational features only
```

versus:

```text
Model C:
Operational features
+
permitted derived wellbeing features
```

Both models must predict the **same observable target**:

```text
30-day leave-pattern anomaly
```

This asks:

> Does adding derived wellbeing information measurably improve prediction?

If not, Model A remains the operational prediction model.

---

# 22. Evidence Convergence Matrix

The MVP convergence logic should preserve the meaning of each source.

| Model A Operational Signal | Engine B Wellbeing Trend | Interpretation |
|---|---|---|
| Not elevated | Stable / no decline | No current elevated evidence from available sources |
| Elevated | Stable / no decline | Operational strain exists; inspect workload/recovery context |
| Not elevated | Declining | Private wellbeing concern; welfare/support path may be appropriate |
| Elevated | Declining | **Converging evidence; priority welfare review may be appropriate** |
| Available | Not completed / unavailable/unshared | OPERATIONAL_EVIDENCE_ONLY; do not penalize missing wellbeing |
| Unavailable | Valid wellbeing decline | Private welfare/support path remains available; do not fabricate operational risk |

This matrix is explainable and jury-friendly.

---

# 23. No Fixed 70/30 or 80/20 Weighting

Do not define:

```text
Final = 0.7 × HR + 0.3 × Wellbeing
```

unless a future empirical validation explicitly justifies such a rule.

Do not assume:

```text
HR = 80%
Wellbeing = 20%
```

The relative predictive value must be measured, not invented.

---

# 24. Model C Incremental-Value Experiment

If Model C is trained, compare:

```text
MODEL A
HR / operational features only

vs

MODEL C
HR / operational features
+
approved derived wellbeing features
```

Evaluate both using:

- PR-AUC;
- Recall;
- Precision;
- F1;
- ROC-AUC;
- Brier score;
- calibration evidence;
- lead time;
- alert burden.

The report must answer:

```text
Does derived wellbeing information add measurable predictive value?
```

Possible outcomes:

```text
YES
→ consider governed use in Welfare workflow

NO / UNCERTAIN
→ keep Model A as production predictor
```

Model C is not automatically selected because it has more features.

---

# 25. Model C Privacy Firewall

Model C is the most privacy-sensitive layer.

Its output visibility must be restricted.

## Commander

Commander receives:

```text
Model A operational intelligence
unit-level operational trends
operational explanations
approved scenarios
```

Commander does not receive:

```text
raw wellbeing
private wellbeing score
private trend details
fusion reason that reveals private disclosure
```

## Welfare Officer

Welfare Officer may receive:

```text
operational context
permitted derived wellbeing signal
evidence convergence state
support/case workflow
```

only where permitted by the approved privacy and consent rules.

## Personnel

Personnel may see:

```text
own operational context
own private wellbeing result/trend
own support pathway
```

## Admin

Admin receives:

```text
system/model health
configuration
job status
governance
```

not raw private wellbeing.

---

# 26. Anti-Inference Privacy Rule

Even a derived fused score can leak private information.

Example risk:

```text
Commander sees:
Operational signal = LOW
Combined signal = HIGH
```

The Commander could infer that private wellbeing data must have changed.

Therefore:

> Commander-facing outputs must never reveal a combined signal whose change can be used to infer a private wellbeing response.

Combined/convergence output belongs primarily to the Welfare workflow.

---

# 27. Final User-Facing Intelligence

PRAHARI should avoid presenting one mysterious number.

Preferred presentation:

```text
Operational Strain
HIGH
WSI: 74 ↑

30-Day Operational Prediction
63%

Personal Baseline
Above normal

Peer Anomaly
Detected

Private Wellbeing Trend
Declining
(only where permitted)

Evidence Convergence
STRONG
(only where permitted)

Top Operational Drivers
• Night-duty concentration
• Short recovery intervals
• Duty load above personal baseline
```

This is more explainable than:

```text
Stress = 87%
```

---

# 28. Operational Attention Policy

PRAHARI keeps these operational signals separate:

```text
WSI
baseline deviation
EWMA trend
peer anomaly
30-day calibrated probability
data quality
```

A versioned policy may map them to:

```text
LOW
MEDIUM
HIGH
```

for operational workflow filtering.

These labels mean:

```text
operational attention level
```

not:

```text
medical severity
```

The policy must be explicit, versioned, and tested.

The calculation, missing-input precedence and alert persistence contract is §8.1. BALANCE and VERIFY belong to architecture.md §§10–11; predictive analytics do not own roster constraints, implementation lifecycle or outcome observation windows.

---

# 29. Wellbeing Must Not Force Operational HIGH

A private wellbeing result must not automatically force:

```text
Operational Attention = HIGH
```

Do not implement:

```text
PHQ >= threshold → Operational HIGH
PSS >= threshold → Operational HIGH
```

or any equivalent hidden “clinical safety floor” inside operational scoring.

If a future validated instrument requires a safety-specific workflow, that workflow must be separately designed and approved.

---

# 30. Probability Calibration

Raw classifier probability is not automatically trustworthy.

Prototype:

```text
classifier
    ↓
calibration
    ↓
calibrated probability
```

Sigmoid / Platt-style calibration may be used where appropriate.

Calibration must use only training/validation data.

The test set must not be used to choose:

- feature set;
- preprocessing;
- hyperparameters;
- calibration strategy;
- operating threshold.

Evaluate calibration using:

```text
Brier score
calibration / reliability evidence
```

---

# 31. Model Training Lifecycle

Model training is offline and versioned.

Runtime startup must **never retrain the model**.

Required artifacts:

```text
model artifact
preprocessing pipeline
feature allowlist
exact feature order
model version
feature version
target version
training cutoff
dependency metadata
dataset/source checksum or provenance
evaluation report
artifact hash
```

Inference must use the exact persisted preprocessing used during training.

Missing artifact:

```text
MODEL_UNAVAILABLE
```

Never:

```text
probability = 0.12
LOW
```

as a fallback.

---

# 32. Data Split

Primary evaluation is chronological.

```text
TRAIN
older prediction dates
        ↓
VALIDATION
later prediction dates
        ↓
TEST
latest prediction dates
```

Use purge/embargo where required to prevent target-window overlap.

The split must verify:

- feature cutoff;
- target window;
- no future feature;
- complete follow-up;
- preprocessing fit only on training data;
- calibration fit only on allowed data.

---

# 33. Longitudinal vs Unseen-Person Validation

Repeated personnel across time may be valid for longitudinal forecasting.

But:

```text
same personnel across train/test
```

must not be described as:

```text
unseen-person generalization
```

If unseen-person or unseen-unit claims are desired, run separate held-out-person or held-out-unit evaluation.

---

# 34. Evaluation Metrics

Do not report only accuracy.

Required:

```text
Target prevalence
Precision
Recall
F1
ROC-AUC
PR-AUC
Confusion Matrix
Brier Score
Calibration evidence
Lead time
Alert burden
```

For imbalanced events:

```text
PR-AUC
Recall
Precision
```

are especially important.

---

# 35. Threshold Selection

Do not assume:

```text
threshold = 0.50
```

Threshold must be selected on validation data based on a documented objective such as:

- recall requirement;
- acceptable false-alert burden;
- alert budget;
- Welfare Officer capacity.

The test set remains untouched until final evaluation.

---

# 36. Lead Time

For a true future event:

```text
lead_time =
event_date - first qualifying sustained alert date
```

Report:

```text
mean lead time
median lead time
definition used
```

Do not count unavailable predictions as negative evidence.

---

# 37. Explainability

Every operational attention state should have understandable operational evidence.

Examples:

```text
High night-duty concentration
Recovery intervals shortened over the last 14 days
Duty load increased above personal baseline
Leave gap is longer than configured reference
Unit staffing pressure is elevated
```

For Logistic Regression, a local directional contribution may use:

```text
standardized_feature_value × fitted_coefficient
```

This is an explanation of model contribution, not causal proof.

Do not claim SHAP unless SHAP is actually implemented and validated.

---

# 38. Alert Engine

Alerts are workflow objects, not diagnoses.

Each alert should contain:

```text
subject
trigger_type
attention_level
as_of
explanation
policy_version
model_version where relevant
created_at
status
```

Add deduplication/cooldown.

Example key:

```text
personnel_id
+
trigger_type
+
policy_version
```

Repeated unchanged conditions should not flood the Welfare Officer.

Alerts must never automatically trigger:

```text
roster change
leave rejection
disciplinary action
posting decision
promotion decision
```

---

# 39. Missing Data / Availability States

Missingness is first-class.

Possible states:

```text
VALID
REST_DATA_MISSING
INSUFFICIENT_HISTORY
BASELINE_UNAVAILABLE
PEER_COHORT_INSUFFICIENT
MODEL_UNAVAILABLE
DATA_STALE
NOT_COMPUTED
COMPUTATION_ERROR
WELLBEING_NOT_COMPLETED
CONSENT_WITHDRAWN
```

Rules:

```text
missing rest != zero rest
missing wellbeing != low wellbeing
no self-check != healthy
insufficient history != normal
model unavailable != LOW
computation error != LOW
```

Never fill a blank with an invented healthy-looking value.

---

# 40. Data Quality / Confidence

Where useful, show a separate confidence/data-quality descriptor.

Inputs may include:

```text
input completeness
history length
recency
peer cohort size
artifact availability
calibration validity
```

Example:

```text
Operational Attention: MEDIUM
Data Confidence: LIMITED
Reason: insufficient rest-history coverage
```

Do not hide uncertainty inside the risk score.

---

# 41. Synthetic Data

Synthetic data is allowed for the SIH prototype.

It should include realistic variation:

```text
normal workload
night-duty-heavy cases
rest deficit
leave gap
deployment variation
staffing pressure
rising/falling trends
peer anomalies
repeated wellbeing assessments
future observable leave outcomes
```

A hidden latent recovery process may be used to generate realistic correlation.

But:

- hidden latent fields never become model features;
- labels follow the explicit target function;
- source-column mapping is explicit;
- synthetic metrics are demo/software-validation metrics only;
- do not claim real CAPF predictive accuracy.

---

# 42. Model A vs Model C Example

Example:

```text
Model A:
Operational-only PR-AUC = X

Model C:
Operational + permitted derived wellbeing PR-AUC = Y
```

Interpretation:

```text
If Y meaningfully improves over X:
    wellbeing adds incremental predictive value

If Y ≈ X:
    private wellbeing does not improve operational prediction enough
    to justify using it in the deployed model
```

This makes the architecture scientifically testable.

---

# 43. Why This Architecture Is Stronger

This architecture is stronger than an HR-only system because it allows independent voluntary evidence.

It is stronger than a survey-only system because operational monitoring continues even when no self-check is completed.

It is stronger than naïve fusion because:

- signals remain independently interpretable;
- missing wellbeing does not reduce operational detection;
- privacy boundaries remain visible;
- fusion value must be empirically tested;
- human reviewers see why evidence is stronger.

---

# 44. Four Important Cases

## Case A — Operational elevated + Wellbeing declining

```text
Operational Signal: HIGH
Wellbeing Trend: DECLINING
Evidence Convergence: STRONG
```

Interpretation:

```text
Multiple independent signals point toward increased welfare attention.
```

## Case B — Operational elevated + Wellbeing stable

```text
Operational Signal: HIGH
Wellbeing Trend: STABLE
```

Interpretation:

```text
Operational strain remains valid.
Private self-report does not currently show parallel deterioration.
```

## Case C — Operational normal + Wellbeing declining

```text
Operational Signal: LOW/NORMAL
Wellbeing Trend: DECLINING
```

Interpretation:

```text
Private welfare concern may exist even though HR patterns are not elevated.
Support pathway remains important.
```

## Case D — Both stable

```text
Operational Signal: not elevated
Wellbeing Trend: stable
```

Interpretation:

```text
No elevated evidence from currently available sources.
```

Never say:

```text
Stress = 0
```

---

# 45. Role Visibility

| Intelligence | Personnel | Welfare Officer | Commander | Admin |
|---|---:|---:|---:|---:|
| Own WSI / operational trend | Yes | Authorized | Unit/authorized operational view | System/data only |
| Operational Model A | Own/permitted | Authorized | Authorized operational view | Model health only |
| Raw wellbeing answers | Own only | No | No | No |
| Private wellbeing result/trend | Own | Permitted derived only | No | No |
| Evidence Convergence | Own where appropriate | Permitted | No private-derived convergence | System health only |
| Unit aggregate operational analytics | No | Authorized | Yes | System/data only |
| Model configuration/health | No | Limited | Limited | Yes |

---

# 46. Runtime Inference Flow

```text
request / scheduled job
        ↓
load governed operational data as-of t
        ↓
build explicit operational features
        ↓
validate completeness / eligibility
        ↓
calculate WSI / baseline / EWMA / peer anomaly
        ↓
load approved Model A artifact
        ↓
apply persisted preprocessing
        ↓
predict + calibrate
        ↓
generate operational explanations
        ↓
apply versioned operational attention policy
        ↓
if permitted:
    combine with derived Engine B trend
        ↓
evidence convergence state
        ↓
persist safe outputs / alerts
```

Runtime must not:

- train during module import;
- silently retrain;
- invent probabilities;
- hardcode WSI;
- use different features from training;
- silently change missing-value handling;
- expose private data through combined outputs.

---

# 47. Scheduled Analytics

APScheduler may run approved recomputation/inference jobs.

Jobs must:

- use explicit scope;
- use one as-of convention;
- avoid overlapping duplicate runs;
- log status safely;
- be idempotent/recomputable where possible;
- never fabricate success.

Training remains a separate controlled operation.

---

# 48. Persisted Output Contract

## WSI snapshot

Persist:

```text
personnel_id
unit_id / effective context
snapshot_date
wsi_score
component values
policy_version
calculated_at
```

## Baseline

Persist:

```text
metric
history window
median
MAD
deviation
EWMA
version
as_of
```

## Model output

Persist:

```text
model_version
feature_version
target_version
as_of
probability
availability_status
threshold/policy version
explanation payload
artifact reference
calculated_at
```

## Convergence output

Only if needed and privacy-approved:

```text
operational_state
wellbeing_state reference / derived state
convergence_state
policy_version
visibility_scope
calculated_at
```

Do not persist raw private answers inside general model output rows.

---

# 49. Historical Artifacts

Old saved models, fusion experiments, reports, and model cards are historical evidence unless regenerated from the current pipeline.

Do not assume:

```text
old model_a_hr.joblib = current production model
old fusion model = current final model
old challenger metrics = current validation
old model card = current authority
```

Historical artifacts must not override this specification.

---

# 50. Prohibited ML Behavior

Never:

- train on future information;
- derive the target from WSI;
- derive the target from model output;
- use hidden synthetic variables as features;
- select all numeric columns automatically;
- expose raw private wellbeing to Commander;
- map unavailable model state to LOW;
- invent missing predictions;
- force operational HIGH from private questionnaire thresholds;
- claim feature contribution proves causation;
- claim synthetic metrics are real-world validation;
- automatically modify roster;
- automatically make disciplinary/career decisions;
- use suicide/self-harm as a target.

---

# 51. Acceptance Gate — Model A

```text
[ ] Operational feature allowlist is explicit
[ ] As-of cutoff is enforced
[ ] Future-feature leakage tests pass
[ ] Hidden synthetic variable exclusion test passes
[ ] Target function is versioned
[ ] WSI reference = 77.50
[ ] WSI rejects NaN/infinity/invalid input
[ ] Baseline uses prior history only
[ ] Insufficient baseline history is explicit
[ ] EWMA is time-ordered
[ ] Peer cohort definition is explicit
[ ] Sparse cohort returns unavailable
[ ] Training preprocessing fit on train only
[ ] Runtime uses persisted preprocessing
[ ] Startup does not retrain
[ ] Missing artifact → MODEL_UNAVAILABLE
[ ] Calibration is evaluated
[ ] Precision/Recall/F1/ROC-AUC/PR-AUC reported
[ ] Confusion matrix reported
[ ] Brier/calibration evidence reported
[ ] Lead-time definition reported
[ ] Threshold selected on validation only
[ ] Human-readable explanations produced
```

---

# 52. Acceptance Gate — Engine B

```text
[ ] Consent required
[ ] Raw answers Personnel-private
[ ] Valid instrument/version defined
[ ] Input ranges validated
[ ] Reverse-scored items handled when required
[ ] Missing answers rejected or incomplete
[ ] No fake universal wellbeing score
[ ] Trend requires repeated valid assessments
[ ] Missing participation does not affect Model A
[ ] Withdrawal blocks new private processing
[ ] Commander/Admin do not receive private result
```

---

# 53. Acceptance Gate — Model C / Convergence

```text
[ ] No fixed arbitrary HR/wellbeing weight
[ ] Evidence convergence logic is explicit
[ ] Missing wellbeing does not reduce operational signal
[ ] Commander cannot infer private wellbeing from combined output
[ ] Welfare combined view obeys privacy/consent scope
[ ] No private wellbeing threshold forces operational HIGH
[ ] Combined output is never labeled clinical stress probability
```

The checklist above is the required MVP convergence/privacy gate. The following is a separate optional research gate, not a prerequisite for deterministic MVP convergence:

```text
[ ] If trained, research Model C predicts the same observable target as Model A
[ ] Only authorised derived wellbeing enters the trained experiment; no raw answers
[ ] If trained, Model A vs Model C incremental value is measured
[ ] Chronological evaluation/calibration and privacy gates in §§24–26 pass
[ ] A trained Model C is deployed only if value + privacy justification are demonstrated
```

---

# 54. Canonical Implementation Ownership

Recommended responsibilities:

```text
analytics/features.py
    → operational feature construction

analytics/wsi.py
    → deterministic WSI

analytics/baseline.py
    → Median/MAD + EWMA

analytics/peer_anomaly.py
    → Isolation Forest peer anomaly

analytics/prediction.py
    → Model A runtime inference

analytics/explanations.py
    → operational explanation

analytics/convergence.py
    → evidence convergence policy

wellbeing/instruments.py
    → private instrument validation/scoring

wellbeing/trends.py
    → private wellbeing trend

ml/targets.py
    → leave-pattern target definition

ml/train.py
    → controlled Model A / optional Model C training

ml/evaluate.py
    → evaluation

ml/calibration.py
    → probability calibration

ml/policy_config.py
    → operational attention policy

ml/artifacts/
    → approved model manifests/artifacts
```

Exact paths may change with architecture, but there must be one authoritative implementation per responsibility.

---

# 55. Final PRAHARI ML Story

PRAHARI does not depend on one opaque AI score.

It combines:

```text
Operational facts
        ↓
WSI
+
Personal baseline
+
EWMA trend
+
Peer anomaly
+
30-day Model A prediction
        ↓
Operational Explanation
```

with a separate private path:

```text
Voluntary wellbeing
        ↓
Engine B result/trend
```

and, where privacy permits:

```text
Operational Signal
        +
Private Wellbeing Trend
        ↓
Evidence Convergence
        ↓
Stronger Welfare Attention
        ↓
Human Review
```

This produces a stronger solution because:

- objective operational evidence and voluntary private evidence remain distinct;
- converging signals strengthen attention without pretending to prove a diagnosis;
- disagreements between the two signals remain informative;
- missing wellbeing never penalizes the person;
- Commander privacy is preserved;
- Welfare Officers receive richer evidence where permitted;
- the value of fusion can be scientifically tested;
- human judgment remains responsible for consequential action.

---

# 56. One-Line Technical Definition

> **PRAHARI combines explainable operational analytics with a separate voluntary private wellbeing track, then uses privacy-preserving evidence convergence to strengthen welfare attention when independent signals agree—without turning the result into a clinical stress diagnosis or automatic decision.**
