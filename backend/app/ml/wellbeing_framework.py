"""PRAHARI — Engine-B Generic Wellbeing Instrument Contract & Framework.

Canonical Reference: AGENTS.md §9, rules.md §2, docs/ml.md §15-18.

Contract Principles:
1. INSTRUMENT-GENERIC:
   - Does NOT assume or hardcode any specific clinical questionnaire (PHQ, PSS, GAD, etc.).
   - Governed by explicit adapter registration.
   - If no approved instrument is activated, returns explicit status:
     INSTRUMENT_NOT_ACTIVATED.
2. ABSOLUTE PRIVACY:
   - Raw responses are stored strictly in private storage (`wellbeing_private`).
   - Derived processing produces only high-level summary metrics (`wellbeing_results`).
   - Raw answers are NEVER returned in derived result objects.
3. NON-CLINICAL TERMINOLOGY:
   - Neutral operational attention terminology only.
   - Strictly NO psychiatric or mental-health diagnostic categorization.
4. TRUTHFUL STATE:
   - Incomplete or invalid submissions return explicit failure/unavailable states.
   - Never fabricate healthy or reassuring scores when data is missing.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union


# Canonical Engine-B Machine-Readable States
STATUS_AVAILABLE = "ENGINE_B_AVAILABLE"
STATUS_NOT_ACTIVATED = "INSTRUMENT_NOT_ACTIVATED"
STATUS_INCOMPLETE = "INCOMPLETE"
STATUS_INVALID = "INVALID_RESPONSE"
STATUS_NOT_COMPUTED = "NOT_COMPUTED"
STATUS_INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
STATUS_NOT_SHARED = "NOT_SHARED"

# Neutral Non-Clinical Attention Bands / Categories
ATTENTION_ROUTINE = "ROUTINE"
ATTENTION_ELEVATED = "ELEVATED_ATTENTION"
ATTENTION_UNAVAILABLE = "UNAVAILABLE"

# Neutral Temporal Trend Directions
TREND_STABLE = "STABLE"
TREND_IMPROVING = "IMPROVING"
TREND_DECLINING = "DECLINING"
TREND_INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
TREND_INSUFFICIENT_GOVERNED_HISTORY = "INSUFFICIENT_GOVERNED_HISTORY"

# Governance Classifications
GOVERNANCE_LEGACY = "LEGACY_UNGOVERNED"
GOVERNANCE_GOVERNED = "GOVERNED"


@dataclass(frozen=True)
class InstrumentItemSpec:
    """Specification of an individual questionnaire item."""

    item_id: str
    item_label: str  # Neutral description
    value_type: str  # 'int', 'float', 'bool', 'choice'
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_choices: Optional[List[str]] = None
    is_required: bool = True


@dataclass
class RawResponseValidationResult:
    """Result of validating raw questionnaire answers against instrument spec."""

    is_valid: bool
    errors: List[str] = field(default_factory=list)
    missing_items: List[str] = field(default_factory=list)
    unknown_items: List[str] = field(default_factory=list)
    completeness_ratio: float = 0.0


@dataclass
class DerivedWellbeingResult:
    """
    Non-raw derived wellbeing summary for safe persistence and authorized projection.

    Strictly contains NO raw item answers.
    """

    instrument_id: str
    instrument_version: str
    scoring_version: str
    assessment_date: date
    status: str  # e.g. INSTRUMENT_NOT_ACTIVATED, ENGINE_B_AVAILABLE
    summary_scores: Dict[str, Any] = field(default_factory=dict)
    attention_category: Optional[str] = None
    trend_direction: Optional[str] = None
    confidence_score: float = 0.0
    notes: Optional[str] = None
    processing_version: str = "v1.0-governed"
    is_governed: bool = True
    created_at_utc: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Converts to dictionary for JSON serialization into wellbeing_results."""
        return {
            "instrument_id": self.instrument_id,
            "instrument_version": self.instrument_version,
            "scoring_version": self.scoring_version,
            "assessment_date": self.assessment_date.isoformat() if isinstance(self.assessment_date, date) else str(self.assessment_date),
            "status": self.status,
            "summary_scores": self.summary_scores,
            "attention_category": self.attention_category,
            "trend_direction": self.trend_direction,
            "confidence_score": round(self.confidence_score, 4),
            "notes": self.notes,
            "processing_version": self.processing_version,
            "is_governed": self.is_governed,
            "created_at_utc": self.created_at_utc,
        }


