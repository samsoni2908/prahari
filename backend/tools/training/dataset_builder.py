"""
PRAHARI â€” Model-A Training Dataset Builder (Task 13)
Canonical Reference: AGENTS.md Â§8, rules.md, docs/ml.md Â§6.1

This module builds the supervised training dataset for Model-A:
- Prediction timestamp: T
- Horizon: (T, T + 30 days]
- Features: Strictly the 15 locked Model-A operational features (features_hr.py)
- Target: Canonical 3-state leave anomaly target (targets.py)
- Ineligibles (TARGET_UNAVAILABLE): Strictly excluded from supervised training/evaluation.
- Zero raw wellbeing, zero private wellbeing, zero Model-C.
- Rigorous leakage scanning and temporal validation.
"""

from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from app.ml.features_hr import MODEL_A_FEATURE_NAMES, extract_hr_features
from tools.training.synthetic_leave_manifest import (
    SYNTHETIC_COUPLING_MANIFEST_V2,
    SYNTHETIC_COUPLING_MANIFEST_V2_1,
    SYNTHETIC_LEAVE_MANIFEST_V1,
    SyntheticOperationalCouplingManifest,
    generate_synthetic_leave_cohort,
)
from app.ml.targets import (
    HORIZON_DAYS,
    TARGET_VERSION,
    LeaveTargetState,
    generate_leave_anomaly_target,
    target_to_binary,
)

CANONICAL_COLUMNS: List[str] = [
    "pseudo_id",
    "prediction_date",
    "future_window_start",
    "future_window_end",
    "target_leave_anomaly",
    "target_state",
    "target_version",
    "data_completeness",
] + MODEL_A_FEATURE_NAMES


