"""
PRAHARI — Personal Baseline Engine (Model-A)
Canonical Reference: AGENTS.md §5, docs/ml.md §8.1, §9

PURPOSE:
Answers: "Is this person's current operational pattern unusual compared with their own history?"

LOCKED METHOD:
Median + MAD (Median Absolute Deviation)
Standard normal consistency scaling: 1.4826

FORMULA:
z = (x - Median(X)) / (1.4826 * MAD(X))
where MAD(X) = Median(|X_i - Median(X)|)

ZERO-MAD CONTRACT (docs/ml.md §8.1):
- When MAD = 0 and current == median:
    z = 0.0, direction = EQUAL, zero_mad = True
- When MAD = 0 and current != median:
    z = None, direction = ABOVE / BELOW, zero_mad = True,
    reason = "ZERO_MAD_NONZERO_DEVIATION"
    NEVER substitute an epsilon, infinity, or fabricated z = 3.
"""

from dataclasses import dataclass
from enum import Enum
import math
import statistics
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

MAD_SCALE_FACTOR: float = 1.4826
DEFAULT_MIN_OBSERVATIONS: int = 5


class BaselineStatus(str, Enum):
    VALID = "VALID"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    CURRENT_VALUE_UNAVAILABLE = "CURRENT_VALUE_UNAVAILABLE"
    COMPUTATION_ERROR = "COMPUTATION_ERROR"


class DeviationDirection(str, Enum):
    ABOVE = "ABOVE"
    BELOW = "BELOW"
    EQUAL = "EQUAL"


@dataclass(frozen=True)
class BaselineResult:
    status: BaselineStatus
    z_score: Optional[float]
    median: Optional[float]
    mad: Optional[float]
    direction: Optional[DeviationDirection]
    zero_mad: bool
    observation_count: int
    reason: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        return self.status == BaselineStatus.VALID


def calculate_median_mad(
    values: Sequence[Any],
    min_observations: int = DEFAULT_MIN_OBSERVATIONS,
) -> Tuple[Optional[float], Optional[float]]:
    """
    Computes Median and Median Absolute Deviation (MAD):
    MAD = Median(|X_i - Median(X)|)
    Returns (None, None) if valid finite observations < min_observations.
    """
    if values is None:
        return None, None

    clean_vals: List[float] = []
    for v in values:
        if v is None:
            continue
        try:
            fv = float(v)
            if not (math.isnan(fv) or math.isinf(fv)):
                clean_vals.append(fv)
        except (TypeError, ValueError):
            continue

    if len(clean_vals) < min_observations:
        return None, None

    med = statistics.median(clean_vals)
    devs = [abs(x - med) for x in clean_vals]
    mad = statistics.median(devs)
    return round(float(med), 4), round(float(mad), 4)


def calculate_robust_z_score(
    current_val: Optional[float],
    median: Optional[float],
    mad: Optional[float],
) -> Optional[float]:
    """
    Computes robust z-score:
    z = (x - Median(X)) / (1.4826 * MAD(X))

    Zero-MAD rule (docs/ml.md §8.1):
    - If MAD == 0 and current == median: returns 0.0
    - If MAD == 0 and current != median: returns None (no finite standardized deviation claimed)
    - Never fabricates z = 3 or substitutes an epsilon.
    """
    if current_val is None or median is None or mad is None:
        return None

    try:
        c_val = float(current_val)
        m_val = float(median)
        mad_val = float(mad)
    except (TypeError, ValueError):
        return None

    if math.isnan(c_val) or math.isinf(c_val):
        return None
    if math.isnan(m_val) or math.isinf(m_val) or math.isnan(mad_val) or math.isinf(mad_val):
        return None

    if mad_val == 0.0:
        return 0.0 if c_val == m_val else None

    z = (c_val - m_val) / (MAD_SCALE_FACTOR * mad_val)
    return round(float(z), 4)


