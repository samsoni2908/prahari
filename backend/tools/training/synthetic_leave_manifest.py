"""Versioned Synthetic Leave Lifecycle Generation Manifest and Cohort Generator.

IMPORTANT DISCLAIMER:
These parameters are VERSIONED SYNTHETIC PROTOTYPE-GENERATION PARAMETERS ONLY.
They do NOT represent real-world Armed Forces / CAPF prevalence, empirical statistical
ground truth, or canonical leave administration policy.
They exist exclusively to drive deterministic, reproducible synthetic leave lifecycle
fixtures for prototype development and model validation with explicitly verifiable ground truth.
"""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import hashlib
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union
import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SyntheticLeaveGenerationManifest:
    """Explicit, versioned configuration for uncoupled baseline synthetic leave lifecycle generation."""

    manifest_version: str = "v1.0-synthetic-prototype"
    documentation_status: str = "SYNTHETIC_PROTOTYPE_ONLY_NOT_POLICY"

    # Planning classification synthetic distribution (prototype assumption only)
    planned_share: float = 0.85
    unplanned_share: float = 0.15

    # Prior approval lead time distributions (prototype assumption only)
    planned_approval_lead_days_range: Tuple[int, int] = (3, 14)
    unplanned_approval_lead_hours_range: Tuple[int, int] = (0, 24)

    # Disruption probability among approved leaves (prototype assumption only)
    service_disruption_probability: float = 0.04
    personnel_disruption_probability: float = 0.06

    # Distribution of disruption types when disruption occurs
    service_disruption_distribution: Tuple[Tuple[str, float], ...] = (
        ("CANCELLED", 0.40),
        ("DEFERRED", 0.30),
        ("RECALLED", 0.15),
        ("SHORTENED", 0.15),
    )
    personnel_disruption_distribution: Tuple[Tuple[str, float], ...] = (
        ("CANCELLED", 0.70),
        ("DEFERRED", 0.30),
    )

    # Deterministic generation seed
    default_seed: int = 26186

    def to_dict(self) -> Dict[str, object]:
        return {
            "manifest_version": self.manifest_version,
            "documentation_status": self.documentation_status,
            "planned_share": self.planned_share,
            "unplanned_share": self.unplanned_share,
            "planned_approval_lead_days_range": list(self.planned_approval_lead_days_range),
            "unplanned_approval_lead_hours_range": list(self.unplanned_approval_lead_hours_range),
            "service_disruption_probability": self.service_disruption_probability,
            "personnel_disruption_probability": self.personnel_disruption_probability,
            "service_disruption_distribution": dict(self.service_disruption_distribution),
            "personnel_disruption_distribution": dict(self.personnel_disruption_distribution),
            "default_seed": self.default_seed,
        }


