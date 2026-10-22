"""
Unit tests for Task 05: Data Quality Layer (PRAHARI Model-A).
Tests required:
- negative value (rejected, never clamped to 0.0 or abs())
- missing value (explicit MISSING status, never imputed with 0.0)
- valid value (explicit VALID status with numeric output)
- partial window (INSUFFICIENT_DATA status reporting observed vs required)
- no records (INSUFFICIENT_DATA status)
"""

import math
import pytest

from app.analytics.data_quality import (
    QualityResult,
    QualityStatus,
    WindowQualityResult,
    validate_duty_hours,
    validate_numeric_measure,
    validate_rest_gap,
    validate_rest_hours,
    validate_staffing_demand,
    validate_window_series,
)


def test_t05_negative_value_rejected_no_clamping():
    """Verify negative rest hours, rest gaps, and duties return INVALID without clamping."""
    # Negative rest hours (e.g. from the 1,918 negative seed records)
    res_rest = validate_rest_hours(-6.5)
    assert res_rest.status == QualityStatus.INVALID
    assert res_rest.value is None
    assert "Clamping prohibited" in (res_rest.reason or "")

    # Negative rest gap hours (e.g. from the 1,963 negative seed records)
    res_gap = validate_rest_gap(-12.0)
    assert res_gap.status == QualityStatus.INVALID
    assert res_gap.value is None
    assert "Clamping prohibited" in (res_gap.reason or "")

    # Negative duty hours
    res_duty = validate_duty_hours(-4.0)
    assert res_duty.status == QualityStatus.INVALID
    assert res_duty.value is None
    assert "Clamping prohibited" in (res_duty.reason or "")


def test_t05_missing_value_handled_explicitly():
    """Verify None/missing values return MISSING status and are never imputed as zero."""
    res_rest = validate_rest_hours(None)
    assert res_rest.status == QualityStatus.MISSING
    assert res_rest.value is None
    assert "missing" in (res_rest.reason or "").lower()

    res_gap = validate_rest_gap(None)
    assert res_gap.status == QualityStatus.MISSING
    assert res_gap.value is None

    res_duty = validate_duty_hours(None)
    assert res_duty.status == QualityStatus.MISSING
    assert res_duty.value is None


def test_t05_valid_value_passes():
    """Verify physically valid measurements return VALID status with float value."""
    res_rest = validate_rest_hours(8.0)
    assert res_rest.status == QualityStatus.VALID
    assert res_rest.value == 8.0
    assert res_rest.is_valid is True
    assert res_rest.reason is None

    res_gap = validate_rest_gap(14.5)
    assert res_gap.status == QualityStatus.VALID
    assert res_gap.value == 14.5

    res_duty = validate_duty_hours(8.0)
    assert res_duty.status == QualityStatus.VALID
    assert res_duty.value == 8.0

    res_staffing = validate_staffing_demand(available_strength=85, required_strength=100)
    assert res_staffing.status == QualityStatus.VALID
    assert res_staffing.value == 0.85


def test_t05_partial_window_insufficient_data():
    """Verify windows with fewer than required observations return INSUFFICIENT_DATA."""
    # 7-day window, but only 3 daily records exist; min_observations is 5
    records = [7.5, 8.0, 6.5]
    res = validate_window_series(
        records,
        min_observations=5,
        total_expected=7,
        validator=validate_rest_hours,
    )
    assert res.status == QualityStatus.INSUFFICIENT_DATA
    assert res.valid_count == 3
    assert res.total_expected == 7
    assert len(res.valid_values) == 3
    assert any("Insufficient observations" in r for r in res.reasons)


def test_t05_no_records_insufficient_data():
    """Verify empty record sequence returns INSUFFICIENT_DATA."""
    res = validate_window_series(
        [],
        min_observations=1,
        total_expected=7,
        validator=validate_rest_hours,
    )
    assert res.status == QualityStatus.INSUFFICIENT_DATA
    assert res.valid_count == 0
    assert len(res.valid_values) == 0
    assert any("No records found" in r for r in res.reasons)


def test_t05_window_with_negative_values_fails_invalid():
    """Verify window containing negative/corrupt records is flagged as INVALID."""
    # Window with 6 valid records and 1 negative record
    records = [8.0, 7.5, -4.0, 8.0, 7.0, 8.5, 6.0]
    res = validate_window_series(
        records,
        min_observations=5,
        total_expected=7,
        validator=validate_rest_hours,
    )
    assert res.status == QualityStatus.INVALID
    assert res.valid_count == 6
    assert res.invalid_count == 1
    assert any("Clamping prohibited" in r for r in res.reasons)


def test_t05_non_finite_values_rejected():
    """Verify NaN and Inf are rejected as INVALID."""
    res_nan = validate_numeric_measure("test", float("nan"))
    assert res_nan.status == QualityStatus.INVALID
    assert "non-finite" in (res_nan.reason or "").lower()

    res_inf = validate_numeric_measure("test", float("inf"))
    assert res_inf.status == QualityStatus.INVALID
    assert "non-finite" in (res_inf.reason or "").lower()
