"""
PRAHARI — Operational Data Quality Layer (Model-A)
Canonical Reference: AGENTS.md §11, docs/ml.md §6.1, §8.1

PURPOSE:
Provides reusable, deterministic data-quality validation for raw operational
data sources (duties, rest_records, leave_records, staffing, deployments).

GOVERNING RULES:
1. Truthful State Rule: Invalid, non-finite, or negative physical values must
   NEVER be clamped to 0.0, transformed via abs(), or silently treated as healthy.
2. Missing values must NEVER be imputed with zero without explicit coverage verification.
3. Explicit quality statuses:
   - VALID: Physically valid and within approved domain bounds.
   - MISSING: Required value is absent / None.
   - INVALID: Non-finite, negative where prohibited, or physically impossible.
   - INSUFFICIENT_DATA: Record count in window is below minimum required observations,
     or no records exist in the evaluation window.
"""

from dataclasses import dataclass
from enum import Enum
import math
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union


class QualityStatus(str, Enum):
    VALID = "VALID"
    MISSING = "MISSING"
    INVALID = "INVALID"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass(frozen=True)
class QualityResult:
    status: QualityStatus
    value: Optional[float]
    reason: Optional[str] = None
    original_input: Any = None

    @property
    def is_valid(self) -> bool:
        return self.status == QualityStatus.VALID


@dataclass(frozen=True)
class WindowQualityResult:
    status: QualityStatus
    valid_count: int
    missing_count: int
    invalid_count: int
    total_expected: int
    valid_values: List[float]
    reasons: List[str]

    @property
    def is_valid(self) -> bool:
        return self.status == QualityStatus.VALID


# --- Single Field Validators ---

def validate_numeric_measure(
    name: str,
    val: Any,
    *,
    min_val: Optional[float] = 0.0,
    max_val: Optional[float] = None,
    allow_zero: bool = True,
) -> QualityResult:
    """
    Validates a single numeric operational measurement.
    Rejects None (MISSING), non-numeric/non-finite/out-of-bounds (INVALID).
    Never clamps or repairs invalid data.
    """
    if val is None:
        return QualityResult(
            status=QualityStatus.MISSING,
            value=None,
            reason=f"Measurement '{name}' is missing (None).",
            original_input=val,
        )
    try:
        f_val = float(val)
    except (TypeError, ValueError):
        return QualityResult(
            status=QualityStatus.INVALID,
            value=None,
            reason=f"Measurement '{name}' is not numeric: {val!r}.",
            original_input=val,
        )

    if math.isnan(f_val) or math.isinf(f_val):
        return QualityResult(
            status=QualityStatus.INVALID,
            value=None,
            reason=f"Measurement '{name}' is non-finite: {f_val}.",
            original_input=val,
        )

    if min_val is not None:
        if not allow_zero and f_val == 0.0:
            return QualityResult(
                status=QualityStatus.INVALID,
                value=None,
                reason=f"Measurement '{name}' must be positive, got 0.0.",
                original_input=val,
            )
        if f_val < min_val:
            return QualityResult(
                status=QualityStatus.INVALID,
                value=None,
                reason=f"Measurement '{name}' value {f_val} < minimum allowed {min_val}. Clamping prohibited.",
                original_input=val,
            )

    if max_val is not None and f_val > max_val:
        return QualityResult(
            status=QualityStatus.INVALID,
            value=None,
            reason=f"Measurement '{name}' value {f_val} > maximum allowed {max_val}. Clamping prohibited.",
            original_input=val,
        )

    return QualityResult(
        status=QualityStatus.VALID,
        value=f_val,
        reason=None,
        original_input=val,
    )


def validate_rest_hours(rest_hours: Any) -> QualityResult:
    """
    Validates daily rest hours.
    Physically valid daily rest must be in [0.0, 24.0] hours.
    Negative rest hours (e.g. 1,918 retained seed errors) are flagged as INVALID.
    """
    return validate_numeric_measure("rest_hours", rest_hours, min_val=0.0, max_val=24.0)