@dataclass(frozen=True)
class SyntheticOperationalCouplingManifest:
    """Explicit, versioned configuration for operational stochastic synthetic leave coupling (Task 19A).

    VERSIONED SYNTHETIC PROTOTYPE-GENERATION PARAMETERS ONLY.
    They do NOT represent real-world Armed Forces / CAPF prevalence, empirical statistical
    ground truth, or canonical leave administration policy.
    They govern a stochastic hazard coupling prior operational strain (t <= T) to future
    leave lifecycle anomalies in (T, T + 30d], avoiding direct label leakage or deterministic thresholds.
    """

    manifest_version: str = "v2.1-frozen-prototype"
    documentation_status: str = "SYNTHETIC_PROTOTYPE_ONLY_NOT_POLICY"
    provenance: str = (
        "PROVENANCE: Design parameters were selected during initial development and are now permanently "
        "FROZEN before evaluation on the independent validation realization (seed 27186). Reference centering "
        "and scaling constants are estimated strictly from the DEVELOPMENT TRAINING PARTITION (t <= 2026-05-04, "
        "N=7200 rows), eliminating pre-split data leakage."
    )
    development_seed: int = 26186
    validation_seed: int = 27186
    default_seed: int = 26186

    # Baseline hazard intercept (weekly base event rate ~ 0.018 -> logit ~ -3.998)
    base_event_rate: float = 0.018

    # Modest positive operational coupling coefficients (linear hazard score beta_k)
    beta_duty_hours_30d: float = 0.45          # Elevated recent duty load
    beta_rest_deficit_14d: float = 0.38        # Reduced rest / recovery deficit
    beta_consecutive_duty_days: float = 0.32   # Consecutive duty burden
    beta_night_duty_ratio_30d: float = 0.35    # Night duty concentration
    beta_deployment_days_30d: float = 0.28     # Deployment intensity
    beta_staffing_pressure_7d: float = 0.25    # Staffing pressure (low staffing ratio)
    beta_baseline_z_workload: float = 0.32     # Deviation from personal baseline
    beta_peer_deviation_workload: float = 0.30 # Peer deviation
    beta_workload_change_14v14: float = 0.22   # Recent workload surge

    # Reference centering and scaling estimated STRICTLY from DEVELOPMENT TRAINING PARTITION (t <= 2026-05-04)
    duty_hours_center: float = 153.23
    duty_hours_scale: float = 54.00
    min_rest_center: float = 3.39
    min_rest_scale: float = 3.36
    consecutive_days_center: float = 1.75
    consecutive_days_scale: float = 2.45
    night_duty_ratio_center: float = 0.269
    night_duty_ratio_scale: float = 0.162
    deployment_days_center: float = 1.53
    deployment_days_scale: float = 4.67
    staffing_ratio_center: float = 0.790
    staffing_ratio_scale: float = 0.249
    peer_deviation_scale: float = 1.27
    workload_change_clip: float = 100.0
    workload_change_scale: float = 50.0

    # Person-level unobserved heterogeneity std (eta_i ~ N(0, sigma^2))
    person_heterogeneity_std: float = 0.35

    # Stochastic observation noise std (eps_{i,T} ~ N(0, sigma^2))
    observation_noise_std: float = 0.35

    # Realization distribution of anomaly events (Condition A vs Condition B)
    unplanned_share: float = 0.70           # Condition A: Unplanned actual start in horizon
    service_disruption_share: float = 0.30  # Condition B: Service disruption of approved leave

    # Background routine planned leave rate (completed without disruption, or personnel-cancelled)
    routine_leaves_annual_rate: float = 2.5
    personnel_cancellation_share: float = 0.05  # Personnel disruption -> confirmed negative

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_version": self.manifest_version,
            "documentation_status": self.documentation_status,
            "provenance": self.provenance,
            "development_seed": self.development_seed,
            "validation_seed": self.validation_seed,
            "default_seed": self.default_seed,
            "base_event_rate": self.base_event_rate,
            "coupling_coefficients": {
                "beta_duty_hours_30d": self.beta_duty_hours_30d,
                "beta_rest_deficit_14d": self.beta_rest_deficit_14d,
                "beta_consecutive_duty_days": self.beta_consecutive_duty_days,
                "beta_night_duty_ratio_30d": self.beta_night_duty_ratio_30d,
                "beta_deployment_days_30d": self.beta_deployment_days_30d,
                "beta_staffing_pressure_7d": self.beta_staffing_pressure_7d,
                "beta_baseline_z_workload": self.beta_baseline_z_workload,
                "beta_peer_deviation_workload": self.beta_peer_deviation_workload,
                "beta_workload_change_14v14": self.beta_workload_change_14v14,
            },
            "training_only_constants": {
                "duty_hours_center": self.duty_hours_center,
                "duty_hours_scale": self.duty_hours_scale,
                "min_rest_center": self.min_rest_center,
                "min_rest_scale": self.min_rest_scale,
                "consecutive_days_center": self.consecutive_days_center,
                "consecutive_days_scale": self.consecutive_days_scale,
                "night_duty_ratio_center": self.night_duty_ratio_center,
                "night_duty_ratio_scale": self.night_duty_ratio_scale,
                "deployment_days_center": self.deployment_days_center,
                "deployment_days_scale": self.deployment_days_scale,
                "staffing_ratio_center": self.staffing_ratio_center,
                "staffing_ratio_scale": self.staffing_ratio_scale,
                "peer_deviation_scale": self.peer_deviation_scale,
            },
            "noise_mechanism": {
                "person_heterogeneity_std": self.person_heterogeneity_std,
                "observation_noise_std": self.observation_noise_std,
            },
            "realization_shares": {
                "unplanned_share": self.unplanned_share,
                "service_disruption_share": self.service_disruption_share,
                "personnel_cancellation_share": self.personnel_cancellation_share,
            },
        }