def validate_raw_responses_against_spec(
    item_specs: List[InstrumentItemSpec],
    answers: Dict[str, Any],
    allow_unknown_items: bool = False,
) -> RawResponseValidationResult:
    """
    Strictly validates raw response dictionary against item specifications.

    Rules:
    - Required items missing -> recorded in missing_items, is_valid = False
    - Unknown item keys -> recorded in unknown_items, is_valid = False (if allow_unknown_items is False)
    - Value type checking (int, float, bool, choice)
    - Value range bounds ([min_value, max_value])
    - Discrete choice validation (allowed_choices)
    - Non-numeric / NaN / inf rejected
    - Zero silent correction.
    """
    spec_dict = {s.item_id: s for s in item_specs}
    errors: List[str] = []
    missing_items: List[str] = []
    unknown_items: List[str] = []

    # 1. Check for unknown items
    for key in answers.keys():
        if key not in spec_dict:
            unknown_items.append(key)
            if not allow_unknown_items:
                errors.append(f"Unknown item key '{key}' not defined in instrument specification")

    # 2. Check for missing required items
    for item_id, spec in spec_dict.items():
        if spec.is_required and (item_id not in answers or answers[item_id] is None):
            missing_items.append(item_id)
            errors.append(f"Required item '{item_id}' ({spec.item_label}) is missing")

    # 3. Check values against specs
    for key, val in answers.items():
        if key not in spec_dict or val is None:
            continue
        spec = spec_dict[key]

        # Type and bounds check
        if spec.value_type in ("int", "float"):
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                errors.append(f"Item '{key}' must be numeric ({spec.value_type}), got {type(val).__name__}")
                continue
            if isinstance(val, float) and (val != val or val in (float("inf"), float("-inf"))):
                errors.append(f"Item '{key}' contains non-finite numeric value")
                continue
            if spec.value_type == "int" and isinstance(val, float) and not val.is_integer():
                errors.append(f"Item '{key}' must be an integer, got float {val}")
                continue

            if spec.min_value is not None and val < spec.min_value:
                errors.append(f"Item '{key}' value {val} is below minimum allowed {spec.min_value}")
            if spec.max_value is not None and val > spec.max_value:
                errors.append(f"Item '{key}' value {val} exceeds maximum allowed {spec.max_value}")

        elif spec.value_type == "bool":
            if not isinstance(val, bool):
                errors.append(f"Item '{key}' must be boolean, got {type(val).__name__}")

        elif spec.value_type == "choice":
            if spec.allowed_choices and str(val) not in spec.allowed_choices:
                errors.append(f"Item '{key}' value '{val}' not in allowed choices: {spec.allowed_choices}")

    total_required = sum(1 for s in item_specs if s.is_required)
    completed_required = total_required - len(missing_items)
    completeness_ratio = (completed_required / total_required) if total_required > 0 else 1.0

    is_valid = len(errors) == 0

    return RawResponseValidationResult(
        is_valid=is_valid,
        errors=errors,
        missing_items=missing_items,
        unknown_items=unknown_items,
        completeness_ratio=round(completeness_ratio, 4),
    )


class BaseInstrumentAdapter(ABC):
    """Abstract base class for wellbeing instrument validation and scoring adapters."""

    @property
    @abstractmethod
    def instrument_id(self) -> str:
        """Unique canonical identifier of the instrument."""
        pass

    @property
    @abstractmethod
    def instrument_version(self) -> str:
        """Specification version string."""
        pass

    @property
    @abstractmethod
    def scoring_version(self) -> str:
        """Version of the deterministic scoring contract."""
        pass

    @property
    @abstractmethod
    def is_activated(self) -> bool:
        """Whether this instrument has received canonical approval to activate."""
        pass

    @abstractmethod
    def get_item_specs(self) -> List[InstrumentItemSpec]:
        """Returns the list of item definitions for this instrument."""
        pass

    def validate_responses(self, answers: Dict[str, Any]) -> RawResponseValidationResult:
        """Default validation against get_item_specs(). Subclasses may customize."""
        if not self.is_activated:
            return RawResponseValidationResult(
                is_valid=False,
                errors=[f"Instrument '{self.instrument_id}' is not canonically activated"],
                completeness_ratio=0.0,
            )
        return validate_raw_responses_against_spec(self.get_item_specs(), answers)

    @abstractmethod
    def derive_result(
        self,
        answers: Dict[str, Any],
        assessment_date: date,
        prior_results: Optional[List[DerivedWellbeingResult]] = None,
    ) -> DerivedWellbeingResult:
        """Computes derived non-raw summary from validated answers."""
        pass


