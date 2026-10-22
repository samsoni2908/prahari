import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from app.repositories.unit_repository import UnitRepository
from app.repositories.personnel_repository import PersonnelRepository
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.operational_repository import OperationalRepository
from app.repositories.audit_repository import AuditRepository
from app.config import settings


class CommanderService:
    def __init__(
        self,
        unit_repo: UnitRepository,
        personnel_repo: PersonnelRepository,
        analytics_repo: AnalyticsRepository,
        operational_repo: OperationalRepository,
        audit_repo: AuditRepository,
    ):
        self.unit_repo = unit_repo
        self.personnel_repo = personnel_repo
        self.analytics_repo = analytics_repo
        self.operational_repo = operational_repo
        self.audit_repo = audit_repo

    async def get_unit_overview(self, unit_id: uuid.UUID) -> Dict[str, Any]:
        unit = await self.unit_repo.get_by_id(unit_id)
        if not unit:
            raise ValueError(f"Unit {unit_id} not found")

        # Staffing
        staffing = await self.unit_repo.get_latest_staffing(unit_id)
        coverage_pct = float(staffing.coverage_percent) if staffing and staffing.coverage_percent is not None else None
        available_str = staffing.available_strength if staffing else None
        required_str = staffing.required_strength if staffing else None

        # Latest WSI snapshots for all personnel in unit
        snapshots = await self.analytics_repo.get_latest_unit_wsi_snapshots(unit_id)
        total_personnel = len(snapshots)

        scores = [float(s.wsi_score) for s in snapshots]
        avg_wsi = round(sum(scores) / len(scores), 2) if scores else None

        # Locked 3 risk bands: LOW (0-39), MEDIUM (40-69), HIGH (70-100)
        low_count = sum(1 for s in scores if s < 40)
        medium_count = sum(1 for s in scores if 40 <= s < 70)
        high_count = sum(1 for s in scores if s >= 70)

        dist_buckets = [
            {"label": "LOW (0-39)", "count": low_count, "color": "#22C55E", "band": "LOW"},
            {"label": "MEDIUM (40-69)", "count": medium_count, "color": "#F59E0B", "band": "MEDIUM"},
            {"label": "HIGH (70-100)", "count": high_count, "color": "#EF4444", "band": "HIGH"},
        ]

        # Driver averages across unit
        d_avg = round(sum(float(s.d_component) for s in snapshots) / len(snapshots), 2) if snapshots else None
        r_avg = round(sum(float(s.r_component) for s in snapshots) / len(snapshots), 2) if snapshots else None
        c_avg = round(sum(float(s.c_component) for s in snapshots) / len(snapshots), 2) if snapshots else None
        n_avg = round(sum(float(s.n_component) for s in snapshots) / len(snapshots), 2) if snapshots else None
        l_avg = round(sum(float(s.l_component) for s in snapshots) / len(snapshots), 2) if snapshots else None
        h_avg = round(sum(float(s.h_component) for s in snapshots) / len(snapshots), 2) if snapshots else None
        s_avg = round(sum(float(s.s_component) for s in snapshots) / len(snapshots), 2) if snapshots else None

        drivers = [
            {"code": "D", "name": "Duty Workload", "value": d_avg, "weight": 0.25},
            {"code": "R", "name": "Rest / Recovery Deficit", "value": r_avg, "weight": 0.20},
            {"code": "C", "name": "Operational Continuity", "value": c_avg, "weight": 0.15},
            {"code": "N", "name": "Night Duty Load", "value": n_avg, "weight": 0.15},
            {"code": "L", "name": "Leave Deficit", "value": l_avg, "weight": 0.10},
            {"code": "H", "name": "Deployment Intensity", "value": h_avg, "weight": 0.10},
            {"code": "S", "name": "Staffing Pressure", "value": s_avg, "weight": 0.05},
        ]

        # Active Alerts
        alerts = await self.analytics_repo.get_active_alerts_by_unit(unit_id)
        alert_count = len(alerts)

        response = {
            "unit": {
                "id": str(unit.id),
                "unit_code": unit.unit_code,
                "unit_name": unit.unit_name,
                "unit_type": unit.unit_type,
                "location_label": unit.location_label,
                "sanctioned_strength": unit.sanctioned_strength,
            },
            "kpis": {
                "wsi_status": "VALID" if scores else "NOT_COMPUTED",
                "staffing_status": ("VALID" if staffing.record_date == datetime.now(timezone.utc).date()-timedelta(days=1)
                    else "DATA_STALE") if staffing else "NOT_COMPUTED",
                "staffing_as_of": staffing.record_date.isoformat() if staffing else None,
                "total_personnel": total_personnel,
                "available_strength": available_str,
                "required_strength": required_str,
                "coverage_percent": coverage_pct,
                "avg_wsi": avg_wsi,
                "low_risk_count": low_count,
                "medium_risk_count": medium_count,
                "high_risk_count": high_count,
                "alert_count": alert_count,
            },
            "distribution": dist_buckets,
            "drivers": drivers,
            "recent_alerts": [
                {
                    "id": str(a.id),
                    "alert_type": a.alert_type,
                    "severity": a.severity,
                    "message": a.message,
                    "created_at": a.created_at.isoformat(),
                }
                for a in alerts[:5]
            ],
        }
        # Protect small cells and complementary totals together. Individual
        # operational access is a separate capability from this aggregate view.
        eligible_people = len({snapshot.personnel_id for snapshot in snapshots})
        cells = (low_count, medium_count, high_count)
        suppress = eligible_people < settings.AGGREGATION_FLOOR or any(
            0 < count < settings.AGGREGATION_FLOOR for count in cells
        )
        response["aggregation_status"] = "NOT_COMPUTED" if not snapshots else "SUPPRESSED" if suppress else "VALID"
        if suppress:
            for key in ("total_personnel", "avg_wsi", "low_risk_count", "medium_risk_count", "high_risk_count"):
                response["kpis"][key] = None
            response["kpis"]["wsi_status"] = "SUPPRESSED" if snapshots else "NOT_COMPUTED"
            for bucket in response["distribution"]:
                bucket["count"] = None
            for driver in response["drivers"]:
                driver["value"] = None
        return response

    async def get_priority_list(self, unit_id: uuid.UUID, limit=100, offset=0, query=None, status_filter=None) -> List[Dict[str, Any]]:
        # Fetch personnel and their latest snapshots
        personnel_list = await self.personnel_repo.list_by_unit(unit_id)
        personnel_map = {p.id: p for p in personnel_list}

        snapshots = await self.analytics_repo.get_latest_unit_wsi_snapshots(unit_id)

        # Build priority records
        results = []
        for snap in snapshots:
            p = personnel_map.get(snap.personnel_id)
            if not p:
                continue

            wsi = float(snap.wsi_score)

            # Determine main driver from components
            components = [
                ("Duty Load", float(snap.d_component) * 0.25),
                ("Rest Deficit", float(snap.r_component) * 0.20),
                ("Op Continuity", float(snap.c_component) * 0.15),
                ("Night Shift", float(snap.n_component) * 0.15),
                ("Leave Gap", float(snap.l_component) * 0.10),
                ("Deployment Intensity", float(snap.h_component) * 0.10),
                ("Staff Pressure", float(snap.s_component) * 0.05),
            ]
            main_driver_name, _ = max(components, key=lambda x: x[1])

            # Status classification
            if wsi >= 85:
                status = "Critical"
            elif wsi >= 70:
                status = "Elevated"
            elif wsi >= 50:
                status = "Moderate"
            else:
                status = "Normal"

            results.append({
                "personnel_id": str(p.id),
                "pseudo_id": p.pseudo_id,
                "rank_or_grade": p.rank_or_grade,
                "role_title": p.role_title,
                "wsi": wsi,
                "wsi_status": "VALID",
                "status": status,
                "trend": "NOT_COMPUTED",
                "trend_reason": "A score threshold cannot establish a time-series trend",
                "main_driver": main_driver_name,
                "components": {
                    "D": float(snap.d_component),
                    "R": float(snap.r_component),
                    "C": float(snap.c_component),
                    "N": float(snap.n_component),
                    "L": float(snap.l_component),
                    "H": float(snap.h_component),
                    "S": float(snap.s_component),
                },
            })

        represented = {record["personnel_id"] for record in results}
        for person in personnel_list:
            if str(person.id) not in represented:
                results.append({"personnel_id": str(person.id), "pseudo_id": person.pseudo_id,
                    "rank_or_grade": person.rank_or_grade, "role_title": person.role_title,
                    "wsi": None, "wsi_status": "NOT_COMPUTED", "status": "NOT_COMPUTED",
                    "trend": "NOT_COMPUTED", "main_driver": None, "components": None})
        if query:
            needle = query.casefold()
            results = [record for record in results if any(needle in str(record[key]).casefold()
                for key in ("pseudo_id", "rank_or_grade", "role_title"))]
        if status_filter:
            results = [record for record in results if record["status"] == status_filter]
        results.sort(key=lambda record: (record["wsi"] is None, -(record["wsi"] or 0), record["pseudo_id"]))
        return results[offset:offset+limit]

    async def get_strain_card(self, personnel_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        person = await self.personnel_repo.get_by_id(personnel_id)
        if not person:
            return None

        # WSI latest & history
        wsi_history = await self.analytics_repo.get_wsi_history(personnel_id, limit=30)
        latest_wsi = await self.analytics_repo.get_latest_wsi(personnel_id)
        current_analytics = await self.analytics_repo.get_current_operational(personnel_id)

        # Personal Baseline (Median/MAD, EWMA)
        baseline = await self.analytics_repo.get_latest_baseline(personnel_id)

        # Peer Anomaly
        anomaly = await self.analytics_repo.get_latest_anomaly(personnel_id)

        # Operational Prediction (Model A)
        # Per BACKEND-PRED-01 / canonical contracts:
        # Read only governed Model-A rows; later unavailable attempts suppress stale results.
        # Retained legacy probabilities never substitute for an approved inference.
        prediction = await self.analytics_repo.get_latest_prediction(
            personnel_id, target_name="target_leave_anomaly"
        )

        # Recent Operational Duties & Rest
        duties = await self.operational_repo.get_recent_duties(personnel_id, limit=14)
        rest_records = await self.operational_repo.get_recent_rest_records(personnel_id, limit=14)

        total_duty_hours = sum(float(d.hours) for d in duties if d.hours)
        night_shift_count = sum(1 for d in duties if d.is_night)
        avg_rest_hours = (
            round(sum(float(r.rest_hours) for r in rest_records if r.rest_hours) / len(rest_records), 1)
            if rest_records
            else None
        )

        # Build response strictly omitting any private wellbeing answers
        return {
            "personnel_id": str(person.id),
            "pseudo_id": person.pseudo_id,
            "rank_or_grade": person.rank_or_grade,
            "role_title": person.role_title,
            "unit_id": str(person.unit_id),
            "operational_analytics": current_analytics,
            "wsi": {
                "status": "VALID" if latest_wsi else "NOT_COMPUTED",
                "score": float(latest_wsi.wsi_score) if latest_wsi else None,
                "date": latest_wsi.snapshot_date.isoformat() if latest_wsi else None,
                "d_component": float(latest_wsi.d_component) if latest_wsi else None,
                "r_component": float(latest_wsi.r_component) if latest_wsi else None,
                "c_component": float(latest_wsi.c_component) if latest_wsi else None,
                "n_component": float(latest_wsi.n_component) if latest_wsi else None,
                "l_component": float(latest_wsi.l_component) if latest_wsi else None,
                "h_component": float(latest_wsi.h_component) if latest_wsi else None,
                "s_component": float(latest_wsi.s_component) if latest_wsi else None,
            },
            "history": [
                {
                    "date": snap.snapshot_date.isoformat(),
                    "wsi": float(snap.wsi_score),
                    "d": float(snap.d_component),
                    "r": float(snap.r_component),
                    "n": float(snap.n_component),
                    "governance_status": "SOURCE_UNVERIFIED_HISTORICAL_SNAPSHOT",
                }
                for snap in reversed(wsi_history)
            ],
            "baseline": {
                "median": current_analytics["baseline"].get("median"),
                "mad": current_analytics["baseline"].get("mad"),
                "z_score": current_analytics["baseline"].get("z_score"),
                "ewma": current_analytics["trend"].get("current_ewma"),
                "status": current_analytics["baseline"]["status"],
            },
            "peer_anomaly": {
                "status": current_analytics["peer"]["status"],
                "is_anomaly": current_analytics["peer"].get("is_anomaly"),
                "anomaly_score": current_analytics["peer"].get("anomaly_strength"),
                "algorithm": "IsolationForest" if current_analytics["peer"]["status"] == "VALID" else None,
            },
            "prediction": {
                "status": "VALID" if prediction else "MODEL_UNAVAILABLE",
                "risk_probability": float(prediction.hr_probability) if prediction else None,
                "predicted_class": prediction.predicted_class if prediction else None,
                "target": "Leave-pattern anomaly in next 30 days",
                "model_name": prediction.model_name if prediction else None,
                "explanation": prediction.explanation_json.get("drivers", []) if prediction else None,
                "as_of": prediction.prediction_date.isoformat() if prediction else None,
                "freshness": "CURRENT_AT_CUTOFF" if prediction and prediction.prediction_date == datetime.now(timezone.utc).date() else "HISTORICAL_AT_CUTOFF" if prediction else "UNAVAILABLE",
            },
            "operational_context": {
                "total_duty_hours_14d": round(total_duty_hours, 1),
                "night_shifts_14d": night_shift_count,
                "avg_rest_hours_14d": avg_rest_hours,
            },
        }

    async def get_unit_deployments(self, unit_id: uuid.UUID) -> Dict[str, Any]:
        """Aggregate deployment metrics for unit."""
        personnel = await self.personnel_repo.list_by_unit(unit_id)
        p_ids = [p.id for p in personnel]
        return {
            "unit_id": str(unit_id),
            "status": "NOT_COMPUTED",
            "total_personnel": len(personnel),
            "currently_deployed_count": None,
            "high_hardship_deployments": None,
            "average_deployment_duration_days": None,
        }

    async def get_unit_leave(self, unit_id: uuid.UUID) -> Dict[str, Any]:
        """Aggregate leave metrics for unit."""
        personnel = await self.personnel_repo.list_by_unit(unit_id)
        return {
            "unit_id": str(unit_id),
            "status": "NOT_COMPUTED",
            "total_personnel": len(personnel),
            "personnel_on_leave": None,
            "leave_utilization_rate": None,
            "accumulated_leave_deficit_days": None,
        }

    async def get_unit_workload(self, unit_id: uuid.UUID) -> Dict[str, Any]:
        """Aggregate workload metrics for unit."""
        personnel = await self.personnel_repo.list_by_unit(unit_id)
        return {
            "unit_id": str(unit_id),
            "status": "NOT_COMPUTED",
            "average_weekly_duty_hours": None,
            "night_duty_share_percent": None,
            "consecutive_duty_warning_count": None,
            "rest_compliance_rate": None,
        }

    async def get_unit_risk_trends(self, unit_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Return privacy-safe daily mean WSI points for the last 90 days."""
        cutoff = datetime.now(timezone.utc).date()
        snapshots = await self.analytics_repo.get_unit_wsi_history(
            unit_id, cutoff - timedelta(days=89)
        )
        by_date: Dict[Any, List[Any]] = {}
        for snapshot in snapshots:
            by_date.setdefault(snapshot.snapshot_date, []).append(snapshot)

        points: List[Dict[str, Any]] = []
        for snapshot_date, daily in sorted(by_date.items()):
            # A mean from a small daily cohort could identify individuals. Omit it
            # rather than exposing a value or fabricating a reassuring zero.
            eligible_people = len({snapshot.personnel_id for snapshot in daily})
            if eligible_people < settings.AGGREGATION_FLOOR:
                continue
            points.append({
                "date": snapshot_date.isoformat(),
                "mean_wsi": round(
                    sum(float(snapshot.wsi_score) for snapshot in daily) / len(daily), 2
                ),
                "eligible_personnel": eligible_people,
                "status": "VALID",
            })
        return points