SYNTHETIC_LEAVE_MANIFEST_V1 = SyntheticLeaveGenerationManifest()
SYNTHETIC_COUPLING_MANIFEST_V2_1 = SyntheticOperationalCouplingManifest()
SYNTHETIC_COUPLING_MANIFEST_V2 = SYNTHETIC_COUPLING_MANIFEST_V2_1


def generate_coupled_synthetic_leave_cohort(
    operational_df: pd.DataFrame,
    start_date: date,
    end_date: date,
    manifest: SyntheticOperationalCouplingManifest = SYNTHETIC_COUPLING_MANIFEST_V2,
    seed: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Deterministically generates coupled synthetic leave records conditioned on prior operational strain.

    Features available at or before T (t <= T) drive a stochastic latent hazard of future leave lifecycle
    anomalies in (T, T + 30d]. Strict temporal causality is preserved: no future data is used at T.
    """
    base_seed = seed if seed is not None else manifest.default_seed
    span_days = max(1, (end_date - start_date).days)
    base_logit = np.log(manifest.base_event_rate / (1.0 - manifest.base_event_rate))

    pids = sorted(operational_df["pseudo_id"].unique())
    rng_master = np.random.RandomState(base_seed)
    person_effects = {pid: rng_master.normal(0, manifest.person_heterogeneity_std) for pid in pids}

    # Reference fallback medians for missing operational values
    medians = {
        "duty_hours_30d": manifest.duty_hours_center,
        "min_rest_hours_14d": manifest.min_rest_center,
        "consecutive_duty_days": manifest.consecutive_days_center,
        "night_duty_ratio_30d": manifest.night_duty_ratio_center,
        "deployment_days_30d": manifest.deployment_days_center,
        "staffing_ratio_7d": manifest.staffing_ratio_center,
        "baseline_z_workload": 0.0,
        "peer_deviation_workload": 0.0,
        "workload_change_14v14": 0.0,
    }

    all_records: List[Dict[str, Any]] = []

    for pid in pids:
        pid_hash = int(hashlib.md5(str(pid).encode()).hexdigest()[:8], 16)
        rng_p = np.random.RandomState((base_seed + pid_hash) % (2**31 - 1))
        eta_i = person_effects[pid]

        p_df = operational_df[operational_df["pseudo_id"] == pid].sort_values("prediction_date")
        person_leaves: List[Dict[str, Any]] = []

        # 1. Background routine planned leaves
        expected_routine = max(1, int(np.round(manifest.routine_leaves_annual_rate * (span_days / 365.25))))
        num_routine = max(1, min(5, rng_p.poisson(expected_routine)))
        routine_offsets = sorted(rng_p.randint(10, max(11, span_days - 30), size=num_routine))

        for roff in routine_offsets:
            r_start = start_date + timedelta(days=int(roff))
            r_dur = int(rng_p.choice([7, 10, 14, 21]))
            r_end = r_start + timedelta(days=r_dur)
            lead = int(rng_p.randint(5, 15))
            app_at = datetime.combine(
                r_start - timedelta(days=lead),
                datetime.min.time(),
                tzinfo=timezone.utc,
            ) + timedelta(hours=9)

            if rng_p.rand() < manifest.personnel_cancellation_share:
                # Personnel-initiated cancellation (evaluated as confirmed NEGATIVE)
                d_off = rng_p.randint(0, lead)
                person_leaves.append({
                    "personnel_id": pid,
                    "pseudo_id": str(pid),
                    "leave_type": "ANNUAL",
                    "start_date": r_start,
                    "end_date": r_end,
                    "days": float(r_dur),
                    "status": "CANCELLED",
                    "planning_classification": "PLANNED",
                    "approved_at": app_at,
                    "actual_start_date": None,
                    "actual_end_date": None,
                    "disruption_type": "CANCELLED",
                    "disruption_initiator": "PERSONNEL",
                    "disrupted_at": app_at + timedelta(days=int(d_off)),
                })
            else:
                # Routine planned completion (evaluated as confirmed NEGATIVE)
                person_leaves.append({
                    "personnel_id": pid,
                    "pseudo_id": str(pid),
                    "leave_type": "ANNUAL",
                    "start_date": r_start,
                    "end_date": r_end,
                    "days": float(r_dur),
                    "status": "COMPLETED",
                    "planning_classification": "PLANNED",
                    "approved_at": app_at,
                    "actual_start_date": r_start,
                    "actual_end_date": r_end,
                    "disruption_type": None,
                    "disruption_initiator": None,
                    "disrupted_at": None,
                })

        # 2. Coupled stochastic operational anomalies driven by prior strain at T
        last_anomaly_date = date(2020, 1, 1)

        for _, row in p_df.iterrows():
            cutoff = (
                date.fromisoformat(str(row["prediction_date"]))
                if isinstance(row["prediction_date"], str)
                else row["prediction_date"]
            )

            # Extract features strictly available at T (t <= T) with fallback
            dh = row["duty_hours_30d"] if pd.notna(row.get("duty_hours_30d")) else medians["duty_hours_30d"]
            mr = row["min_rest_hours_14d"] if pd.notna(row.get("min_rest_hours_14d")) else medians["min_rest_hours_14d"]
            cd = row["consecutive_duty_days"] if pd.notna(row.get("consecutive_duty_days")) else medians["consecutive_duty_days"]
            nd = row["night_duty_ratio_30d"] if pd.notna(row.get("night_duty_ratio_30d")) else medians["night_duty_ratio_30d"]
            dp = row["deployment_days_30d"] if pd.notna(row.get("deployment_days_30d")) else medians["deployment_days_30d"]
            st = row["staffing_ratio_7d"] if pd.notna(row.get("staffing_ratio_7d")) else medians["staffing_ratio_7d"]
            bz = row["baseline_z_workload"] if pd.notna(row.get("baseline_z_workload")) else medians["baseline_z_workload"]
            pd_val = row["peer_deviation_workload"] if pd.notna(row.get("peer_deviation_workload")) else medians["peer_deviation_workload"]
            wc = row["workload_change_14v14"] if pd.notna(row.get("workload_change_14v14")) else medians["workload_change_14v14"]

            # Standardized directional factors (higher = greater strain / fatigue)
            x_duty = (dh - manifest.duty_hours_center) / manifest.duty_hours_scale
            x_rest = (manifest.min_rest_center - mr) / manifest.min_rest_scale
            x_consec = (cd - manifest.consecutive_days_center) / manifest.consecutive_days_scale
            x_night = (nd - manifest.night_duty_ratio_center) / manifest.night_duty_ratio_scale
            x_deploy = (dp - manifest.deployment_days_center) / manifest.deployment_days_scale
            x_staff = (manifest.staffing_ratio_center - st) / manifest.staffing_ratio_scale
            x_base = bz
            x_peer = pd_val / manifest.peer_deviation_scale
            x_chg = np.clip(wc, -manifest.workload_change_clip, manifest.workload_change_clip) / manifest.workload_change_scale

            eps = rng_p.normal(0, manifest.observation_noise_std)

            z = (
                base_logit
                + manifest.beta_duty_hours_30d * x_duty
                + manifest.beta_rest_deficit_14d * x_rest
                + manifest.beta_consecutive_duty_days * x_consec
                + manifest.beta_night_duty_ratio_30d * x_night
                + manifest.beta_deployment_days_30d * x_deploy
                + manifest.beta_staffing_pressure_7d * x_staff
                + manifest.beta_baseline_z_workload * x_base
                + manifest.beta_peer_deviation_workload * x_peer
                + manifest.beta_workload_change_14v14 * x_chg
                + eta_i
                + eps
            )

            p_hazard = 1.0 / (1.0 + np.exp(-z))

            # Stochastic Bernoulli realization
            if rng_p.rand() < p_hazard:
                event_offset = int(rng_p.randint(3, 27))
                event_d = cutoff + timedelta(days=event_offset)

                # Refractory constraint: at least 14 days between distinct leave events
                if event_d <= end_date and (event_d - last_anomaly_date).days >= 14:
                    last_anomaly_date = event_d

                    if rng_p.rand() < manifest.unplanned_share:
                        # Path A: Unplanned leave outbreak
                        dur = int(rng_p.choice([5, 7, 10]))
                        end_act = event_d + timedelta(days=dur)
                        app_h = int(rng_p.randint(4, 24))
                        app_dt = datetime.combine(
                            event_d,
                            datetime.min.time(),
                            tzinfo=timezone.utc,
                        ) - timedelta(hours=app_h)
                        person_leaves.append({
                            "personnel_id": pid,
                            "pseudo_id": str(pid),
                            "leave_type": "CASUAL",
                            "start_date": event_d,
                            "end_date": end_act,
                            "days": float(dur),
                            "status": "COMPLETED",
                            "planning_classification": "UNPLANNED",
                            "approved_at": app_dt,
                            "actual_start_date": event_d,
                            "actual_end_date": end_act,
                            "disruption_type": None,
                            "disruption_initiator": None,
                            "disrupted_at": None,
                        })
                    else:
                        # Path B: Service disruption of approved leave
                        dur = int(rng_p.choice([10, 14, 21]))
                        plan_start = event_d + timedelta(days=int(rng_p.randint(5, 12)))
                        plan_end = plan_start + timedelta(days=dur)
                        app_days = int(rng_p.randint(14, 28))
                        app_dt = datetime.combine(
                            plan_start - timedelta(days=app_days),
                            datetime.min.time(),
                            tzinfo=timezone.utc,
                        ) + timedelta(hours=9)
                        dis_dt = datetime.combine(
                            event_d,
                            datetime.min.time(),
                            tzinfo=timezone.utc,
                        ) + timedelta(hours=int(rng_p.randint(8, 16)))
                        dis_type = str(rng_p.choice(["CANCELLED", "DEFERRED", "RECALLED", "SHORTENED"]))

                        person_leaves.append({
                            "personnel_id": pid,
                            "pseudo_id": str(pid),
                            "leave_type": "PRIVILEGE",
                            "start_date": plan_start,
                            "end_date": plan_end,
                            "days": float(dur),
                            "status": dis_type,
                            "planning_classification": "PLANNED",
                            "approved_at": app_dt,
                            "actual_start_date": None if dis_type in ("CANCELLED", "DEFERRED") else plan_start,
                            "actual_end_date": None if dis_type in ("CANCELLED", "DEFERRED") else plan_start + timedelta(days=dur // 2),
                            "disruption_type": dis_type,
                            "disruption_initiator": "SERVICE",
                            "disrupted_at": dis_dt,
                        })

        all_records.extend(person_leaves)

    all_records.sort(key=lambda r: (str(r["personnel_id"]), r["start_date"]))
    return all_records


def generate_synthetic_leave_cohort(
    personnel_ids: Sequence[Any],
    start_date: date,
    end_date: date,
    manifest: Union[SyntheticLeaveGenerationManifest, SyntheticOperationalCouplingManifest] = SYNTHETIC_LEAVE_MANIFEST_V1,
    seed: Optional[int] = None,
    operational_df: Optional[pd.DataFrame] = None,
) -> List[Dict[str, Any]]:
    """Generates synthetic leave lifecycle records.

    If operational_df is provided, uses the versioned coupled generator (Task 19A).
    If operational_df is None, uses uncoupled baseline generator (backward compatible with Task 12 tests).
    """
    if operational_df is not None:
        coupling_manifest = (
            manifest
            if isinstance(manifest, SyntheticOperationalCouplingManifest)
            else SYNTHETIC_COUPLING_MANIFEST_V2
        )
        return generate_coupled_synthetic_leave_cohort(
            operational_df=operational_df,
            start_date=start_date,
            end_date=end_date,
            manifest=coupling_manifest,
            seed=seed,
        )

    base_seed = seed if seed is not None else manifest.default_seed
    days_span = max(1, (end_date - start_date).days)
    records: List[Dict[str, Any]] = []

    legacy_manifest = (
        manifest
        if isinstance(manifest, SyntheticLeaveGenerationManifest)
        else SYNTHETIC_LEAVE_MANIFEST_V1
    )

    svc_types, svc_probs = zip(*legacy_manifest.service_disruption_distribution)
    per_types, per_probs = zip(*legacy_manifest.personnel_disruption_distribution)

    for idx, pid in enumerate(personnel_ids):
        pid_hash = int(hashlib.md5(str(pid).encode()).hexdigest()[:8], 16)
        rng = np.random.RandomState((base_seed + pid_hash) % (2**31 - 1))

        expected_leaves = max(1, int(np.round(3.0 * (days_span / 365.25))))
        num_leaves = rng.poisson(lam=expected_leaves)
        num_leaves = max(1, min(num_leaves, 8))

        intervals = sorted(rng.randint(0, max(1, days_span - 20), size=num_leaves))

        for offset in intervals:
            event_start = start_date + timedelta(days=int(offset))
            duration = int(rng.choice([5, 7, 10, 14, 21]))
            event_end = event_start + timedelta(days=duration)
            days = float(duration)

            is_planned = rng.rand() < legacy_manifest.planned_share
            planning_class = "PLANNED" if is_planned else "UNPLANNED"
            leave_type = rng.choice(["ANNUAL", "CASUAL", "PRIVILEGE", "SPECIAL_LEAVE"])

            if is_planned:
                lead_min, lead_max = legacy_manifest.planned_approval_lead_days_range
                lead_days = int(rng.randint(lead_min, lead_max + 1))
                approved_at = datetime.combine(
                    event_start - timedelta(days=lead_days),
                    datetime.min.time(),
                    tzinfo=timezone.utc,
                ) + timedelta(hours=9)

                r_disrupt = rng.rand()
                if r_disrupt < legacy_manifest.service_disruption_probability:
                    disruption_type = str(rng.choice(svc_types, p=svc_probs))
                    disruption_initiator = "SERVICE"
                    if disruption_type in ("CANCELLED", "DEFERRED"):
                        disrupt_offset = rng.randint(0, lead_days)
                        disrupted_at = approved_at + timedelta(days=int(disrupt_offset))
                        actual_start_date = None
                        actual_end_date = None
                        status = disruption_type
                    elif disruption_type == "RECALLED":
                        actual_start_date = event_start
                        actual_duration = max(1, duration // 2)
                        actual_end_date = event_start + timedelta(days=actual_duration)
                        disrupted_at = datetime.combine(actual_end_date, datetime.min.time(), tzinfo=timezone.utc)
                        status = "RECALLED"
                    else:  # SHORTENED
                        actual_start_date = event_start
                        actual_duration = max(1, duration - 3)
                        actual_end_date = event_start + timedelta(days=actual_duration)
                        disrupted_at = datetime.combine(event_start, datetime.min.time(), tzinfo=timezone.utc)
                        status = "SHORTENED"
                elif r_disrupt < (legacy_manifest.service_disruption_probability + legacy_manifest.personnel_disruption_probability):
                    disruption_type = str(rng.choice(per_types, p=per_probs))
                    disruption_initiator = "PERSONNEL"
                    disrupt_offset = rng.randint(0, lead_days)
                    disrupted_at = approved_at + timedelta(days=int(disrupt_offset))
                    actual_start_date = None
                    actual_end_date = None
                    status = disruption_type
                else:
                    disruption_type = None
                    disruption_initiator = None
                    disrupted_at = None
                    actual_start_date = event_start
                    actual_end_date = event_end
                    status = "COMPLETED"
            else:
                lead_hours = int(rng.randint(
                    legacy_manifest.unplanned_approval_lead_hours_range[0],
                    legacy_manifest.unplanned_approval_lead_hours_range[1] + 1,
                ))
                approved_at = datetime.combine(
                    event_start,
                    datetime.min.time(),
                    tzinfo=timezone.utc,
                ) - timedelta(hours=lead_hours)
                disruption_type = None
                disruption_initiator = None
                disrupted_at = None
                actual_start_date = event_start
                actual_end_date = event_end
                status = "COMPLETED"

            records.append({
                "personnel_id": pid,
                "pseudo_id": str(pid),
                "leave_type": leave_type,
                "start_date": event_start,
                "end_date": event_end,
                "days": days,
                "status": status,
                "planning_classification": planning_class,
                "approved_at": approved_at,
                "actual_start_date": actual_start_date,
                "actual_end_date": actual_end_date,
                "disruption_type": disruption_type,
                "disruption_initiator": disruption_initiator,
                "disrupted_at": disrupted_at,
            })

    records.sort(key=lambda r: (str(r["personnel_id"]), r["start_date"]))
    return records


__all__ = [
    "SyntheticLeaveGenerationManifest",
    "SyntheticOperationalCouplingManifest",
    "SYNTHETIC_LEAVE_MANIFEST_V1",
    "SYNTHETIC_COUPLING_MANIFEST_V2",
    "SYNTHETIC_COUPLING_MANIFEST_V2_1",
    "generate_coupled_synthetic_leave_cohort",
    "generate_synthetic_leave_cohort",
]