def compute_personal_baseline(
    history: Sequence[Any],
    current_val: Optional[Any] = None,
    *,
    min_observations: int = DEFAULT_MIN_OBSERVATIONS,
) -> BaselineResult:
    """
    Authoritative personal baseline engine returning structured BaselineResult.

    Validates:
    - Minimum history count (INSUFFICIENT_HISTORY if < min_observations)
    - Current value availability (CURRENT_VALUE_UNAVAILABLE if None)
    - Non-finite errors (COMPUTATION_ERROR)
    - Zero-MAD non-zero deviation (retains valid median/MAD, z=None, reason='ZERO_MAD_NONZERO_DEVIATION')
    """
    if history is None:
        return BaselineResult(
            status=BaselineStatus.INSUFFICIENT_HISTORY,
            z_score=None,
            median=None,
            mad=None,
            direction=None,
            zero_mad=False,
            observation_count=0,
            reason="Historical observations sequence is None.",
        )

    clean_vals: List[float] = []
    has_invalid = False
    for v in history:
        if v is None:
            continue
        try:
            fv = float(v)
            if math.isnan(fv) or math.isinf(fv):
                has_invalid = True
            else:
                clean_vals.append(fv)
        except (TypeError, ValueError):
            has_invalid = True

    if len(clean_vals) < min_observations:
        reason = (
            f"Insufficient history: found {len(clean_vals)} valid observations, "
            f"minimum required is {min_observations}."
        )
        if has_invalid:
            reason += " (Some historical values were invalid/non-finite)."
        return BaselineResult(
            status=BaselineStatus.INSUFFICIENT_HISTORY,
            z_score=None,
            median=None,
            mad=None,
            direction=None,
            zero_mad=False,
            observation_count=len(clean_vals),
            reason=reason,
        )

    med = round(float(statistics.median(clean_vals)), 4)
    devs = [abs(x - med) for x in clean_vals]
    mad = round(float(statistics.median(devs)), 4)
    zero_mad = (mad == 0.0)

    # Current value validation
    if current_val is None:
        return BaselineResult(
            status=BaselineStatus.CURRENT_VALUE_UNAVAILABLE,
            z_score=None,
            median=med,
            mad=mad,
            direction=None,
            zero_mad=zero_mad,
            observation_count=len(clean_vals),
            reason="Current observation value is missing (None).",
        )

    try:
        c_val = float(current_val)
    except (TypeError, ValueError):
        return BaselineResult(
            status=BaselineStatus.COMPUTATION_ERROR,
            z_score=None,
            median=med,
            mad=mad,
            direction=None,
            zero_mad=zero_mad,
            observation_count=len(clean_vals),
            reason=f"Current observation value is not numeric: {current_val!r}.",
        )

    if math.isnan(c_val) or math.isinf(c_val):
        return BaselineResult(
            status=BaselineStatus.COMPUTATION_ERROR,
            z_score=None,
            median=med,
            mad=mad,
            direction=None,
            zero_mad=zero_mad,
            observation_count=len(clean_vals),
            reason=f"Current observation value is non-finite: {c_val}.",
        )

    # Direction
    if c_val > med:
        direction = DeviationDirection.ABOVE
    elif c_val < med:
        direction = DeviationDirection.BELOW
    else:
        direction = DeviationDirection.EQUAL

    # Zero-MAD branch
    if zero_mad:
        if c_val == med:
            return BaselineResult(
                status=BaselineStatus.VALID,
                z_score=0.0,
                median=med,
                mad=0.0,
                direction=DeviationDirection.EQUAL,
                zero_mad=True,
                observation_count=len(clean_vals),
                reason=None,
            )
        else:
            return BaselineResult(
                status=BaselineStatus.VALID,
                z_score=None,
                median=med,
                mad=0.0,
                direction=direction,
                zero_mad=True,
                observation_count=len(clean_vals),
                reason="ZERO_MAD_NONZERO_DEVIATION",
            )

    # Normal MAD > 0 branch
    z = (c_val - med) / (MAD_SCALE_FACTOR * mad)
    return BaselineResult(
        status=BaselineStatus.VALID,
        z_score=round(float(z), 4),
        median=med,
        mad=mad,
        direction=direction,
        zero_mad=False,
        observation_count=len(clean_vals),
        reason=None,
    )


def calculate_ewma(series: List[float], alpha: float = 0.30) -> Optional[float]:
    """
    Computes Exponentially Weighted Moving Average (EWMA):
    S_t = lambda * X_t + (1 - lambda) * S_(t-1)
    Locked default: lambda = 0.30.
    Initializes S_0 = X_0 with the first valid observation (NEVER artificial zero).
    """
    from app.analytics.ewma import calculate_ewma as _ewma
    return _ewma(series, lambda_param=alpha)
