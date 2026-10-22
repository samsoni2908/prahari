"""
PRAHARI — Operational Peer Anomaly Engine (Model-A)
Canonical Reference: AGENTS.md §5, docs/ml.md §8.1

PURPOSE:
Detects multivariate operational anomalies within an operationally defensible
peer cohort (effective unit + operational role_title).

CONSTRAINTS:
1. Operational data ONLY. Strictly NO private wellbeing or clinical data.
2. Defensible Cohort: Effective unit + operational service role (NOT RBAC).
3. Truthful State Rule: Sparse peer cohorts must NEVER return fake score 0.0
   or fabricated is_anomaly=False. Returns INSUFFICIENT_PEER_DATA.
4. Default parameters: n_estimators = 100, contamination = 0.10, random_state = 26186.
"""

from dataclasses import dataclass
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Sequence, Union
import numpy as np
from sklearn.ensemble import IsolationForest

DEFAULT_N_ESTIMATORS: int = 100
DEFAULT_CONTAMINATION: float = 0.10
DEFAULT_RANDOM_STATE: int = 26186
DEFAULT_MIN_COHORT_SIZE: int = 5


class PeerAnomalyStatus(str, Enum):
    VALID = "VALID"
    INSUFFICIENT_PEER_DATA = "INSUFFICIENT_PEER_DATA"
    MISSING_FEATURE_DATA = "MISSING_FEATURE_DATA"
    COMPUTATION_ERROR = "COMPUTATION_ERROR"


@dataclass(frozen=True)
class PeerMemberResult:
    status: PeerAnomalyStatus
    score: Optional[float]           # Raw decision_function (negative = anomalous)
    anomaly_strength: Optional[float] # -score_samples (higher = more unusual)
    is_anomaly: Optional[bool]
    reason: Optional[str] = None

    @property
    def is_peer_anomaly(self) -> Optional[bool]:
        return self.is_anomaly

    @property
    def anomaly_score(self) -> Optional[float]:
        return self.score