def validate_rest_gap(rest_gap_hours: Any) -> QualityResult:
    """
    Validates rest gap between consecutive shifts.
    Gap must be non-negative (>= 0.0 hours).
    Negative rest gap hours (e.g. 1,963 retained seed errors) are flagged as INVALID.
    """
    return validate_numeric_measure("rest_gap_hours", rest_gap_hours, min_val=0.0, max_val=168.0)


def validate_duty_hours(duty_hours: Any, max_single_shift: float = 24.0) -> QualityResult:
    """
    Validates completed duty hours for a shift or daily total.
    Must be in [0.0, max_single_shift] hours.
    """
    return validate_numeric_measure("duty_hours", duty_hours, min_val=0.0, max_val=max_single_shift)


def validate_staffing_demand(available_strength: Any, required_strength: Any) -> QualityResult:
    """
    Validates unit staffing metrics.
    available_strength >= 0, required_strength > 0.
    """
    avail_res = validate_numeric_measure("available_strength", available_strength, min_val=0.0)
    if not avail_res.is_valid:
        return avail_res

    req_res = validate_numeric_measure("required_strength", required_strength, min_val=0.0, allow_zero=False)
    if not req_res.is_valid:
        return req_res

    return QualityResult(
        status=QualityStatus.VALID,
        value=avail_res.value / req_res.value,
        reason=None,
        original_input=(available_strength, required_strength),
    )


# --- Window / Aggregate Quality Validators ---

def validate_window_series(
    records: Sequence[Any],
    *,
    min_observations: int = 1,
    total_expected: Optional[int] = None,
    value_extractor: Optional[Callable[[Any], Any]] = None,
    validator: Callable[[Any], QualityResult] = validate_rest_hours,
    allow_partial: bool = False,
) -> WindowQualityResult:
    """
    Validates a sequence of observation records across an evaluation window.

    Status Rules:
    - If records is empty: INSUFFICIENT_DATA
    - If any record is INVALID: returns INVALID (unless quarantined in allow_partial mode)
    - If valid observations < min_observations: INSUFFICIENT_DATA
    - If valid observations >= min_observations: VALID
    """
    expected = total_expected if total_expected is not None else len(records)
    reasons: List[str] = []

    if not records:
        return WindowQualityResult(
            status=QualityStatus.INSUFFICIENT_DATA,
            valid_count=0,
            missing_count=0,
            invalid_count=0,
            total_expected=expected,
            valid_values=[],
            reasons=["No records found in evaluation window."],
        )

    valid_vals: List[float] = []
    missing_count = 0
    invalid_count = 0

    for idx, rec in enumerate(records):
        raw_val = value_extractor(rec) if value_extractor else rec
        res = validator(raw_val)
        if res.status == QualityStatus.VALID:
            valid_vals.append(res.value)
        elif res.status == QualityStatus.MISSING:
            missing_count += 1
        elif res.status == QualityStatus.INVALID:
            invalid_count += 1
            reasons.append(f"Index {idx}: {res.reason}")

    # Decision logic
    if invalid_count > 0 and not allow_partial:
        return WindowQualityResult(
            status=QualityStatus.INVALID,
            valid_count=len(valid_vals),
            missing_count=missing_count,
            invalid_count=invalid_count,
            total_expected=expected,
            valid_values=valid_vals,
            reasons=reasons,
        )

    if len(valid_vals) < min_observations:
        reasons.append(
            f"Insufficient observations: found {len(valid_vals)} valid points, "
            f"minimum required is {min_observations} (expected {expected})."
        )
        return WindowQualityResult(
            status=QualityStatus.INSUFFICIENT_DATA,
            valid_count=len(valid_vals),
            missing_count=missing_count,
            invalid_count=invalid_count,
            total_expected=expected,
            valid_values=valid_vals,
            reasons=reasons,
        )

    return WindowQualityResult(
        status=QualityStatus.VALID,
        valid_count=len(valid_vals),
        missing_count=missing_count,
        invalid_count=invalid_count,
        total_expected=expected,
        valid_values=valid_vals,
        reasons=[],
    )
