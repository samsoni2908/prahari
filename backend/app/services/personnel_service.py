import uuid
from datetime import date, datetime
from typing import List, Dict, Any, Optional
from app.models import SupportRequest, WellbeingConsent, WellbeingPrivate, WellbeingResult
from app.repositories.personnel_repository import PersonnelRepository
from app.repositories.unit_repository import UnitRepository
from app.repositories.wellbeing_repository import WellbeingRepository
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.operational_repository import OperationalRepository
from app.repositories.audit_repository import AuditRepository


class PersonnelService:
    def __init__(
        self,
        personnel_repo: PersonnelRepository,
        unit_repo: UnitRepository,
        wellbeing_repo: WellbeingRepository,
        analytics_repo: AnalyticsRepository,
        operational_repo: OperationalRepository,
        audit_repo: AuditRepository,
    ):
        self.personnel_repo = personnel_repo
        self.unit_repo = unit_repo
        self.wellbeing_repo = wellbeing_repo
        self.analytics_repo = analytics_repo
        self.operational_repo = operational_repo
        self.audit_repo = audit_repo

    async def get_profile(self, personnel_id: uuid.UUID) -> Optional[Dict[str, Any]]:
        person = await self.personnel_repo.get_by_id(personnel_id)
        if not person:
            return None

        unit = await self.unit_repo.get_by_id(person.unit_id)
        history = await self.personnel_repo.get_posting_history(personnel_id)

        return {
            "id": str(person.id),
            "personnel_code": person.personnel_code,
            "pseudo_id": person.pseudo_id,
            "rank_or_grade": person.rank_or_grade,
            "role_title": person.role_title,
            "status": person.status,
            "service_years": float(person.service_years) if person.service_years is not None else None,
            "joining_date": person.joining_date.isoformat() if person.joining_date else None,
            "unit": {
                "id": str(unit.id),
                "unit_code": unit.unit_code,
                "unit_name": unit.unit_name,
                "unit_type": unit.unit_type,
                "location_label": unit.location_label,
            }
            if unit
            else None,
            "postings": [
                {
                    "unit_id": str(p.unit_id),
                    "start_date": p.posting_start_date.isoformat(),
                    "end_date": p.posting_end_date.isoformat() if p.posting_end_date else None,
                    "type": p.posting_type,
                    "location": p.location_label,
                }
                for p in history
            ],
        }

    async def get_rest(self, personnel_id: uuid.UUID, limit: int):
        rows = await self.operational_repo.get_recent_rest_records(personnel_id, limit)
        return [{"id": str(row.id), "date": row.record_date.isoformat(),
                 "rest_hours": float(row.rest_hours) if row.rest_hours is not None else None,
                 "rest_gap_hours": float(row.rest_gap_hours) if row.rest_gap_hours is not None else None,
                 "source": row.source, "data_quality_status": row.data_quality_status} for row in rows]

    async def get_consent(self, personnel_id: uuid.UUID) -> Dict[str, Any]:
        consent = await self.wellbeing_repo.get_latest_consent(personnel_id)
        if not consent:
            return {
                "consented": False,
                "status": "NONE",
                "purpose": "Voluntary confidential personnel wellbeing self-reflection",
            }
        return {
            "consented": consent.status == "ACTIVE",
            "status": consent.status,
            "consent_version": consent.consent_version,
            "purpose": consent.purpose,
            "consented_at": consent.consented_at.isoformat() if consent.consented_at else None,
            "withdrawn_at": consent.withdrawn_at.isoformat() if consent.withdrawn_at else None,
        }

    async def update_consent(
        self, personnel_id: uuid.UUID, action: str, purpose: str = "Voluntary confidential personnel wellbeing self-reflection"
    ) -> Dict[str, Any]:
        now = datetime.utcnow()
        if action.upper() == "CONSENT":
            consent = WellbeingConsent(
                personnel_id=personnel_id,
                consent_version="v2.0",
                purpose=purpose,
                status="ACTIVE",
                consented_at=now,
            )
            await self.wellbeing_repo.record_consent(consent)
            await self.audit_repo.log_event(
                actor_user_id=None,
                actor_role="PERSONNEL",
                action="CONSENT_GRANTED",
                resource_type="wellbeing_consent",
                resource_id=personnel_id,
                result="SUCCESS",
            )
            return {"status": "ACTIVE", "consented": True, "consented_at": now.isoformat()}
        else:
            consent = WellbeingConsent(
                personnel_id=personnel_id,
                consent_version="v2.0",
                purpose=purpose,
                status="WITHDRAWN",
                withdrawn_at=now,
            )
            await self.wellbeing_repo.record_consent(consent)
            await self.audit_repo.log_event(
                actor_user_id=None,
                actor_role="PERSONNEL",
                action="CONSENT_WITHDRAWN",
                resource_type="wellbeing_consent",
                resource_id=personnel_id,
                result="SUCCESS",
            )
            return {"status": "WITHDRAWN", "consented": False, "withdrawn_at": now.isoformat()}

    async def submit_self_check(
        self,
        personnel_id: uuid.UUID,
        answers: Dict[str, Any],
        instrument_name: str = "WELLBEING_SELF_CHECK_V2",
    ) -> Dict[str, Any]:
        from fastapi import HTTPException
        from app.ml.wellbeing_framework import GLOBAL_INSTRUMENT_REGISTRY

        # 1. Verify active voluntary consent
        consent = await self.wellbeing_repo.get_latest_consent(personnel_id)
        if not consent or consent.status != "ACTIVE":
            raise HTTPException(
                status_code=403,
                detail="CONSENT_REQUIRED: Active voluntary consent is required before submitting a self-check",
            )

        # 2. Retrieve adapter from registry
        adapter = GLOBAL_INSTRUMENT_REGISTRY.get(instrument_name)
        if not adapter.is_activated:
            raise HTTPException(
                status_code=503,
                detail=f"INSTRUMENT_NOT_ACTIVATED: instrument '{instrument_name}' has not received canonical approval",
            )

        # 3. Validate raw responses strictly
        val = adapter.validate_responses(answers)
        if not val.is_valid:
            raise HTTPException(
                status_code=422,
                detail=f"INVALID_RESPONSE: {'; '.join(val.errors)}",
            )

        today = date.today()

        # 4. Store raw responses strictly in private storage
        check = WellbeingPrivate(
            personnel_id=personnel_id,
            assessment_date=today,
            instrument_name=adapter.instrument_id,
            instrument_version=adapter.instrument_version,
            answers_json=answers,
            score_json=None,
        )
        await self.wellbeing_repo.submit_self_check(check)

        # 5. Derive non-raw summary result
        derived = adapter.derive_result(answers, assessment_date=today)
        score_payload = {
            "instrument_id": adapter.instrument_id,
            "instrument_version": adapter.instrument_version,
            "scoring_version": derived.scoring_version,
            "processing_version": "v1.0-governed",
            "status": derived.status,
            "summary_scores": derived.summary_scores,
            "confidence_score": round(derived.confidence_score, 4),
        }
        result_row = WellbeingResult(
            wellbeing_private_id=check.id,
            personnel_id=personnel_id,
            instrument_name=adapter.instrument_id,
            assessment_date=today,
            score_summary_json=score_payload,
            category_label=derived.attention_category,
            trend_label=derived.trend_direction,
            model_version=f"{adapter.instrument_version}:{derived.scoring_version}",
        )
        await self.wellbeing_repo.record_wellbeing_result(result_row)

        # 6. Privacy-safe audit logging (ZERO raw answer payload copy)
        await self.audit_repo.log_event(
            actor_user_id=None,
            actor_role="PERSONNEL",
            action="SELF_CHECK_SUBMITTED",
            resource_type="wellbeing_private",
            resource_id=check.id,
            result="SUCCESS",
        )

        # 7. Return safe projection (zero raw answers in response payload)
        return {
            "id": str(check.id),
            "assessment_date": today.isoformat(),
            "instrument_name": check.instrument_name,
            "status": derived.status,
            "category_label": derived.attention_category,
            "trend_label": derived.trend_direction,
        }

    async def get_deployments(self, personnel_id: uuid.UUID) -> List[Dict[str, Any]]:
        deps = await self.operational_repo.get_active_deployments(personnel_id)
        return [
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

    async def get_duties(self, personnel_id: uuid.UUID) -> List[Dict[str, Any]]:
        duties = await self.operational_repo.get_recent_duties(personnel_id, limit=30)
        return [
            {
                "id": str(d.id),
                "duty_date": d.duty_date.isoformat(),
                "start_at": d.start_at.isoformat(),
                "end_at": d.end_at.isoformat(),
                "duty_type": d.duty_type,
                "shift_type": d.shift_type,
                "is_night": d.is_night,
                "hours": float(d.hours),
            }
            for d in duties
        ]

    async def get_leave(self, personnel_id: uuid.UUID) -> List[Dict[str, Any]]:
        leaves = await self.operational_repo.get_recent_leaves(personnel_id, limit=20)
        return [
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

    async def get_risk(self, personnel_id: uuid.UUID) -> Dict[str, Any]:
        return await self.analytics_repo.get_current_operational(personnel_id)


    async def list_self_checks(self, personnel_id: uuid.UUID) -> List[Dict[str, Any]]:
        # Enforced via server-side application authorization / query scoping
        from app.ml.wellbeing_framework import GLOBAL_INSTRUMENT_REGISTRY, GOVERNANCE_GOVERNED, GOVERNANCE_LEGACY

        checks = await self.wellbeing_repo.list_self_checks(personnel_id)
        out = []
        for c in checks:
            is_active = GLOBAL_INSTRUMENT_REGISTRY.is_activated(c.instrument_name)
            gov_status = GOVERNANCE_GOVERNED if is_active else GOVERNANCE_LEGACY
            out.append({
                "id": str(c.id),
                "assessment_date": c.assessment_date.isoformat(),
                "instrument_name": c.instrument_name,
                "governance_status": gov_status,
                "score": c.score_json,
                "answers": c.answers_json,
                "created_at": c.created_at.isoformat(),
            })
        return out

    async def list_wellbeing_results(self, personnel_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Returns non-raw derived results for authenticated personnel with explicit governance distinction."""
        from app.ml.wellbeing_framework import GLOBAL_INSTRUMENT_REGISTRY, GOVERNANCE_GOVERNED, GOVERNANCE_LEGACY

        results = await self.wellbeing_repo.list_wellbeing_results(personnel_id)
        out = []
        for r in results:
            summary = r.score_summary_json if isinstance(r.score_summary_json, dict) else {}
            is_gov = (
                summary.get("processing_version") == "v1.0-governed"
                and GLOBAL_INSTRUMENT_REGISTRY.is_activated(r.instrument_name)
            )
            gov_status = GOVERNANCE_GOVERNED if is_gov else GOVERNANCE_LEGACY
            out.append({
                "id": str(r.id),
                "assessment_date": r.assessment_date.isoformat(),
                "instrument_name": r.instrument_name,
                "governance_status": gov_status,
                "processing_status": summary.get("status", "ENGINE_B_AVAILABLE") if is_gov else "HISTORICAL_RECORD",
                "score_summary": r.score_summary_json if is_gov else {
                    "status": "LEGACY_UNGOVERNED",
                    "historical_score_data": r.score_summary_json,
                },
                "category_label": r.category_label if is_gov else "HISTORICAL_RECORD",
                "trend_label": r.trend_label if is_gov else "INSUFFICIENT_GOVERNED_HISTORY",
                "historical_category_label": r.category_label if not is_gov else None,
                "historical_trend_label": r.trend_label if not is_gov else None,
                "model_version": r.model_version,
                "created_at": r.created_at.isoformat(),
            })
        return out

    async def create_support_request(
        self, personnel_id: uuid.UUID, request_type: str, priority: str, details: str,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        import hashlib
        import json
        from fastapi import HTTPException
        from sqlalchemy import select, text
        from app.models import SupportRequest

        actor = self.wellbeing_repo.session.info.get("actor") or {}
        if actor.get("role") != "PERSONNEL" or actor.get("personnel_id") != str(personnel_id):
            raise HTTPException(403, "Personnel ownership required")
        request_type = request_type.strip().upper()
        if request_type not in ("LEAVE_ASSISTANCE", "STRESS_FATIGUE", "MEDICAL_HEALTH", "FAMILY_PERSONAL"):
            raise HTTPException(422, "Unsupported support request type")
        priority = priority.strip().upper()
        priority = {"LOW": "NORMAL", "MEDIUM": "NORMAL", "HIGH": "URGENT"}.get(priority, priority)
        if priority not in ("NORMAL", "URGENT"):
            raise HTTPException(422, "Unsupported manual priority")
        details = details.strip()
        if not 10 <= len(details) <= 2000:
            raise HTTPException(422, "Bounded support request reason required")
        request_hash = hashlib.sha256(json.dumps({
            "type": request_type, "priority": priority, "details": details,
        }, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        if not idempotency_key or not 8 <= len(idempotency_key.strip()) <= 200:
            raise HTTPException(422, "Idempotency-Key required")
        session = self.wellbeing_repo.session
        seed = str(personnel_id) + ":" + idempotency_key.strip()
        lock_hash = hashlib.sha256(seed.encode()).digest()
        lock_id = int.from_bytes(lock_hash[:8], "big", signed=True)
        await session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_id})
        rows = list((await session.execute(select(SupportRequest).where(
            SupportRequest.personnel_id == personnel_id,
        ).order_by(SupportRequest.created_at.desc()))).scalars())
        key_hash = lock_hash.hex()
        prior = next((row for row in rows if row.request_key_hash == key_hash), None)
        if prior:
            if prior.request_hash != request_hash:
                raise HTTPException(409, "Idempotency key already used with different payload")
            return {
                "id": str(prior.id), "request_type": prior.request_type,
                "status": prior.status, "priority": prior.priority,
                "created_at": prior.created_at.isoformat(), "replay_safe": True,
            }
        req = SupportRequest(
            personnel_id=personnel_id,
            request_type=request_type,
            status="OPEN",
            priority=priority,
            request_text=details,
            request_key_hash=key_hash,
            request_hash=request_hash,
        )
        saved = await self.wellbeing_repo.create_support_request(req)

        await self.audit_repo.log_event(
            actor_user_id=None,
            actor_role="PERSONNEL",
            action="SUPPORT_REQUEST_SUBMITTED",
            resource_type="support_requests",
            resource_id=saved.id,
            result="SUCCESS",
        )

        return {
            "id": str(saved.id),
            "request_type": saved.request_type,
            "status": saved.status,
            "priority": saved.priority,
            "created_at": saved.created_at.isoformat(),
            "replay_safe": False,
        }

    async def list_support_requests(self, personnel_id: uuid.UUID) -> List[Dict[str, Any]]:
        reqs = await self.wellbeing_repo.list_support_requests_for_personnel(personnel_id)
        return [
            {
                "id": str(r.id),
                "request_type": r.request_type,
                "status": r.status,
                "priority": r.priority,
                "request_text": r.request_text,
                "follow_up_date": r.follow_up_date.isoformat() if r.follow_up_date else None,
                "created_at": r.created_at.isoformat(),
            }
            for r in reqs
        ]

    async def get_privacy_history(self, personnel_id: uuid.UUID) -> List[Dict[str, Any]]:
        from sqlalchemy import or_, select
        from app.models import AuditEvent
        actor = self.wellbeing_repo.session.info.get("actor") or {}
        if actor.get("role") != "PERSONNEL" or actor.get("personnel_id") != str(personnel_id):
            from fastapi import HTTPException
            raise HTTPException(403, "Personnel ownership required")
        own_cases = select(SupportRequest.id).where(SupportRequest.personnel_id == personnel_id)
        events = list((await self.wellbeing_repo.session.execute(select(AuditEvent).where(or_(
            AuditEvent.actor_user_id == uuid.UUID(actor["user_id"]),
            (AuditEvent.action.in_(("CASE_CONTENT_ACCESS", "CASE_IDENTITY_ACCESS")))
            & ((AuditEvent.resource_id.in_(own_cases))
               | ((AuditEvent.resource_type == "personnel") & (AuditEvent.resource_id == personnel_id))),
        )).order_by(AuditEvent.created_at.desc()).limit(100))).scalars())
        return [
            {
                "id": str(e.id),
                "action": e.action,
                "actor_role": e.actor_role,
                "resource_type": e.resource_type,
                "result": e.result,
                "timestamp": e.created_at.isoformat(),
            }
            for e in events
        ]
