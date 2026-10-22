"""PRAHARI Operational Policy Configuration Constants.

Governs non-clinical terminology rules, alert budget defaults, and operational thresholds.
"""

from typing import Dict, List, Tuple

# Banned Terminology Filter (rules.md, AGENTS.md, Task 24)
# System strictly prohibits clinical / psychiatric / diagnostic labeling of personnel.
from app.ml.terminology import BANNED_PHRASES

# Operational Attention Decision Thresholds (Approved Option 2: Balanced Operational Threshold)
DEFAULT_TAU_HIGH: float = 0.15
DEFAULT_TAU_MED: float = 0.075

# Canonical Operational Score Bands (LOW = 0–39, MEDIUM = 40–69, HIGH = 70–100)
SCORE_LOW_MAX: float = 39.9
SCORE_MEDIUM_MIN: float = 40.0
SCORE_MEDIUM_MAX: float = 69.9
SCORE_HIGH_MIN: float = 70.0
SCORE_HIGH_MAX: float = 100.0

CANONICAL_BANDS: Dict[str, Tuple[float, float]] = {
    "LOW": (0.0, 39.9),
    "MEDIUM": (40.0, 69.9),
    "HIGH": (70.0, 100.0),
}

# Operational Rest & Duty Reference Constants (Operational only, outside ML)
MIN_DAILY_REST_HOURS: float = 6.0
MIN_RECOVERY_GAP_HOURS: float = 8.0
ALERT_BUDGET_FRACTION: float = 0.10
SUSTAINED_ALERT_DAYS: int = 3
ALERT_COOLDOWN_DAYS: int = 14

# Historical legacy thresholds (preserved for governance test regression compatibility)
CLINICAL_FLOOR_SCORE: float = 70.0
PHQ9_CLINICAL_THRESHOLD: int = 15
PSS10_CLINICAL_THRESHOLD: int = 27
COMPOSITE_SELF_CHECK_THRESHOLD: float = 4.0