def build_model_a_dataset(
    source_ml_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
    observation_end_date: date = date(2026, 8, 31),
    random_seed: int = 26186,
    manifest: Optional[SyntheticOperationalCouplingManifest] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Builds and validates the Model-A supervised training dataset.

    Args:
        source_ml_path: Path to input feature dataset (default /data/seed26186/ml_training.csv).
        output_path: Path to save canonical assembled dataset.
        observation_end_date: End of observational history.
        random_seed: Deterministic seed for synthetic lifecycle generation.
        manifest: SyntheticOperationalCouplingManifest to govern lifecycle generation.

    Returns:
        Tuple of (clean_eligible_dataframe, audit_report_dict).
    """
    active_manifest = manifest if manifest is not None else SYNTHETIC_COUPLING_MANIFEST_V2_1

    if source_ml_path is None:
        candidates = [
            Path("/data/seed26186/ml_training.csv"),
            Path("data/seed26186/ml_training.csv"),
            Path(__file__).resolve().parent.parent.parent.parent / "data" / "seed26186" / "ml_training.csv",
        ]
        for c in candidates:
            if c.exists():
                source_ml_path = c
                break
        if source_ml_path is None:
            raise FileNotFoundError("Could not find source ml_training.csv")

    df_raw = pd.read_csv(source_ml_path)

    # 1. Quarantine & Exclude Banned Columns (Privacy & Anti-Leakage Contracts)
    banned_substrings = ["wellbeing", "phq", "gad", "who", "pss", "model_c", "leave_frequency", "leave_gap"]
    detected_banned = [c for c in df_raw.columns if any(b in c.lower() for b in banned_substrings)]
    df_clean = df_raw.drop(columns=detected_banned, errors="ignore").copy()

    # 2. Extract strictly the 15 locked features
    df_features = extract_hr_features(df_clean)

    # 3. Deterministic Synthetic Leave Lifecycle Generation according to Manifest (Task 19B Frozen)
    personnel_ids = sorted(df_raw["pseudo_id"].unique())
    synth_leaves = generate_synthetic_leave_cohort(
        personnel_ids=personnel_ids,
        start_date=date(2025, 8, 1),
        end_date=observation_end_date,
        manifest=active_manifest,
        seed=random_seed,
        operational_df=df_raw,
    )

    leaves_by_person: Dict[str, List[Dict[str, Any]]] = {}
    for r in synth_leaves:
        leaves_by_person.setdefault(str(r["personnel_id"]), []).append(r)

    # 4. Generate Canonical Target Labels
    targets_state: List[str] = []
    targets_binary: List[Optional[int]] = []
    window_starts: List[str] = []
    window_ends: List[str] = []

    for _, row in df_raw.iterrows():
        pid = str(row["pseudo_id"])
        cutoff = date.fromisoformat(str(row["prediction_date"]))
        person_leaves = leaves_by_person.get(pid, [])

        w_start = cutoff + timedelta(days=1)
        w_end = cutoff + timedelta(days=HORIZON_DAYS)
        window_starts.append(w_start.isoformat())
        window_ends.append(w_end.isoformat())

        state, ver = generate_leave_anomaly_target(
            leave_records=person_leaves,
            cutoff_date=cutoff,
            horizon_days=HORIZON_DAYS,
            active_service=True,
            max_data_date=observation_end_date,
        )
        targets_state.append(state.value)
        targets_binary.append(target_to_binary(state))

    # 5. Assemble Dataset
    df_assembled = pd.DataFrame()
    df_assembled["pseudo_id"] = df_raw["pseudo_id"]
    df_assembled["prediction_date"] = df_raw["prediction_date"]
    df_assembled["future_window_start"] = window_starts
    df_assembled["future_window_end"] = window_ends
    df_assembled["target_leave_anomaly"] = targets_binary
    df_assembled["target_state"] = targets_state
    df_assembled["target_version"] = TARGET_VERSION

    # Compute data completeness (% non-null across the 15 features)
    feature_completeness = (1.0 - df_features.isna().mean(axis=1)).round(4)
    df_assembled["data_completeness"] = feature_completeness

    for feat in MODEL_A_FEATURE_NAMES:
        df_assembled[feat] = df_features[feat]

    # 6. Filter Eligible Rows (Strictly Exclude TARGET_UNAVAILABLE from Supervised Dataset)
    df_eligible = df_assembled[df_assembled["target_leave_anomaly"].notna()].copy()
    df_eligible["target_leave_anomaly"] = df_eligible["target_leave_anomaly"].astype(int)

    # 7. Leakage Scanning & Statistical Validation
    correlations: Dict[str, float] = {}
    for feat in MODEL_A_FEATURE_NAMES:
        corr = df_eligible[feat].corr(df_eligible["target_leave_anomaly"])
        correlations[feat] = float(corr) if not np.isnan(corr) else 0.0

    max_corr_feat = max(correlations.items(), key=lambda x: abs(x[1]))
    if abs(max_corr_feat[1]) >= 0.85:
        raise ValueError(
            f"LEAKAGE ALERT: Feature '{max_corr_feat[0]}' has suspicious correlation {max_corr_feat[1]:.4f} with target."
        )

    # Missingness summary
    missingness = df_eligible[MODEL_A_FEATURE_NAMES].isna().sum().to_dict()

    pos_count = int((df_eligible["target_leave_anomaly"] == 1).sum())
    neg_count = int((df_eligible["target_leave_anomaly"] == 0).sum())
    pos_rate = float(pos_count / len(df_eligible)) if len(df_eligible) > 0 else 0.0

    report = {
        "TASK_13_STATUS": "PASS",
        "total_rows_evaluated": len(df_assembled),
        "eligible_rows": len(df_eligible),
        "excluded_unavailable_rows": int((df_assembled["target_leave_anomaly"].isna()).sum()),
        "persons": int(df_eligible["pseudo_id"].nunique()),
        "date_range": [str(df_eligible["prediction_date"].min()), str(df_eligible["prediction_date"].max())],
        "positive_count": pos_count,
        "negative_count": neg_count,
        "positive_rate": round(pos_rate, 4),
        "missingness_summary": missingness,
        "leakage_scan_result": {
            "max_feature_correlation": round(max_corr_feat[1], 4),
            "max_feature": max_corr_feat[0],
            "quarantined_banned_columns": detected_banned,
            "leakage_detected": False,
        },
        "target_version": TARGET_VERSION,
        "coupling_manifest_version": active_manifest.manifest_version,
        "coupling_manifest": active_manifest.to_dict(),
        "random_seed": random_seed,
    }

    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df_eligible.to_csv(output_path, index=False)

    return df_eligible, report


__all__ = ["CANONICAL_COLUMNS", "build_model_a_dataset"]