class GenericUnactivatedAdapter(BaseInstrumentAdapter):
    """
    Default generic fallback adapter for unactivated / unfinalized instruments.

    Used when an instrument is referenced but has not received canonical approval.
    """

    def __init__(self, instrument_id: str = "GENERIC_UNACTIVATED", instrument_version: str = "0.0"):
        self._instrument_id = instrument_id
        self._instrument_version = instrument_version

    @property
    def instrument_id(self) -> str:
        return self._instrument_id

    @property
    def instrument_version(self) -> str:
        return self._instrument_version

    @property
    def scoring_version(self) -> str:
        return "none"

    @property
    def is_activated(self) -> bool:
        return False

    def get_item_specs(self) -> List[InstrumentItemSpec]:
        return []

    def validate_responses(self, answers: Dict[str, Any]) -> RawResponseValidationResult:
        return RawResponseValidationResult(
            is_valid=False,
            errors=[f"Instrument '{self._instrument_id}' is not canonically activated"],
            completeness_ratio=0.0,
        )

    def derive_result(
        self,
        answers: Dict[str, Any],
        assessment_date: date,
        prior_results: Optional[List[DerivedWellbeingResult]] = None,
    ) -> DerivedWellbeingResult:
        return DerivedWellbeingResult(
            instrument_id=self._instrument_id,
            instrument_version=self._instrument_version,
            scoring_version="none",
            assessment_date=assessment_date,
            status=STATUS_NOT_ACTIVATED,
            summary_scores={},
            attention_category=ATTENTION_UNAVAILABLE,
            trend_direction=TREND_INSUFFICIENT_HISTORY,
            confidence_score=0.0,
            notes="Instrument has not received canonical activation approval.",
        )


class InstrumentRegistry:
    """Registry managing available wellbeing instrument adapters."""

    def __init__(self):
        self._adapters: Dict[str, BaseInstrumentAdapter] = {}

    def register(self, adapter: BaseInstrumentAdapter) -> None:
        """Registers an instrument adapter keyed by instrument_id."""
        key = f"{adapter.instrument_id.upper()}@{adapter.instrument_version}"
        self._adapters[key] = adapter
        # Also map base name to latest registered version
        self._adapters[adapter.instrument_id.upper()] = adapter

    def get(self, instrument_id: str, version: Optional[str] = None) -> BaseInstrumentAdapter:
        """
        Retrieves adapter for given instrument_id and optional version.

        If not registered or not activated, returns a GenericUnactivatedAdapter.
        """
        inst_key = instrument_id.upper()
        if version:
            ver_key = f"{inst_key}@{version}"
            if ver_key in self._adapters:
                return self._adapters[ver_key]

        if inst_key in self._adapters:
            return self._adapters[inst_key]

        return GenericUnactivatedAdapter(instrument_id=instrument_id, instrument_version=version or "0.0")

    def is_activated(self, instrument_id: str, version: Optional[str] = None) -> bool:
        """Checks if the instrument is registered and activated."""
        adapter = self.get(instrument_id, version)
        return adapter.is_activated

    def list_registered(self) -> List[Dict[str, Any]]:
        """Returns metadata for all registered instrument adapters."""
        seen = set()
        out = []
        for key, adapter in self._adapters.items():
            composite = f"{adapter.instrument_id}@{adapter.instrument_version}"
            if composite not in seen:
                seen.add(composite)
                out.append({
                    "instrument_id": adapter.instrument_id,
                    "instrument_version": adapter.instrument_version,
                    "scoring_version": adapter.scoring_version,
                    "is_activated": adapter.is_activated,
                })
        return out


# Global singleton registry
GLOBAL_INSTRUMENT_REGISTRY = InstrumentRegistry()


