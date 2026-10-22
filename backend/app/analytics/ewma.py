"""
PRAHARI — EWMA Trend Engine (Model-A)
Canonical Reference: AGENTS.md §5, docs/ml.md §8.1, §10

LOCKED PARAMETER:
lambda = 0.30 (prototype default, replaces legacy 0.20)

RECURSION:
S_t = lambda * X_t + (1 - lambda) * S_(t-1)

SEGMENT & INITIALIZATION RULES (docs/ml.md §8.1):
1. Never initialize with artificial zero.
   Initialize each consecutive valid daily segment at its first observation: S_0 = X_0.
2. A missing/invalid day breaks the segment; resume with a new initialization.
   Never silently compress time or carry an old value as current.
3. If current observation is missing or invalid, current EWMA is unavailable.
4. Trend requires minimum segment length of at least 2 points:
   delta = current EWMA - preceding daily EWMA
   - RISING: delta > stability_tolerance
   - FALLING: delta < -stability_tolerance
   - STABLE: abs(delta) <= stability_tolerance
   A lone point has no trend (INSUFFICIENT_HISTORY).
"""

from dataclasses import dataclass
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Sequence, Union

DEFAULT_LAMBDA: float = 0.30
DEFAULT_MIN_SEGMENT_LENGTH: int = 2
DEFAULT_STABILITY_TOLERANCE: float = 1.0


class TrendDirection(str, Enum):
    RISING = "RISING"
    FALLING = "FALLING"
    STABLE = "STABLE"


class EwmaStatus(str, Enum):
    VALID = "VALID"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    CURRENT_VALUE_UNAVAILABLE = "CURRENT_VALUE_UNAVAILABLE"
    COMPUTATION_ERROR = "COMPUTATION_ERROR"


@dataclass(frozen=True)
class EwmaResult:
    status: EwmaStatus
    current_ewma: Optional[float]
    trend: Optional[TrendDirection]
    delta: Optional[float]
    segment_length: int
    ewma_series: List[Optional[float]]
    lambda_param: float = DEFAULT_LAMBDA
    reason: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        return self.status == EwmaStatus.VALID


def calculate_ewma(
    series: Sequence[Optional[float]],
    lambda_param: float = DEFAULT_LAMBDA,
    *,
    break_on_missing: bool = False,
) -> Optional[float]:
    """
    Computes EWMA of a series using canonical lambda (locked default 0.30).
    Initializes S_0 = X_0 with the first valid observation (NEVER artificial zero).

    If break_on_missing=True, missing values reset the active segment per ml.md §8.1.
    If break_on_missing=False, filters None while maintaining chronological order.
    """
    if not series:
        return None

    if lambda_param <= 0.0 or lambda_param > 1.0:
        raise ValueError(f"lambda_param must be in (0, 1], got {lambda_param}")

    if break_on_missing:
        current_s: Optional[float] = None
        for val in series:
            if val is None:
                current_s = None
                continue
            try:
                fv = float(val)
                if math.isnan(fv) or math.isinf(fv):
                    current_s = None
                    continue
            except (TypeError, ValueError):
                current_s = None
                continue

            if current_s is None:
                current_s = fv
            else:
                current_s = lambda_param * fv + (1.0 - lambda_param) * current_s
        return round(current_s, 4) if current_s is not None else None
    else:
        clean_vals: List[float] = []
        for v in series:
            if v is not None:
                try:
                    fv = float(v)
                    if not (math.isnan(fv) or math.isinf(fv)):
                        clean_vals.append(fv)
                except (TypeError, ValueError):
                    pass

        if not clean_vals:
            return None

        s = clean_vals[0]
        for x in clean_vals[1:]:
            s = lambda_param * x + (1.0 - lambda_param) * s
        return round(s, 4)


def compute_ewma_trend(
    series: Sequence[Optional[float]],
    lambda_param: float = DEFAULT_LAMBDA,
    min_segment_length: int = DEFAULT_MIN_SEGMENT_LENGTH,
    stability_tolerance: float = DEFAULT_STABILITY_TOLERANCE,
) -> EwmaResult:
    """
    Detailed, segment-aware EWMA engine with trend classification per docs/ml.md §8.1.
    """
    if not series:
        return EwmaResult(
            status=EwmaStatus.INSUFFICIENT_HISTORY,
            current_ewma=None,
            trend=None,
            delta=None,
            segment_length=0,
            ewma_series=[],
            lambda_param=lambda_param,
            reason="Empty observation series.",
        )

    ewma_history: List[Optional[float]] = []
    current_segment_len = 0
    current_s: Optional[float] = None
    prev_s: Optional[float] = None

    for val in series:
        if val is None:
            current_s = None
            current_segment_len = 0
            ewma_history.append(None)
            continue

        try:
            fv = float(val)
            if math.isnan(fv) or math.isinf(fv):
                current_s = None
                current_segment_len = 0
                ewma_history.append(None)
                continue
        except (TypeError, ValueError):
            current_s = None
            current_segment_len = 0
            ewma_history.append(None)
            continue

        if current_s is None:
            current_s = fv
            prev_s = None
            current_segment_len = 1
        else:
            prev_s = current_s
            current_s = lambda_param * fv + (1.0 - lambda_param) * current_s
            current_segment_len += 1

        ewma_history.append(round(current_s, 4))

    if current_s is None:
        return EwmaResult(
            status=EwmaStatus.CURRENT_VALUE_UNAVAILABLE,
            current_ewma=None,
            trend=None,
            delta=None,
            segment_length=0,
            ewma_series=ewma_history,
            lambda_param=lambda_param,
            reason="Current observation is missing or invalid.",
        )

    final_ewma = round(current_s, 4)

    if current_segment_len < min_segment_length or prev_s is None:
        return EwmaResult(
            status=EwmaStatus.INSUFFICIENT_HISTORY,
            current_ewma=final_ewma,
            trend=None,
            delta=None,
            segment_length=current_segment_len,
            ewma_series=ewma_history,
            lambda_param=lambda_param,
            reason=f"Segment length ({current_segment_len}) is below minimum for trend ({min_segment_length}).",
        )

    delta = round(final_ewma - round(prev_s, 4), 4)
    if delta > stability_tolerance:
        trend = TrendDirection.RISING
    elif delta < -stability_tolerance:
        trend = TrendDirection.FALLING
    else:
        trend = TrendDirection.STABLE

    return EwmaResult(
        status=EwmaStatus.VALID,
        current_ewma=final_ewma,
        trend=trend,
        delta=delta,
        segment_length=current_segment_len,
        ewma_series=ewma_history,
        lambda_param=lambda_param,
        reason=None,
    )
