import uuid
from datetime import date, datetime
from typing import List, Dict, Any, Optional
from app.repositories.wellbeing_repository import WellbeingRepository
from app.repositories.personnel_repository import PersonnelRepository
from app.repositories.unit_repository import UnitRepository
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.audit_repository import AuditRepository


from app.repositories.operational_repository import OperationalRepository
from app.models import SupportRequest


class WelfareService:
    def __init__(
        self,
        wellbeing_repo: WellbeingRepository,
        personnel_repo: PersonnelRepository,
        unit_repo: UnitRepository,
        analytics_repo: AnalyticsRepository,
        audit_repo: AuditRepository,
        operational_repo: Optional[OperationalRepository] = None,
    ):
        self.wellbeing_repo = wellbeing_repo
        self.personnel_repo = personnel_repo
        self.unit_repo = unit_repo
        self.analytics_repo = analytics_repo
        self.audit_repo = audit_repo
        self.operational_repo = operational_repo

    @staticmethod
    def _calculate_risk_band(score: float) -> str:
        if score is None:
            return "NOT_COMPUTED"
        if score < 40:
            return "LOW"
        elif score < 70:
            return "MEDIUM"
        else:
            return "HIGH"

    async def search_personnel(
        self,
        query: Optional[str] = None,
        risk_filter: Optional[str] = None,
        unit_id: Optional[uuid.UUID] = None,
    ) -> List[Dict[str, Any]]:
        personnel_list = await self.wellbeing_repo.search_operational_personnel(query=query, unit_id=unit_id)
        results = []
        for p in personnel_list:
            latest_wsi = await self.analytics_repo.get_latest_wsi(p.id)
            score = float(latest_wsi.wsi_score) if latest_wsi else None
            band = self._calculate_risk_band(score)

            if risk_filter and risk_filter.upper() != "ALL":
                if band != risk_filter.upper():
                    continue

            unit = await self.unit_repo.get_by_id(p.unit_id)

            results.append({
                "id": str(p.id),
                "pseudo_id": p.pseudo_id,
                "rank_or_grade": p.rank_or_grade,
                "role_title": p.role_title,
                "status": p.status,
                "unit_id": str(p.unit_id),
                "unit_name": unit.unit_name if unit else "Unknown Unit",
                "risk_score": round(score, 1) if score is not None else None,
                "risk_band": band,
            })
        return results

    async def get_personnel_profile(self, personnel_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        case = await self.wellbeing_repo.get_authorized_case_for_personnel(personnel_id)
        if not case:
            return None
        actor = self.wellbeing_repo.session.info["actor"]
        await self.audit_repo.log_event(uuid.UUID(actor["user_id"]), "WELFARE_OFFICER", "CASE_IDENTITY_ACCESS", "support_requests", case.id)
        person = await self.personnel_repo.get_by_id(personnel_id)
        if not person:
            return None

        unit = await self.unit_repo.get_by_id(person.unit_id)
        latest_wsi = await self.analytics_repo.get_latest_wsi(person_id := personnel_id)
        risk_score = float(latest_wsi.wsi_score) if latest_wsi else None
        risk_band = self._calculate_risk_band(risk_score)

        # Tab 1: Overview
        alerts = await self.analytics_repo.get_active_alerts_by_personnel(personnel_id)
        overview = {
            "id": str(person.id),
            "pseudo_id": person.pseudo_id,
            "personnel_code": person.personnel_code,
            "rank_or_grade": person.rank_or_grade,
            "role_title": person.role_title,
            "status": person.status,
            "service_years": float(person.service_years) if person.service_years else None,
            "joining_date": person.joining_date.isoformat() if person.joining_date else None,
            "unit": {
                "id": str(unit.id) if unit else None,
                "unit_name": unit.unit_name if unit else "N/A",
                "unit_code": unit.unit_code if unit else "N/A",
                "location_label": unit.location_label if unit else "N/A",
            },
            "risk_score": round(risk_score, 1) if risk_score is not None else None,
            "risk_band": risk_band,
            "active_alerts_count": len(alerts),
            "alerts": [
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

        # Tab 2: Service History (Postings)
        postings = await self.personnel_repo.get_posting_history(personnel_id)
        service_history = [
            {
                "id": str(post.id),
                "posting_type": post.posting_type,
                "location_label": post.location_label,
                "start_date": post.posting_start_date.isoformat(),
                "end_date": post.posting_end_date.isoformat() if post.posting_end_date else None,
            }
            for post in postings
        ]

        # Tab 3: Deployment
        deployments_data = []
        if self.operational_repo:
            deps = await self.operational_repo.get_active_deployments(personnel_id)
            deployments_data = [
                {
                    "id": str(d.id),
                    "deployment_type": d.deployment_type,
                    "location_label": d.location_label,
                    "start_date": d.start_date.isoformat(),
                    "end_date": d.end_date.isoformat() if d.end_date else None,
                    "intensity_level": d.intensity_level,
                }
                for d in deps
            ]

        # Tab 4: Leave & Rest
        leaves_data = []
        rest_data = []
        if self.operational_repo:
            leaves = await self.operational_repo.get_recent_leaves(personnel_id, limit=20)
            rests = await self.operational_repo.get_recent_rest_records(personnel_id, limit=20)
            leaves_data = [
                {
                    "id": str(l.id),
                    "leave_type": l.leave_type,
                    "start_date": l.start_date.isoformat(),
                    "end_date": l.end_date.isoformat(),
                    "status": l.status,
                    "days": (l.end_date - l.start_date).days + 1,
                }
                for l in leaves
            ]
            rest_data = [
                {
                    "id": str(r.id),
                    "record_date": r.record_date.isoformat(),
                    "rest_hours": float(r.rest_hours) if r.rest_hours is not None else None,
                    "rest_gap_hours": float(r.rest_gap_hours) if r.rest_gap_hours is not None else None,
                    "source": r.source,
                }
                for r in rests
            ]


        # Tab 5: Training
        trainings_data = []
        if self.operational_repo:
            trains = await self.operational_repo.get_training_records(personnel_id, limit=20)
            trainings_data = [
                {
                    "id": str(t.id),
                    "training_name": t.training_name,
                    "training_type": t.training_type,
                    "start_date": t.start_date.isoformat(),
                    "end_date": t.end_date.isoformat(),
                    "hours": float(t.hours) if t.hours else None,
                    "status": t.status,
                }
                for t in trains
            ]

        # Tab 6: Authorized Well-being summary (Preserving raw answer privacy)
        wellbeing_data = {"status": "NOT_SHARED"}

        # Tab 7: Risk Analysis & Contributing Factors
        baseline = await self.analytics_repo.get_latest_baseline(personnel_id)
        anomaly = await self.analytics_repo.get_latest_anomaly(personnel_id)
        # Operational Prediction (Model A)
        # Per BACKEND-PRED-01 / canonical contracts:
        # Retained legacy rows are historical only and do not qualify as approved current Model A.
        # Fake 0.18 fallback is removed; unavailable state is explicitly reported as MODEL_UNAVAILABLE.
        prediction = await self.analytics_repo.get_latest_prediction(
            personnel_id, target_name="target_leave_anomaly"
        )
        wsi_history = await self.analytics_repo.get_wsi_history(personnel_id, limit=14)

        factors = []
        if baseline and baseline.current_value and baseline.median_value and baseline.current_value > baseline.median_value * 1.2:
            factors.append({
                "factor": "Elevated Workload vs Baseline",
                "severity": "HIGH",
                "detail": f"Current EWMA: {round(float(baseline.ewma_value or baseline.current_value), 1)} (Median: {round(float(baseline.median_value), 1)})",
            })
        if anomaly:
            factors.append({
                "factor": f"Operational Anomaly ({anomaly.algorithm})",
                "severity": "MEDIUM",
                "detail": f"Detected on {anomaly.event_date.isoformat()} with anomaly score {round(float(anomaly.anomaly_score or 0), 2)}",
            })

        risk_analysis = {
            "current_wsi": round(risk_score, 1) if risk_score is not None else None,
            "risk_band": risk_band,
            "baseline": {
                "metric_name": baseline.metric_name if baseline else "WORKLOAD_EWMA",
                "baseline_mean": round(float(baseline.median_value), 2) if baseline and baseline.median_value else None,
                "current_value": round(float(baseline.current_value), 2) if baseline and baseline.current_value else None,
            } if baseline else None,
            "anomaly": {
                "algorithm": anomaly.algorithm,
                "score": float(anomaly.anomaly_score) if anomaly.anomaly_score is not None else None,
                "date": anomaly.event_date.isoformat(),
            } if anomaly else None,
            "prediction": {
                "status": "VALID" if prediction else "MODEL_UNAVAILABLE",
                "target_leave_anomaly_prob": float(prediction.hr_probability) if prediction else None,
                "model_version": prediction.model_version if prediction else None,
                "prediction_date": prediction.prediction_date.isoformat() if prediction else None,
            },
            "trend_history": [

                {
                    "date": snap.snapshot_date.isoformat(),
                    "score": round(float(snap.wsi_score), 1),
                    "band": self._calculate_risk_band(float(snap.wsi_score)),
                }
                for snap in reversed(wsi_history)
            ],
            "contributing_factors": factors,
        }

        # Model-C Evidence Convergence (governed; Welfare projection respects NOT_SHARED boundary)
        from app.ml.convergence import (
            OperationalEvidenceSource,
            PrivateWellbeingEvidenceSource,
            evaluate_evidence_convergence,
            SOURCE_AVAILABLE,
            SOURCE_NOT_SHARED,
        )
        is_op_elevated = (risk_band in ("MEDIUM", "HIGH")) if risk_band else (risk_score >= 40.0 if risk_score is not None else False)
        src_a = OperationalEvidenceSource(
            status=SOURCE_AVAILABLE if risk_score is not None else "MODEL_UNAVAILABLE",
            is_elevated=is_op_elevated,
            risk_score=risk_score,
            operational_attention=risk_band if risk_score is not None else "UNAVAILABLE",
            drivers=[f["factor"] for f in factors],
        )
        src_b = PrivateWellbeingEvidenceSource(
            status=SOURCE_NOT_SHARED,
            is_declining_or_elevated=False,
            is_governed=True,
            is_shared=False,
        )
        conv_res = evaluate_evidence_convergence(src_a, src_b)
        risk_analysis["evidence_convergence"] = conv_res.to_welfare_projection(is_case_authorized=True, is_shared=False)

        return {
            "overview": overview,
            "service_history": service_history,
            "deployment": deployments_data,
            "leave_and_rest": {
                "leaves": leaves_data,
                "rests": rest_data,
            },
            "training": trainings_data,
            "wellbeing": wellbeing_data,
            "risk_analysis": risk_analysis,
        }

    async def record_welfare_action(
        self,
        personnel_id: uuid.UUID,
        officer_user_id: uuid.UUID,
        action_type: str,
        details: str,
        notes: Optional[str] = None,
        follow_up_date: Optional[date] = None,
        outcome: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        from fastapi import HTTPException
        from app.services.welfare_case_service import WelfareCaseService
        actor = self.wellbeing_repo.session.info.get("actor") or {}
        if actor.get("role") != "WELFARE_OFFICER" or actor.get("user_id") != str(officer_user_id):
            raise HTTPException(403, "Officer authority required")
        case = await self.wellbeing_repo.get_authorized_case_for_personnel(personnel_id)
        if not case:
            raise HTTPException(404, "Case not found")
        mapped = {
            "MONITOR": "WORKLOAD_REVIEW", "CONTACT_PERSONNEL": "CONTACT_ATTEMPT",
            "WELFARE_FOLLOWUP": "FOLLOW_UP", "RECORD_OUTCOME": "CLOSE",
        }.get(action_type.upper().strip())
        if mapped is None:
            raise HTTPException(422, "Unsupported welfare action")
        if not idempotency_key:
            raise HTTPException(422, "Idempotency-Key required")
        key = idempotency_key
        service = WelfareCaseService(self.wellbeing_repo.session)
        if mapped == "CLOSE":
            if not outcome or len(outcome.strip()) < 5:
                raise HTTPException(422, "Personnel-visible closure outcome required")
            confidential = "\n".join(part.strip() for part in (details, notes) if part and part.strip())
            if confidential:
                await service.action(case.id, "DISCUSSION", confidential, "OFFICER", None,
                                     None, key + "-private")
            return await service.action(case.id, "CLOSE", outcome, "PERSONNEL", None, None, key)
        confidential = "\n".join(part.strip() for part in (details, notes) if part and part.strip())
        return await service.action(case.id, mapped, confidential, "OFFICER", follow_up_date,
                                    "IN_PROGRESS" if case.status == "ASSIGNED" else None, key)

    async def list_cases(self, status_filter: Optional[str] = None, limit=100, offset=0, query=None, assigned_to_me=False) -> List[Dict[str, Any]]:
        return await self.wellbeing_repo.list_queue(status_filter, limit, offset, query, assigned_to_me)

    async def claim_case(self, request_id, officer_user_id, reason):
        """Explicit same-unit self-assignment; never repair historical assignments."""
        from fastapi import HTTPException
        from app.security.scope import require_unit
        session = self.wellbeing_repo.session
        actor = session.info.get("actor", {})
        require_unit(actor)
        if actor.get("role") != "WELFARE_OFFICER" or actor.get("user_id") != str(officer_user_id):
            raise HTTPException(403, "Operation not permitted")
        if not reason.strip():
            raise HTTPException(422, "Assignment purpose required")
        session.info["actor"] = {**actor, "_claim_case": str(request_id)}
        try:
            case = await self.wellbeing_repo.lock_support_request(request_id)
            if not case:
                raise HTTPException(404, "Case not found")
            if case.status in ("CLOSED", "RESOLVED", "WITHDRAWN"):
                raise HTTPException(409, "Closed case cannot be assigned")
            if case.assigned_to_user_id == officer_user_id:
                return {"id": str(case.id), "status": case.status, "assigned_to_me": True}
            case.assigned_to_user_id = officer_user_id
            case.status = "ASSIGNED"
            await session.flush()
        finally:
            session.info["actor"] = actor
        await self.audit_repo.log_event(officer_user_id, "WELFARE_OFFICER", "CASE_ASSIGNED", "support_requests", request_id)
        return {"id": str(case.id), "status": case.status, "assigned_to_me": True}

    async def get_case_detail(self, request_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        req = await self.wellbeing_repo.get_support_request_by_id(request_id)
        if not req:
            return None

        person = await self.personnel_repo.get_by_id(req.personnel_id)
        actor = self.wellbeing_repo.session.info["actor"]
        await self.audit_repo.log_event(uuid.UUID(actor["user_id"]), "WELFARE_OFFICER", "CASE_CONTENT_ACCESS", "support_requests", req.id)
        unit = await self.unit_repo.get_by_id(person.unit_id) if person else None
        latest_wsi = await self.analytics_repo.get_latest_wsi(req.personnel_id) if person else None

        return {
            "id": str(req.id),
            "personnel_id": str(req.personnel_id),
            "pseudo_id": person.pseudo_id if person else "N/A",
            "rank_or_grade": person.rank_or_grade if person else "N/A",
            "role_title": person.role_title if person else "N/A",
            "unit": {
                "id": str(unit.id) if unit else None,
                "unit_name": unit.unit_name if unit else "N/A",
                "unit_code": unit.unit_code if unit else "N/A",
            },
            "request_type": req.request_type,
            "status": req.status,
            "priority": req.priority,
            "request_text": req.request_text,
            "follow_up_date": req.follow_up_date.isoformat() if req.follow_up_date else None,
            "created_at": req.created_at.isoformat(),
            "closed_at": req.closed_at.isoformat() if req.closed_at else None,
            "permitted_operational_wsi": float(latest_wsi.wsi_score) if latest_wsi else None,
        }

    async def update_case(
        self,
        request_id: uuid.UUID,
        officer_user_id: uuid.UUID,
        status: str,
        follow_up_date: Optional[date] = None,
        notes: Optional[str] = None,
        idempotency_key: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        from fastapi import HTTPException
        from app.services.welfare_case_service import WelfareCaseService, _digest
        req = await self.wellbeing_repo.get_support_request_by_id(request_id)
        if not req:
            return None
        actor = self.wellbeing_repo.session.info.get("actor", {})
        if actor.get("role") != "WELFARE_OFFICER" or actor.get("user_id") != str(officer_user_id):
            raise HTTPException(403, "Operation not permitted")
        status = status.upper().strip()
        if status not in ("ASSIGNED", "IN_PROGRESS", "CLOSED"):
            raise HTTPException(422, "Only canonical current case states are writable")
        if status == req.status and not follow_up_date and not notes:
            return {"id": str(req.id), "status": req.status,
                    "follow_up_date": req.follow_up_date.isoformat() if req.follow_up_date else None,
                    "closed_at": req.closed_at.isoformat() if req.closed_at else None}
        key = idempotency_key or "legacy-update-" + _digest({
            "case_id": str(req.id), "status": status, "follow_up_date": follow_up_date, "notes": notes,
        })
        if status == "CLOSED":
            raise HTTPException(422, "Use explicit CLOSE action with Personnel-visible outcome note")
        elif follow_up_date:
            await WelfareCaseService(self.wellbeing_repo.session).action(
                req.id, "FOLLOW_UP", notes, "OFFICER", follow_up_date,
                status if status != req.status else None, key,
            )
        elif status == "IN_PROGRESS":
            await WelfareCaseService(self.wellbeing_repo.session).action(
                req.id, "STATUS_CHANGE", notes, "OFFICER", None, status, key,
            )
        else:
            raise HTTPException(409, "Use explicit assignment action")
        return {
            "id": str(req.id),
            "status": req.status,
            "follow_up_date": req.follow_up_date.isoformat() if req.follow_up_date else None,
            "closed_at": req.closed_at.isoformat() if req.closed_at else None,
        }
