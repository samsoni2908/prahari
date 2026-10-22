"""PRAHARI Model-C: Governed Evidence Convergence Engine.

Canonical Specification: docs/ml.md §§ 20–23, 25; rules.md; prd.md.

Truthful State Semantics:
1. Evidence Convergence, NOT a third predictive model.
2. NO numeric weighted averaging (NO 0.7 * A + 0.3 * B).
3. NO combined stress probability or psychiatric diagnosis.
4. Deterministic, transparent evaluation preserving domain boundaries.
5. Strict Privacy Firewall: Commander NEVER receives private convergence details or private source availability.
6. Whenever Source B is unavailable (INSTRUMENT_NOT_ACTIVATED, NOT_SHARED, INSUFFICIENT_HISTORY, etc.),
   Model-C emits OPERATIONAL_EVIDENCE_ONLY for BOTH elevated and non-elevated operational strain,
   separately exposing operational_attention (HIGH/MEDIUM/LOW).
7. NO_ELEVATED_EVIDENCE is emitted ONLY when BOTH sources are actually available/governed and both confirm non-elevated evidence.
8. CONVERGING_EVIDENCE is emitted ONLY when BOTH sources are actually available/governed and both confirm elevated evidence.
9. PRIVATE_EVIDENCE_ONLY is emitted ONLY when Source B is actually available/governed and elevated while Source A is routine/unavailable.
10. CONVERGENCE_UNAVAILABLE is emitted when neither source provides evaluable evidence.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional


# Canonical Model-C Convergence State Vocabulary (docs/ml.md §22)
STATE_CONVERGING_EVIDENCE = "CONVERGING_EVIDENCE"
STATE_OPERATIONAL_EVIDENCE_ONLY = "OPERATIONAL_EVIDENCE_ONLY"
STATE_PRIVATE_EVIDENCE_ONLY = "PRIVATE_EVIDENCE_ONLY"
STATE_NO_ELEVATED_EVIDENCE = "NO_ELEVATED_EVIDENCE"
STATE_CONVERGENCE_UNAVAILABLE = "CONVERGENCE_UNAVAILABLE"

# Source Availability Statuses
SOURCE_AVAILABLE = "AVAILABLE"
SOURCE_UNAVAILABLE = "UNAVAILABLE"
SOURCE_NOT_ACTIVATED = "INSTRUMENT_NOT_ACTIVATED"
SOURCE_NOT_SHARED = "NOT_SHARED"
SOURCE_INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
SOURCE_MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
SOURCE_PROCESSING_ERROR = "PROCESSING_ERROR"

# Framework Version Constants
CONVERGENCE_FRAMEWORK_VERSION = "v1.0-governed"
CONVERGENCE_RULES_VERSION = "v1.1-truthful-source"
MODEL_A_COMPAT_VERSION = "v2.1-frozen-prototype"
ENGINE_B_COMPAT_VERSION = "v1.0-governed"
PRIVACY_POLICY_VERSION = "v1.0-locked"


@dataclass(frozen=True)
class OperationalEvidenceSource:
    """Source A: Operational and service evidence derived from Model-A and WSI."""

    status: str  # AVAILABLE | MODEL_UNAVAILABLE | INSUFFICIENT_HISTORY
    is_elevated: bool = False
    operational_attention: Optional[str] = None  # LOW | MEDIUM | HIGH (or UNAVAILABLE / NOT_COMPUTED)
    risk_score: Optional[float] = None
    calibrated_prob: Optional[float] = None
    attention_band: Optional[str] = None  # LOW | MEDIUM | HIGH
    trend: Optional[str] = None  # STABLE | RISING | FALLING
    drivers: List[str] = field(default_factory=list)
    confidence: float = 0.0
    wsi_score: Optional[float] = None


@dataclass(frozen=True)
class PrivateWellbeingEvidenceSource:
    """Source B: Governed derived wellbeing evidence from Engine-B."""

    status: str  # AVAILABLE | INSTRUMENT_NOT_ACTIVATED | NOT_SHARED | INSUFFICIENT_HISTORY
    is_declining_or_elevated: bool = False
    attention_category: Optional[str] = None  # ROUTINE | ELEVATED_ATTENTION | UNAVAILABLE
    trend_direction: Optional[str] = None  # STABLE | IMPROVING | DECLINING | INSUFFICIENT_HISTORY
    confidence_score: float = 0.0
    is_governed: bool = True
    is_shared: bool = False


@dataclass
class EvidenceConvergenceResult:
    """Internal typed result of Model-C evidence convergence."""

    convergence_state: str
    operational_status: str
    private_status: str
    operational_attention: str  # LOW | MEDIUM | HIGH | UNAVAILABLE
    explanation: str
    evaluation_date: date
    framework_version: str = CONVERGENCE_FRAMEWORK_VERSION
    rules_version: str = CONVERGENCE_RULES_VERSION
    is_operational_elevated: bool = False
    is_private_elevated: bool = False
    operational_drivers: List[str] = field(default_factory=list)
    created_at_utc: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_personnel_projection(self) -> Dict[str, Any]:
        """Personnel self-projection: includes operational indicators and own private evidence status."""
        return {
            "convergence_state": self.convergence_state,
            "operational_attention": self.operational_attention,
            "explanation": self.explanation,
            "evaluation_date": self.evaluation_date.isoformat(),
            "framework_version": self.framework_version,
            "operational_evidence": {
                "status": self.operational_status,
                "is_elevated": self.is_operational_elevated,
                "operational_attention": self.operational_attention,
                "drivers": self.operational_drivers,
            },
            "private_wellbeing_evidence": {
                "status": self.private_status,
                "is_elevated": self.is_private_elevated,
            },
        }

    def to_welfare_projection(self, is_case_authorized: bool, is_shared: bool) -> Optional[Dict[str, Any]]:
        """
        Welfare projection: requires authorized case.

        When not shared (current default), strictly masks private evidence.
        """
        if not is_case_authorized:
            return None

        if not is_shared:
            return {
                "convergence_state": STATE_OPERATIONAL_EVIDENCE_ONLY,
                "operational_attention": self.operational_attention,
                "explanation": (
                    f"Only operational evidence is currently available (operational attention: {self.operational_attention}); "
                    "private wellbeing evidence is not shared for this case."
                ),
                "evaluation_date": self.evaluation_date.isoformat(),
                "framework_version": self.framework_version,
                "operational_evidence": {
                    "status": self.operational_status,
                    "is_elevated": self.is_operational_elevated,
                    "operational_attention": self.operational_attention,
                    "drivers": self.operational_drivers,
                },
                "private_wellbeing_evidence": {
                    "status": SOURCE_NOT_SHARED,
                    "is_elevated": None,
                },
            }

        return {
            "convergence_state": self.convergence_state,
            "operational_attention": self.operational_attention,
            "explanation": self.explanation,
            "evaluation_date": self.evaluation_date.isoformat(),
            "framework_version": self.framework_version,
            "operational_evidence": {
                "status": self.operational_status,
                "is_elevated": self.is_operational_elevated,
                "operational_attention": self.operational_attention,
                "drivers": self.operational_drivers,
            },
            "private_wellbeing_evidence": {
                "status": self.private_status,
                "is_elevated": self.is_private_elevated,
            },
        }

    def to_commander_projection(self) -> Dict[str, Any]:
        """
        Commander projection: STRICT PRIVACY FIREWALL.

        Commander NEVER receives private convergence state or private evidence status.
        Only returns operational indicators.
        """
        return {
            "operational_evidence": {
                "status": self.operational_status,
                "is_elevated": self.is_operational_elevated,
                "operational_attention": self.operational_attention,
                "drivers": self.operational_drivers,
            },
        }

    def to_admin_projection(self) -> Dict[str, Any]:
        """Admin projection: governance metadata only. No individual case dossiers."""
        return {
            "framework_version": self.framework_version,
            "rules_version": self.rules_version,
            "model_a_compatibility": MODEL_A_COMPAT_VERSION,
            "engine_b_compatibility": ENGINE_B_COMPAT_VERSION,
            "privacy_policy_version": PRIVACY_POLICY_VERSION,
            "status": "CONVERGENCE_FRAMEWORK_AVAILABLE",
        }


def evaluate_evidence_convergence(
    source_a: OperationalEvidenceSource,
    source_b: PrivateWellbeingEvidenceSource,
    evaluation_date: Optional[date] = None,
    rules_version: str = CONVERGENCE_RULES_VERSION,
) -> EvidenceConvergenceResult:
    """
    Deterministic Evidence Convergence Matrix evaluation.

    Truthful State Semantics:
    - Both A and B available/shared:
      - A elevated + B declining/elevated -> CONVERGING_EVIDENCE
      - A elevated + B stable -> OPERATIONAL_EVIDENCE_ONLY
      - A routine + B declining/elevated -> PRIVATE_EVIDENCE_ONLY
      - A routine + B stable -> NO_ELEVATED_EVIDENCE
    - A available + B unavailable/unshared/unactivated:
      - ALWAYS OPERATIONAL_EVIDENCE_ONLY (for BOTH A elevated and A routine)
      - separately exposes operational_attention (HIGH/MEDIUM/LOW)
      - NO_ELEVATED_EVIDENCE is NEVER emitted when B is unavailable
    - A unavailable + B available/shared:
      - B declining/elevated -> PRIVATE_EVIDENCE_ONLY
      - B stable -> NO_ELEVATED_EVIDENCE (or PRIVATE_EVIDENCE_ONLY)
    - Both A and B unavailable:
      - CONVERGENCE_UNAVAILABLE
    """
    eval_date = evaluation_date or date.today()
    a_avail = source_a.status == SOURCE_AVAILABLE
    b_avail = source_b.status == SOURCE_AVAILABLE and source_b.is_governed and source_b.is_shared

    op_att = (
        source_a.operational_attention
        or (source_a.attention_band if source_a.attention_band else None)
        or ("HIGH" if source_a.is_elevated else "LOW")
    )
    drivers_str = ", ".join(source_a.drivers) if source_a.drivers else "operational indicators"

    # Case 1: Both sources are evaluable and shared
    if a_avail and b_avail:
        if source_a.is_elevated and source_b.is_declining_or_elevated:
            state = STATE_CONVERGING_EVIDENCE
            explanation = (
                f"Converging evidence: independent operational strain ({op_att}) and private "
                "wellbeing signals both indicate elevated concern. Priority welfare review is recommended."
            )
        elif source_a.is_elevated and not source_b.is_declining_or_elevated:
            state = STATE_OPERATIONAL_EVIDENCE_ONLY
            explanation = (
                f"Operational strain exists ({op_att}: {drivers_str}); inspect workload and recovery context. "
                "Private wellbeing signal remains stable."
            )
        elif not source_a.is_elevated and source_b.is_declining_or_elevated:
            state = STATE_PRIVATE_EVIDENCE_ONLY
            explanation = (
                f"Private wellbeing concern indicated; operational strain is within routine thresholds ({op_att}). "
                "Welfare support path may be appropriate."
            )
        else:
            state = STATE_NO_ELEVATED_EVIDENCE
            explanation = (
                f"No current elevated evidence: both operational indicators ({op_att}) and "
                "private wellbeing signals are within routine thresholds."
            )

    # Case 2: Source A is available, but Source B is unavailable, unactivated, unshared, or insufficient
    elif a_avail and not b_avail:
        # TRUTHFUL STATE RULE: Must NOT emit NO_ELEVATED_EVIDENCE based only on Source A.
        # Emit OPERATIONAL_EVIDENCE_ONLY for BOTH elevated and routine operational strain.
        state = STATE_OPERATIONAL_EVIDENCE_ONLY
        b_label = "not shared" if source_b.status == SOURCE_NOT_SHARED else source_b.status.lower()
        if source_a.is_elevated:
            explanation = (
                f"Only operational evidence is currently available ({op_att}: {drivers_str}). "
                f"Private wellbeing evidence is {b_label} and is not penalized."
            )
        else:
            explanation = (
                f"Only operational evidence is currently available ({op_att} - not elevated). "
                f"Private wellbeing evidence is {b_label} and was not evaluated."
            )

    # Case 3: Source A is unavailable, but Source B is available and shared
    elif not a_avail and b_avail:
        if source_b.is_declining_or_elevated:
            state = STATE_PRIVATE_EVIDENCE_ONLY
            explanation = (
                "Private wellbeing concern indicated; operational model is unavailable. "
                "Welfare support path remains open without fabricating operational strain."
            )
        else:
            state = STATE_PRIVATE_EVIDENCE_ONLY
            explanation = (
                "Private wellbeing signal is stable; operational model is currently unavailable."
            )

    # Case 4: Neither source provides evaluable evidence
    else:
        state = STATE_CONVERGENCE_UNAVAILABLE
        explanation = "Insufficient evidence available from operational and private sources to compute convergence."

    return EvidenceConvergenceResult(
        convergence_state=state,
        operational_status=source_a.status,
        private_status=source_b.status,
        operational_attention=op_att,
        explanation=explanation,
        evaluation_date=eval_date,
        rules_version=rules_version,
        is_operational_elevated=source_a.is_elevated,
        is_private_elevated=source_b.is_declining_or_elevated,
        operational_drivers=source_a.drivers,
    )
