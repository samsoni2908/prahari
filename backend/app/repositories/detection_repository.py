"""Operational-only source retrieval and governed persistence; never private tables."""
import uuid
from datetime import timedelta
from sqlalchemy import select, text, and_, or_, insert
from app.models import Base

TABLES = Base.metadata.tables
SOURCE_COLUMNS = {
    "personnel": ("id", "unit_id", "pseudo_id", "rank_or_grade", "role_title", "status"),
    "duties": ("id", "personnel_id", "unit_id", "duty_date", "start_at", "end_at", "hours", "is_night"),
    "rest_records": ("id", "personnel_id", "record_date", "rest_hours", "rest_gap_hours", "data_quality_status", "source"),
    "leave_records": ("id", "personnel_id", "start_date", "end_date", "status"),
    "deployments": ("id", "personnel_id", "unit_id", "start_date", "end_date", "intensity_level"),
    "training": ("id", "personnel_id", "start_date", "end_date", "status"),
    "staffing": ("id", "unit_id", "record_date", "available_strength", "required_strength"),
    "posting_history": ("id", "personnel_id", "unit_id", "posting_start_date", "posting_end_date"),
    "person_skills": ("personnel_id", "skill_id", "valid_from", "valid_until"),
    "skills": ("id",),
}
TARGET = "next_30d_leave_anomaly"
FEATURE_VERSION = "v2.1-SetB-15ops"
MODEL_VERSION = "1.0.0"
TRAINING_VERSION = "v2.1-frozen-prototype"


