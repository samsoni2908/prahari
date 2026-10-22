"""
PRAHARI Analytics Package.
"""
from app.analytics.baseline import (
    MAD_SCALE_FACTOR,
    BaselineResult,
    BaselineStatus,
    DeviationDirection,
    calculate_median_mad,
    calculate_robust_z_score,
    compute_personal_baseline,
)
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
from app.analytics.ewma import (
    DEFAULT_LAMBDA,
    EwmaResult,
    EwmaStatus,
    TrendDirection,
    calculate_ewma,
    compute_ewma_trend,
)
from app.analytics.wsi import (
    WSI_POLICY_VERSION,
    WSI_VERSION,
    WSI_WEIGHTS,
    REFERENCE_INPUT,
    REFERENCE_WSI,
    calculate_wsi,
    compute_wsi,
    compute_wsi_detailed,
    get_strain_severity,
    get_wsi_category,
)

__all__ = [
    # Data Quality
    "QualityResult",
    "QualityStatus",
    "WindowQualityResult",
    "validate_duty_hours",
    "validate_numeric_measure",
    "validate_rest_gap",
    "validate_rest_hours",
    "validate_staffing_demand",
    "validate_window_series",
    # WSI
    "WSI_POLICY_VERSION",
    "WSI_VERSION",
    "WSI_WEIGHTS",
    "REFERENCE_INPUT",
    "REFERENCE_WSI",
    "calculate_wsi",
    "compute_wsi",
    "compute_wsi_detailed",
    "get_strain_severity",
    "get_wsi_category",
    # Baseline
    "MAD_SCALE_FACTOR",
    "BaselineResult",
    "BaselineStatus",
    "DeviationDirection",
    "calculate_median_mad",
    "calculate_robust_z_score",
    "compute_personal_baseline",
    # EWMA
    "DEFAULT_LAMBDA",
    "EwmaResult",
    "EwmaStatus",
    "TrendDirection",
    "calculate_ewma",
    "compute_ewma_trend",
]
