import uuid
from datetime import date, datetime, timezone
from typing import List, Optional
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Alert, AnomalyEvent, AuditEvent, BaselineMetric, ModelOutput, WsiSnapshot, Personnel


class AnalyticsRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_latest_wsi(self, personnel_id: uuid.UUID) -> Optional[WsiSnapshot]:
        current = await self.get_current_operational(personnel_id)
        if current["wsi"]["status"] != "VALID":
            return None
        expected_id = uuid.uuid5(uuid.NAMESPACE_URL,
            f"prahari:wsi:{personnel_id}:{current['wsi']['as_of']}:{current['wsi']['policy_version']}:{current['wsi']['source_hash']}")
        stmt = (
            select(WsiSnapshot)
            .where(WsiSnapshot.personnel_id == personnel_id,
                WsiSnapshot.id == expected_id,
                WsiSnapshot.snapshot_date == datetime.now(timezone.utc).date(),
                WsiSnapshot.policy_version == current["wsi"]["policy_version"],
                WsiSnapshot.wsi_score == current["wsi"]["value"])
            .order_by(WsiSnapshot.snapshot_date.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_current_operational(self, personnel_id: uuid.UUID):
        from app.repositories.detection_repository import DetectionRepository
        from app.services.operational_analytics_service import OperationalAnalyticsService
        person = (await self.session.execute(select(Personnel).where(Personnel.id == personnel_id))).scalar_one_or_none()
        if person is None:
            from fastapi import HTTPException
            raise HTTPException(404, "Personnel not found")
        cutoff = datetime.now(timezone.utc).date()
        subject = {"id": person.id, "unit_id": person.unit_id}
        return await self.session.run_sync(lambda session: OperationalAnalyticsService(
            DetectionRepository(session.connection())).calculate(subject, cutoff))

    async def get_wsi_history(self, personnel_id: uuid.UUID, limit: int = 30) -> List[WsiSnapshot]:
        stmt = (
            select(WsiSnapshot)
            .where(WsiSnapshot.personnel_id == personnel_id)
            .order_by(WsiSnapshot.snapshot_date.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_unit_wsi_snapshots(self, unit_id: uuid.UUID) -> List[WsiSnapshot]:
        # Subquery to get max snapshot_date per personnel_id
        stmt = (
            select(WsiSnapshot)
            .where(WsiSnapshot.unit_id == unit_id,
                WsiSnapshot.snapshot_date == datetime.now(timezone.utc).date())
            .order_by(WsiSnapshot.snapshot_date.desc())
        )
        result = await self.session.execute(stmt)
        # Deduplicate to latest per person in Python
        seen = set()
        latest = []
        for snap in result.scalars().all():
            if snap.personnel_id not in seen:
                seen.add(snap.personnel_id)
                current = await self.get_current_operational(snap.personnel_id)
                if (current["wsi"]["status"] == "VALID"
                        and current["wsi"]["policy_version"] == snap.policy_version
                        and current["wsi"]["value"] == float(snap.wsi_score)
                        and snap.id == uuid.uuid5(uuid.NAMESPACE_URL,
                            f"prahari:wsi:{snap.personnel_id}:{current['wsi']['as_of']}:{current['wsi']['policy_version']}:{current['wsi']['source_hash']}")):
                    latest.append(snap)
        return latest

    async def get_unit_wsi_history(
        self, unit_id: uuid.UUID, start_date: date
    ) -> List[WsiSnapshot]:
        """Return persisted operational snapshots for an authorised unit window."""
        stmt = (
            select(WsiSnapshot)
            .where(
                WsiSnapshot.unit_id == unit_id,
                WsiSnapshot.snapshot_date >= start_date,
            )
            .order_by(WsiSnapshot.snapshot_date.asc(), WsiSnapshot.personnel_id.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_latest_baseline(self, personnel_id: uuid.UUID, metric_name: str = "WORKLOAD_EWMA") -> Optional[BaselineMetric]:
        stmt = (
            select(BaselineMetric)
            .where(
                BaselineMetric.personnel_id == personnel_id,
                BaselineMetric.metric_name == metric_name,
            )
            .order_by(BaselineMetric.metric_date.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_anomaly(self, personnel_id: uuid.UUID) -> Optional[AnomalyEvent]:
        stmt = (
            select(AnomalyEvent)
            .where(AnomalyEvent.personnel_id == personnel_id)
            .order_by(AnomalyEvent.event_date.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_prediction(
        self, personnel_id: uuid.UUID, target_name: Optional[str] = "next_30d_leave_anomaly"
    ) -> Optional[ModelOutput]:
        stmt = select(ModelOutput).where(ModelOutput.personnel_id == personnel_id)
        if target_name:
            # Legacy target names never promote historical rows to governed Model-A.
            stmt = stmt.where(ModelOutput.target_name == "next_30d_leave_anomaly")
        stmt = stmt.where(
            ModelOutput.model_version == "1.0.0",
            ModelOutput.feature_set_version == "v2.1-SetB-15ops",
            ModelOutput.training_data_version == "v2.1-frozen-prototype",
            ModelOutput.wellbeing_probability.is_(None), ModelOutput.combined_probability.is_(None),
            ModelOutput.explanation_json["governance"].astext == "MODEL_A_FINAL_LOCKED",
            ModelOutput.explanation_json["artifact_hash"].astext == "2e540b4ca0c3db9cf32b7601ac23319ead74db5c18ac5fd7c466b2ef4ae290b9",
            ModelOutput.explanation_json["target_contract"].astext == "v2.1-approved-leave-lifecycle",
            # System detection failures are not the user's audit history. Read only
            # existence of allowlisted operational events for the scoped person.
            ~select(AuditEvent.__table__.c.id).where(
                AuditEvent.__table__.c.resource_id == personnel_id,
                AuditEvent.__table__.c.action.in_(("OPERATIONAL_PERSON_UNAVAILABLE", "OPERATIONAL_PERSON_FAILURE")),
                AuditEvent.__table__.c.created_at > ModelOutput.created_at,
            ).exists(),
        )
        stmt = stmt.order_by(ModelOutput.prediction_date.desc()).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_alerts_by_unit(self, unit_id: uuid.UUID) -> List[Alert]:
        stmt = (
            select(Alert)
            .where(Alert.unit_id == unit_id, Alert.status.in_(("OPEN", "ACKNOWLEDGED")))
            .order_by(Alert.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_alerts_by_personnel(self, personnel_id: uuid.UUID) -> List[Alert]:
        stmt = (
            select(Alert)
            .where(Alert.personnel_id == personnel_id, Alert.status.in_(("OPEN", "ACKNOWLEDGED")))
            .order_by(Alert.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