class DetectionRepository:
    def __init__(self, connection):
        self.connection = connection

    def rows(self, table, predicate):
        t = TABLES[table]
        return [dict(r) for r in self.connection.execute(
            select(*(t.c[c] for c in SOURCE_COLUMNS[table])).where(predicate).order_by(*t.primary_key.columns)
        ).mappings()]

    def people(self, unit_id=None):
        t = TABLES["personnel"]
        return self.rows("personnel", and_(t.c.status == "ACTIVE", t.c.unit_id == unit_id) if unit_id else t.c.status == "ACTIVE")

    def sources(self, unit_id, cutoff):
        people = self.people(unit_id)
        ids = [r["id"] for r in people]
        start = cutoff - timedelta(days=57)
        data = {"personnel": people}
        for name in SOURCE_COLUMNS:
            if name == "personnel":
                continue
            t = TABLES[name]
            if name == "skills":
                predicate = t.c.id.in_(select(TABLES["person_skills"].c.skill_id).where(TABLES["person_skills"].c.personnel_id.in_(ids)))
            elif name == "staffing":
                predicate = and_(t.c.unit_id == unit_id, t.c.record_date >= cutoff-timedelta(days=7), t.c.record_date < cutoff)
            else:
                predicate = t.c.personnel_id.in_(ids)
                if name in ("duties", "rest_records"):
                    field = t.c.duty_date if name == "duties" else t.c.record_date
                    predicate = and_(predicate, field >= start, field < cutoff)
                elif name in ("leave_records", "deployments", "training"):
                    predicate = and_(predicate, t.c.start_date < cutoff, or_(t.c.end_date.is_(None), t.c.end_date >= start))
                elif name == "posting_history":
                    predicate = and_(predicate, t.c.posting_start_date < cutoff, or_(t.c.posting_end_date.is_(None), t.c.posting_end_date >= start))
            data[name] = self.rows(name, predicate)
        return data

    def manifest(self, unit_id, cutoff):
        p, u = TABLES["policy_config"], TABLES["users"]
        row = self.connection.execute(select(p.c.policy_value_json).join(u, p.c.updated_by_user_id == u.c.id).where(
            p.c.policy_key == f"analytics.coverage.{unit_id}.{cutoff.isoformat()}",
            p.c.version == "SOURCE_COVERAGE_POLICY_V1_SYNTHETIC_DEMO",
            u.c.role == "ADMIN", u.c.is_active.is_(True),
        )).scalar_one_or_none()
        return row

    def lock_person(self, personnel_id):
        # Existing parent row serializes inference and alert effects across processes.
        p = TABLES["personnel"]
        self.connection.execute(select(p.c.id).where(p.c.id == personnel_id).with_for_update()).scalar_one()

    def wsi_sources(self, unit_id, cutoff):
        data = self.sources(unit_id, cutoff)
        leave = TABLES["leave_records"]
        identifiers = [row["id"] for row in data["personnel"]]
        # Whole actual leave history, not a 57-day join-date substitute for L.
        columns = (*SOURCE_COLUMNS["leave_records"], "actual_start_date", "actual_end_date")
        data["leave_records"] = [dict(row) for row in self.connection.execute(
            select(*(leave.c[name] for name in columns)).where(
                leave.c.personnel_id.in_(identifiers), leave.c.start_date < cutoff,
            ).order_by(leave.c.id)).mappings()]
        return data

    def wsi_manifest(self, unit_id, cutoff):
        p, u = TABLES["policy_config"], TABLES["users"]
        return self.connection.execute(select(p.c.policy_value_json).join(u, p.c.updated_by_user_id == u.c.id).where(
            p.c.policy_key == f"analytics.wsi.coverage.{unit_id}.{cutoff.isoformat()}",
            p.c.version == "SOURCE_COVERAGE_POLICY_V1_SYNTHETIC_DEMO",
            u.c.role == "ADMIN", u.c.is_active.is_(True),
        )).scalar_one_or_none()

    def wsi_policy(self, cutoff):
        from datetime import datetime, timezone
        import hashlib
        import json
        p, u = TABLES["policy_config"], TABLES["users"]
        at = datetime.combine(cutoff, datetime.min.time(), timezone.utc)
        rows = self.connection.execute(select(p).join(u, p.c.updated_by_user_id == u.c.id).where(
            p.c.policy_key == "analytics.wsi", p.c.effective_from <= at,
            or_(p.c.effective_until.is_(None), p.c.effective_until > at),
            p.c.created_at <= at, u.c.role == "ADMIN", u.c.is_active.is_(True),
        )).mappings().all()
        if len(rows) != 1:
            return None
        row = rows[0]
        evidence = row["policy_value_json"]
        values = evidence.get("values")
        if not isinstance(values, dict) or evidence.get("activation_status") != "ACTIVE":
            return None
        digest = hashlib.sha256(json.dumps(values, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        if evidence.get("content_hash") != digest:
            return None
        return {"version": row["version"], "values": values,
            "effective_from": row["effective_from"].isoformat(),
            "effective_until": row["effective_until"].isoformat() if row["effective_until"] else None,
            "known_at": row["created_at"].isoformat(), "content_hash": digest}

    def governed(self, personnel_id, cutoff=None):
        t = TABLES["model_outputs"]
        q = select(t).where(t.c.personnel_id == personnel_id, t.c.target_name == TARGET,
             t.c.model_version == MODEL_VERSION, t.c.feature_set_version == FEATURE_VERSION,
             t.c.training_data_version == TRAINING_VERSION,
             t.c.wellbeing_probability.is_(None), t.c.combined_probability.is_(None))
        if cutoff:
            q = q.where(t.c.prediction_date == cutoff)
        return [dict(r) for r in self.connection.execute(q.order_by(t.c.prediction_date.desc(), t.c.created_at.desc(), t.c.id)).mappings()
                if (r["explanation_json"] or {}).get("governance") == "MODEL_A_FINAL_LOCKED"
                and (r["explanation_json"] or {}).get("artifact_hash") == "2e540b4ca0c3db9cf32b7601ac23319ead74db5c18ac5fd7c466b2ef4ae290b9"
                and (r["explanation_json"] or {}).get("target_contract") == "v2.1-approved-leave-lifecycle"]

    def audit(self, action, actor, cutoff, counts=None, reason=None, source_hash=None, personnel_id=None, availability=None, request_key_hash=None, request_hash=None):
        safe = {"cutoff": cutoff.isoformat()}
        if counts:
            safe.update({k:int(v) for k,v in counts.items() if k in ("processed","valid","unavailable","failed","alerts_created","alerts_suppressed")})
        if reason:
            safe["reason_code"] = reason
        if source_hash:
            safe["source_hash"] = source_hash
        if availability:
            safe["availability"] = availability
        if request_key_hash:
            safe["request_key_hash"] = request_key_hash
            safe["request_hash"] = request_hash
        self.connection.execute(insert(TABLES["audit_events"]).values(
            id=uuid.uuid4(), actor_user_id=uuid.UUID(actor["user_id"]) if actor and actor.get("user_id") else None,
            actor_role=actor["role"] if actor else None, action=action, resource_type="OPERATIONAL_DETECTION",
            resource_id=personnel_id,
            result="FAILURE" if reason else "SUCCESS", metadata_json=safe,
        ))