def compute_private_wellbeing_trend(
    history: List[DerivedWellbeingResult],
    primary_metric_key: Optional[str] = None,
    min_required_assessments: int = 2,
    tolerance: float = 2.0,
    higher_is_better: bool = True,
) -> Tuple[str, Dict[str, Any]]:
    """
    Computes private wellbeing trend strictly from non-raw derived results.

    Contract Rules:
    1. Valid Assessments Only:
       - Only records with status == STATUS_AVAILABLE are evaluated.
       - Invalid, incomplete, or unactivated records are ignored.
    2. Minimum Assessment Gate:
       - Requires >= min_required_assessments (default 2) valid assessments.
       - If fewer: returns (TREND_INSUFFICIENT_HISTORY, {"reason": "INSUFFICIENT_HISTORY"}).
    3. Incomparable Instrument Boundary:
       - If instruments or scoring versions change across history,
         trend evaluates only the contiguous recent sequence matching the
         latest assessment's instrument_id and scoring_version.
       - Incomparable instruments are NEVER merged without an approved normalization policy.
       - If matching homogeneous assessments < min_required_assessments:
         returns (TREND_INSUFFICIENT_HISTORY, {"reason": "INSTRUMENT_CHANGE_BOUNDARY"}).
    4. Deterministic Direction Calculation:
       - delta = latest_score - previous_score
       - delta > tolerance -> IMPROVING (if higher_is_better) or DECLINING (if lower_is_better)
       - delta < -tolerance -> DECLINING (if higher_is_better) or IMPROVING (if lower_is_better)
       - |delta| <= tolerance -> STABLE
    """
    if not history:
        return TREND_INSUFFICIENT_HISTORY, {
            "status": TREND_INSUFFICIENT_HISTORY,
            "reason": "NO_ASSESSMENTS",
            "valid_count": 0,
            "delta": None,
        }

    # 1. Filter to valid, governed completed assessments sorted chronologically (oldest to newest)
    valid_history = [
        r for r in history
        if getattr(r, "is_governed", True) is True
        and getattr(r, "processing_version", "v1.0-governed") == "v1.0-governed"
        and r.status == STATUS_AVAILABLE
        and r.summary_scores
    ]
    # Sort by assessment_date
    valid_history.sort(key=lambda r: (r.assessment_date, r.created_at_utc))

    if len(valid_history) < min_required_assessments:
        # Check if unactivated or ungoverned records were provided
        if any(r.status == STATUS_NOT_ACTIVATED for r in history):
            return STATUS_NOT_ACTIVATED, {
                "status": STATUS_NOT_ACTIVATED,
                "reason": "INSTRUMENT_NOT_ACTIVATED",
                "valid_count": len(valid_history),
                "delta": None,
            }
        if len(history) >= min_required_assessments and not valid_history:
            return TREND_INSUFFICIENT_GOVERNED_HISTORY, {
                "status": TREND_INSUFFICIENT_GOVERNED_HISTORY,
                "reason": "LEGACY_UNGOVERNED_HISTORY: Historical retained records cannot generate governed trends",
                "valid_count": 0,
                "delta": None,
            }
        return TREND_INSUFFICIENT_HISTORY, {
            "status": TREND_INSUFFICIENT_HISTORY,
            "reason": f"INSUFFICIENT_ASSESSMENTS (got {len(valid_history)}, requires {min_required_assessments})",
            "valid_count": len(valid_history),
            "delta": None,
        }

    # 2. Check Instrument Homogeneity from the tail
    latest = valid_history[-1]
    matching_tail = [
        r for r in valid_history
        if r.instrument_id == latest.instrument_id and r.scoring_version == latest.scoring_version
    ]

    if len(matching_tail) < min_required_assessments:
        return TREND_INSUFFICIENT_HISTORY, {
            "status": TREND_INSUFFICIENT_HISTORY,
            "reason": "INSTRUMENT_BOUNDARY_INCOMPARABLE: Different instruments or scoring versions cannot be merged",
            "valid_count": len(matching_tail),
            "delta": None,
        }

    # 3. Determine numeric metric to track
    if primary_metric_key:
        metric_key = primary_metric_key
    else:
        # Default to first numeric key in summary_scores
        numeric_keys = [k for k, v in latest.summary_scores.items() if isinstance(v, (int, float))]
        if not numeric_keys:
            return TREND_INSUFFICIENT_HISTORY, {
                "status": TREND_INSUFFICIENT_HISTORY,
                "reason": "NO_NUMERIC_SCORES",
                "valid_count": len(matching_tail),
                "delta": None,
            }
        metric_key = numeric_keys[0]

    curr_val = latest.summary_scores.get(metric_key)
    prev_val = matching_tail[-2].summary_scores.get(metric_key)

    if curr_val is None or prev_val is None or not isinstance(curr_val, (int, float)) or not isinstance(prev_val, (int, float)):
        return TREND_INSUFFICIENT_HISTORY, {
            "status": TREND_INSUFFICIENT_HISTORY,
            "reason": "METRIC_VALUE_UNAVAILABLE",
            "valid_count": len(matching_tail),
            "delta": None,
        }

    delta = float(curr_val - prev_val)

    # 4. Map delta to neutral direction
    if abs(delta) <= tolerance:
        direction = TREND_STABLE
    elif delta > tolerance:
        direction = TREND_IMPROVING if higher_is_better else TREND_DECLINING
    else:
        direction = TREND_DECLINING if higher_is_better else TREND_IMPROVING

    return direction, {
        "status": direction,
        "delta": round(delta, 2),
        "metric_tracked": metric_key,
        "current_score": round(float(curr_val), 2),
        "previous_score": round(float(prev_val), 2),
        "valid_count": len(matching_tail),
        "instrument_id": latest.instrument_id,
        "scoring_version": latest.scoring_version,
    }
