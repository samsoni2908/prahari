import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


# --- Auth & User Schemas ---
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: uuid.UUID
    username: str
    role: str
    personnel_id: Optional[uuid.UUID] = None
    unit_id: Optional[uuid.UUID] = None


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    username: str
    role: str
    personnel_id: Optional[uuid.UUID] = None
    unit_id: Optional[uuid.UUID] = None
    is_active: bool
    created_at: datetime


# --- Master Data Schemas ---
class UnitSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    unit_code: str
    unit_name: str
    unit_type: str
    location_label: Optional[str] = None
    sanctioned_strength: int
    is_active: bool


class PersonnelSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    personnel_code: str
    pseudo_id: str
    unit_id: uuid.UUID
    rank_or_grade: str
    role_title: str
    status: str
    joining_date: Optional[date] = None
    service_years: Optional[float] = None


# --- Analytics Schemas ---
class WsiComponentBreakdown(BaseModel):
    wsi_score: float
    d_component: float
    r_component: float
    c_component: float
    n_component: float
    l_component: float
    h_component: float
    s_component: float
    policy_version: str
    snapshot_date: date


class BaselineMetricSummary(BaseModel):
    metric_name: str
    current_value: Optional[float]
    median_value: Optional[float]
    mad_value: Optional[float]
    z_score: Optional[float]
    ewma_value: Optional[float]
    history_count: int
    baseline_status: str
    metric_date: date


class AnomalySummary(BaseModel):
    id: uuid.UUID
    event_date: date
    algorithm: str
    anomaly_score: Optional[float]
    is_anomaly: bool


class PredictionSummary(BaseModel):
    id: Optional[uuid.UUID] = None
    prediction_date: Optional[date] = None
    target_name: Optional[str] = None
    status: str = "MODEL_UNAVAILABLE"
    prediction_probability: Optional[float] = None
    predicted_class: Optional[int] = None
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    explanation_json: Optional[Dict[str, Any]] = None


class AlertItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    personnel_id: Optional[uuid.UUID] = None
    unit_id: uuid.UUID
    alert_type: str
    severity: str
    source_type: str
    source_id: Optional[uuid.UUID] = None
    status: str
    dedupe_key: str
    message: str
    created_at: datetime
    resolved_at: Optional[datetime] = None


# --- Commander Overview & Risk Schemas ---
class CommanderOverview(BaseModel):
    unit_id: uuid.UUID
    unit_name: str
    unit_code: str
    total_personnel: int
    average_wsi: float
    high_strain_count: int
    elevated_count: int
    normal_count: int
    active_alerts_count: int
    unresolved_support_requests: int
    recent_anomalies_count: int


class PersonnelStrainCard(BaseModel):
    pseudo_id: str
    rank_or_grade: str
    role_title: str
    status: str
    current_wsi: float
    ewma_trend: str  # "RISING", "STABLE", "FALLING"
    primary_driver: str  # e.g. "Rest Deficit (R: 85.0)", "Night Shift Concentration (N: 80.0)"
    has_anomaly: bool
    prediction_status: str = "MODEL_UNAVAILABLE"
    prediction_probability: Optional[float] = None
    prediction_alert: bool = False
    active_alert_count: int = 0


# --- What-If & Scenario Schemas ---
class ScenarioCreateRequest(BaseModel):
    scenario_name: str
    unit_id: uuid.UUID
    changes: List[Dict[str, Any]] = Field(default_factory=list)


class ScenarioDetail(BaseModel):
    id: uuid.UUID
    unit_id: uuid.UUID
    scenario_name: str
    status: str
    optimizer_method: str
    before_metrics: Dict[str, Any]
    after_metrics: Dict[str, Any]
    constraint_results: Dict[str, Any]
    created_at: datetime
    changes: List[Dict[str, Any]] = Field(default_factory=list)


class ApprovalRequest(BaseModel):
    decision: str  # ACCEPT, MODIFY, REJECT
    reason: str


class OutcomeCreateRequest(BaseModel):
    observation_date: date
    observed_metrics: Dict[str, Any]
    wsi_change: Optional[float] = None
    operational_event_observed: Optional[bool] = None
    notes: Optional[str] = None


# --- Private Personnel & Wellbeing Schemas ---
class WellbeingConsentStatus(BaseModel):
    has_consented: bool
    consent_version: Optional[str] = None
    consented_at: Optional[datetime] = None


class WellbeingConsentSubmit(BaseModel):
    purpose: str = "Voluntary operational stress recovery tracking and confidential welfare assessment"
    consent_version: str = "1.0"
    status: str = "ACTIVE"


class SelfCheckSubmit(BaseModel):
    instrument_name: str = "PRAHARI_SELF_CHECK"
    instrument_version: str = "1.0"
    answers: Dict[str, Any]


class SelfCheckHistoryItem(BaseModel):
    id: uuid.UUID
    assessment_date: date
    instrument_name: str
    composite_score: Optional[float] = None
    created_at: datetime


class SupportRequestCreate(BaseModel):
    request_type: str  # REST_DEFICIT, FAMILY_EMERGENCY, MEDICAL_ASSISTANCE, ROSTER_EXHAUSTION
    priority: str = "MEDIUM"  # LOW, MEDIUM, HIGH, URGENT
    request_text: Optional[str] = None


class SupportRequestDetail(BaseModel):
    id: uuid.UUID
    personnel_id: uuid.UUID
    request_type: str
    status: str  # SUBMITTED, UNDER_REVIEW, ACTION_SCHEDULED, RESOLVED
    priority: str
    request_text: Optional[str] = None
    follow_up_date: Optional[date] = None
    closed_at: Optional[datetime] = None
    created_at: datetime


# --- Audit & Governance Schemas ---
class AuditEventItem(BaseModel):
    id: uuid.UUID
    actor_user_id: Optional[uuid.UUID]
    actor_role: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[uuid.UUID]
    result: str
    reason: Optional[str]
    metadata_json: Optional[Dict[str, Any]] = None
    created_at: datetime


class PolicyConfigItem(BaseModel):
    id: uuid.UUID
    policy_key: str
    policy_value_json: Dict[str, Any]
    version: str
    effective_from: datetime
