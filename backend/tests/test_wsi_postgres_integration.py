"""Real source repository/persistence proof; every fixture write rolls back."""
import hashlib
import json
import uuid
from datetime import date, datetime, timedelta, timezone
from sqlalchemy import create_engine, insert, select, update
from app.config import settings
from app.analytics.operational_feature_adapter import source_hash, row_key, POLICY
from app.repositories.detection_repository import DetectionRepository, TABLES
from app.services.operational_analytics_service import OperationalAnalyticsService
from app.schemas.operational_analytics import OperationalAnalyticsView


def test_wsi_database_sources_persistence_replay_and_correction():
    engine = create_engine(settings.DATABASE_URL_SYNC, hide_parameters=True)
    cutoff = date(2026, 9, 1)
    known = datetime(2026, 1, 1, tzinfo=timezone.utc)
    person_id, unit_id = uuid.uuid4(), uuid.uuid4()
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            admin = connection.execute(select(TABLES["users"].c.id).where(
                TABLES["users"].c.role == "ADMIN", TABLES["users"].c.is_active.is_(True)).limit(1)).scalar_one()
            connection.execute(insert(TABLES["units"]).values(id=unit_id, unit_code=str(unit_id),
                unit_name="Rollback-only WSI fixture", unit_type="TEST", sanctioned_strength=10))
            connection.execute(insert(TABLES["personnel"]).values(id=person_id, personnel_code=str(person_id),
                pseudo_id=str(person_id), full_name="Synthetic rollback-only fixture", unit_id=unit_id,
                rank_or_grade="TEST", role_title="TEST", status="ACTIVE"))
            connection.execute(insert(TABLES["posting_history"]).values(id=uuid.uuid4(), personnel_id=person_id,
                unit_id=unit_id, posting_start_date=date(2026, 1, 1), posting_type="TEST"))
            duty_ids = []
            for index in range(1, 8):
                day = cutoff - timedelta(days=index)
                begin = datetime.combine(day, datetime.min.time(), timezone.utc) + timedelta(hours=8)
                identifier = uuid.uuid4()
                duty_ids.append(identifier)
                connection.execute(insert(TABLES["duties"]).values(id=identifier, personnel_id=person_id,
                    unit_id=unit_id, duty_date=day, start_at=begin, end_at=begin+timedelta(hours=8),
                    hours=8, is_night=False, duty_type="TEST", shift_type="DAY"))
                connection.execute(insert(TABLES["rest_records"]).values(id=uuid.uuid4(), personnel_id=person_id,
                    record_date=day, rest_hours=8, rest_gap_hours=16, source="DERIVED_FROM_DUTY", data_quality_status="VALID"))
                connection.execute(insert(TABLES["staffing"]).values(id=uuid.uuid4(), unit_id=unit_id,
                    record_date=day, sanctioned_strength=10, available_strength=8, required_strength=10))
            connection.execute(insert(TABLES["leave_records"]).values(id=uuid.uuid4(), personnel_id=person_id,
                leave_type="TEST", start_date=date(2026, 7, 1), end_date=date(2026, 7, 3), days=3,
                status="COMPLETED", actual_start_date=date(2026, 7, 1), actual_end_date=date(2026, 7, 3)))
            values = {"wsi.d.reference_hours": 56, "wsi.r.reference_hours": 12,
                "wsi.c.reference_days": 7, "wsi.l.reference_days": 60, "wsi.h.reference_intensity": 5}
            policy_hash = hashlib.sha256(json.dumps(values, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            connection.execute(insert(TABLES["policy_config"]).values(id=uuid.uuid4(), policy_key="analytics.wsi",
                policy_value_json={"activation_status": "ACTIVE", "content_hash": policy_hash, "values": values},
                version="TEST_WSI_V1", effective_from=known, created_at=known, updated_by_user_id=admin))
            repository = DetectionRepository(connection)
            data = repository.wsi_sources(unit_id, cutoff)
            manifest = {"policy": POLICY, "cutoff": cutoff.isoformat(), "families": list(data),
                "unknown_gaps": 0, "source_hash": source_hash(data),
                "known_at": {name+"."+row_key(row): "2026-09-01T00:00:00+00:00" for name, rows in data.items() for row in rows},
                "complete_days": {str(person_id): [(cutoff-timedelta(days=i)).isoformat() for i in range(1, 31)]},
                "leave_completion_history_complete": {str(person_id): True}, "completed_intervals": {}}
            connection.execute(insert(TABLES["policy_config"]).values(id=uuid.uuid4(),
                policy_key=f"analytics.wsi.coverage.{unit_id}.{cutoff}", policy_value_json=manifest,
                version=POLICY, effective_from=known, created_at=known, updated_by_user_id=admin))
            service = OperationalAnalyticsService(repository)
            person = {"id": person_id, "unit_id": unit_id}
            result = service.process(person, cutoff)
            assert result["wsi"]["status"] == "VALID" and result["wsi"]["value"] == 57.67
            assert result["baseline"]["status"] == "BASELINE_UNAVAILABLE"
            assert OperationalAnalyticsView.model_validate(result).wsi.value == 57.67
            assert service.process(person, cutoff) == result
            snapshots = connection.execute(select(TABLES["wsi_snapshots"].c.id).where(
                TABLES["wsi_snapshots"].c.personnel_id == person_id)).all()
            assert len(snapshots) == 1
            connection.execute(update(TABLES["duties"]).where(TABLES["duties"].c.id == duty_ids[0]).values(is_night=True))
            stale = service.process(person, cutoff)
            assert stale["wsi"]["status"] == "DATA_STALE" and stale["wsi"]["value"] is None
            assert len(connection.execute(select(TABLES["wsi_snapshots"].c.id).where(
                TABLES["wsi_snapshots"].c.personnel_id == person_id)).all()) == 1
        finally:
            transaction.rollback()
    engine.dispose()
