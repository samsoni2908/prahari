"""Current operational projections; unavailable values stay null."""
from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict


class Projection(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Coverage(Projection):
    required_days: int
    observed_days: int


class Component(Projection):
    weight: float
    value: float | None
    contribution: float | None
    input_state: Literal["VALID", "COMPONENT_INPUT_UNAVAILABLE"]
    reason: str | None


class WsiMetric(Projection):
    status: Literal["VALID", "NOT_COMPUTED", "DATA_STALE", "INSUFFICIENT_HISTORY", "REST_DATA_MISSING", "COMPUTATION_ERROR"]
    value: float | None
    reason_codes: list[str]
    as_of: date
    source_timestamp: datetime | None
    source_hash: str | None
    policy_version: str | None
    coverage: Coverage
    components: dict[Literal["D", "R", "C", "N", "L", "H", "S"], Component]
    freshness: Literal["UNAVAILABLE", "CURRENT_AT_CUTOFF"]
    raw_measures: dict[str, float] | None = None
    unrounded_value: float | None = None
    excluded_zero_demand_days: int | None = None
    peer_vector: list[float] | None = None


class BaselineView(Projection):
    status: Literal["BASELINE_UNAVAILABLE", "VALID", "INSUFFICIENT_HISTORY", "CURRENT_VALUE_UNAVAILABLE", "COMPUTATION_ERROR"]
    z_score: float | None
    median: float | None = None
    mad: float | None = None
    direction: Literal["ABOVE", "BELOW", "EQUAL"] | None = None
    zero_mad: bool | None = None
    observation_count: int | None = None
    reason: str | None = None


class TrendView(Projection):
    status: Literal["NOT_COMPUTED", "VALID", "INSUFFICIENT_HISTORY", "CURRENT_VALUE_UNAVAILABLE", "COMPUTATION_ERROR"]
    current_ewma: float | None
    trend: Literal["RISING", "FALLING", "STABLE"] | None
    delta: float | None = None
    segment_length: int | None = None
    ewma_series: list[float | None] | None = None
    lambda_param: float | None = None
    reason: str | None = None


class PeerView(Projection):
    status: str
    anomaly_strength: float | None
    reason: str | None = None
    score: float | None = None
    anomaly_score: float | None = None
    is_anomaly: bool | None = None
    is_peer_anomaly: bool | None = None
    cohort_size: int | None = None
    cohort_hash: str | None = None
    policy_version: str | None = None


class OperationalAnalyticsView(Projection):
    wsi: WsiMetric
    baseline: BaselineView
    trend: TrendView
    peer: PeerView