def detect_peer_anomalies(
    feature_matrix: Sequence[Sequence[Any]],
    identifiers: Optional[Sequence[str]] = None,
    *,
    contamination: float = DEFAULT_CONTAMINATION,
    n_estimators: int = DEFAULT_N_ESTIMATORS,
    random_state: int = DEFAULT_RANDOM_STATE,
    min_cohort_size: int = DEFAULT_MIN_COHORT_SIZE,
    max_samples: Union[int, float, str] = "auto",
    max_features: Union[int, float] = 1.0,
    n_jobs: int = -1,
) -> Union[Dict[str, Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Applies Isolation Forest to detect multivariate operational peer anomalies.

    If identifiers is provided:
        Returns Dict[id, {status, score, anomaly_score, anomaly_strength, is_anomaly, is_peer_anomaly, reason}]
    If identifiers is None:
        Returns List[{status, score, anomaly_score, anomaly_strength, is_anomaly, is_peer_anomaly, reason}]

    TRUTHFUL BEHAVIOR:
    - If cohort size < min_cohort_size:
      Returns status="INSUFFICIENT_PEER_DATA", score=None, is_anomaly=None.
      NEVER returns fake score 0.0 or fake is_anomaly=False.
    - If any member has missing or non-finite features:
      That member returns status="MISSING_FEATURE_DATA", score=None, is_anomaly=None.
    """
    cohort_len = len(feature_matrix) if feature_matrix is not None else 0
    id_list = list(identifiers) if identifiers is not None else None

    # Handle sparse peer cohort (< min_cohort_size)
    if cohort_len < min_cohort_size:
        sparse_reason = (
            f"Insufficient peer cohort size: observed {cohort_len} members, "
            f"minimum required is {min_cohort_size}."
        )
        if id_list:
            return {
                pid: {
                    "status": PeerAnomalyStatus.INSUFFICIENT_PEER_DATA.value,
                    "score": None,
                    "anomaly_score": None,
                    "anomaly_strength": None,
                    "is_anomaly": None,
                    "is_peer_anomaly": None,
                    "reason": sparse_reason,
                }
                for pid in id_list
            }
        else:
            return [
                {
                    "status": PeerAnomalyStatus.INSUFFICIENT_PEER_DATA.value,
                    "score": None,
                    "anomaly_score": None,
                    "anomaly_strength": None,
                    "is_anomaly": None,
                    "is_peer_anomaly": None,
                    "reason": sparse_reason,
                }
                for _ in range(cohort_len)
            ]

    # Validate feature vectors
    valid_indices: List[int] = []
    invalid_indices: Dict[int, str] = {}
    clean_rows: List[List[float]] = []

    for i, row in enumerate(feature_matrix):
        if row is None:
            invalid_indices[i] = "Feature row is None."
            continue
        try:
            row_floats = []
            has_nan = False
            for val in row:
                if val is None:
                    has_nan = True
                    break
                fv = float(val)
                if math.isnan(fv) or math.isinf(fv):
                    has_nan = True
                    break
                row_floats.append(fv)

            if has_nan or len(row_floats) == 0:
                invalid_indices[i] = "Feature row contains missing, NaN, or non-finite values."
            else:
                clean_rows.append(row_floats)
                valid_indices.append(i)
        except (TypeError, ValueError) as err:
            invalid_indices[i] = f"Feature row has invalid non-numeric values: {err}"

    # Check if remaining valid members satisfy minimum cohort size
    if len(clean_rows) < min_cohort_size:
        sparse_after_clean_reason = (
            f"Insufficient valid peer cohort size after data quality filtering: "
            f"found {len(clean_rows)} valid members, minimum required is {min_cohort_size}."
        )
        all_results: List[Dict[str, Any]] = []
        for i in range(cohort_len):
            if i in invalid_indices:
                all_results.append({
                    "status": PeerAnomalyStatus.MISSING_FEATURE_DATA.value,
                    "score": None,
                    "anomaly_score": None,
                    "anomaly_strength": None,
                    "is_anomaly": None,
                    "is_peer_anomaly": None,
                    "reason": invalid_indices[i],
                })
            else:
                all_results.append({
                    "status": PeerAnomalyStatus.INSUFFICIENT_PEER_DATA.value,
                    "score": None,
                    "anomaly_score": None,
                    "anomaly_strength": None,
                    "is_anomaly": None,
                    "is_peer_anomaly": None,
                    "reason": sparse_after_clean_reason,
                })
        if id_list:
            return {id_list[i]: all_results[i] for i in range(cohort_len)}
        return all_results

    # Fit Isolation Forest on clean cohort
    X = np.array(clean_rows, dtype=float)
    iso = IsolationForest(
        n_estimators=n_estimators,
        contamination=contamination,
        random_state=random_state,
        n_jobs=n_jobs,
        max_samples=max_samples,
        max_features=max_features,
    )
    preds = iso.fit_predict(X)            # -1 = anomaly, 1 = normal
    dec_scores = iso.decision_function(X) # lower = more abnormal
    sample_scores = iso.score_samples(X)

    # Build results matching input ordering
    results_map: Dict[int, Dict[str, Any]] = {}
    for valid_idx, pred, score, sample_score in zip(valid_indices, preds, dec_scores, sample_scores):
        is_anom = bool(pred == -1)
        sc = round(float(score), 4)
        strength = round(float(-sample_score), 4)
        results_map[valid_idx] = {
            "status": PeerAnomalyStatus.VALID.value,
            "score": sc,
            "anomaly_score": sc,
            "anomaly_strength": strength,
            "is_anomaly": is_anom,
            "is_peer_anomaly": is_anom,
            "reason": None,
        }

    for inv_idx, reason_text in invalid_indices.items():
        results_map[inv_idx] = {
            "status": PeerAnomalyStatus.MISSING_FEATURE_DATA.value,
            "score": None,
            "anomaly_score": None,
            "anomaly_strength": None,
            "is_anomaly": None,
            "is_peer_anomaly": None,
            "reason": reason_text,
        }

    ordered_results = [results_map[i] for i in range(cohort_len)]

    if id_list:
        return {id_list[i]: ordered_results[i] for i in range(cohort_len)}
    return ordered_results
