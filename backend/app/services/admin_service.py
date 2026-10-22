import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy import text, select
from app.repositories.user_repository import UserRepository
from app.repositories.audit_repository import AuditRepository
from app.models import PolicyConfig


from app.repositories.personnel_repository import PersonnelRepository
from app.repositories.unit_repository import UnitRepository
from app.models import AuthSession, Personnel, User
from datetime import datetime, timezone
from app.security.password import hash_password


class AdminService:
    def __init__(
        self,
        user_repo: UserRepository,
        audit_repo: AuditRepository,
        personnel_repo: Optional[PersonnelRepository] = None,
        unit_repo: Optional[UnitRepository] = None,
    ):
        self.user_repo = user_repo
        self.audit_repo = audit_repo
        self.personnel_repo = personnel_repo
        self.unit_repo = unit_repo

    async def get_system_health(self) -> Dict[str, Any]:
        counts = {}
        tables = [
            "units", "personnel", "users", "duties", "rest_records",
            "wsi_snapshots", "alerts", "roster_scenarios", "audit_events",
        ]

        try:
            for tbl in tables:
                res = await self.audit_repo.session.execute(text(f"SELECT COUNT(*) FROM {tbl}"))
                counts[tbl] = res.scalar() or 0
            db_status = "HEALTHY"
        except Exception as e:
            db_status = "UNAVAILABLE"

        return {
            "system_name": "PRAHARI Personnel Stress & Welfare Monitoring System",
            "challenge_id": "SIH 26186",
            "version": "5.0-PROTOTYPE",
            "database_status": db_status,
            "table_record_counts": counts,
            "ml_engine": {
                "status": self.model_governance()["model_a"]["status"],
                "algorithms": ["LogisticRegression (Prediction)", "IsolationForest (Anomaly)", "EWMA/MAD (Baseline)"],
                "target": "Leave-pattern anomaly within 30 days",
                "features_active": self.model_governance()["model_a"]["feature_count"]
                if self.model_governance()["model_a"]["status"] == "MODEL_AVAILABLE" else 0,
                "source_coverage_required": True,
                "dataset_source": "PRAHARI_ML_DATA_V2_seed26186",
            },
            "security": {
                "rls_enforcement": "DEFERRED (application authorization required)",
                "wellbeing_firewall": "ACTIVE (Raw wellbeing isolated from command/admin)",
                "pseudonymization": "ACTIVE (pseudo_id for operational views)",
            }
        }

    async def list_users(self, limit: int = 100, offset: int = 0, query=None, role=None, is_active=None) -> List[Dict[str, Any]]:
        users = await self.user_repo.list_all(limit=limit, offset=offset, query=query, role=role, is_active=is_active)
        return [
            {
                "id": str(u.id),
                "username": u.username,
                "role": u.role,
                "unit_id": str(u.unit_id) if u.unit_id else None,
                "personnel_id": str(u.personnel_id) if u.personnel_id else None,
                "is_active": u.is_active,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ]

    async def create_user(
        self,
        username: str,
        password_clear: str,
        role: str,
        unit_id: Optional[uuid.UUID] = None,
        personnel_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        # Validate role is strictly one of the 4 locked roles
        valid_roles = {"PERSONNEL", "COMMANDER", "WELFARE_OFFICER", "ADMIN"}
        if role.upper() not in valid_roles:
            raise ValueError(f"Invalid role '{role}'. Must be one of {valid_roles}")
        if role.upper() in ("COMMANDER", "WELFARE_OFFICER") and not unit_id:
            raise ValueError("Assigned unit required")
        if role.upper() == "PERSONNEL":
            if not personnel_id:
                raise ValueError("Personnel binding required")
            person = await self.personnel_repo.get_by_id(personnel_id)
            existing = (await self.user_repo.session.execute(select(User.id).where(User.personnel_id == personnel_id))).first()
            if not person or existing:
                raise ValueError("Personnel binding unavailable")
            unit_id = person.unit_id
        elif personnel_id:
            raise ValueError("Personnel binding is not permitted for this role")
        if unit_id and not await self.unit_repo.get_by_id(unit_id):
            raise ValueError("Unit unavailable")

        hashed = hash_password(password_clear)
        user = User(
            username=username,
            password_hash=hashed,
            role=role.upper(),
            unit_id=unit_id,
            personnel_id=personnel_id,
            is_active=True,
        )
        saved = await self.user_repo.create(user)
        return {
            "id": str(saved.id),
            "username": saved.username,
            "role": saved.role,
            "unit_id": str(saved.unit_id) if saved.unit_id else None,
            "personnel_id": str(saved.personnel_id) if saved.personnel_id else None,
            "is_active": saved.is_active,
        }

    async def update_user(
        self,
        user_id: uuid.UUID,
        is_active: Optional[bool] = None,
        role: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return None
        if is_active is not None:
            user.is_active = is_active
        if role:
            valid_roles = {"PERSONNEL", "COMMANDER", "WELFARE_OFFICER", "ADMIN"}
            if role.upper() in valid_roles:
                if role.upper() != user.role:
                    # A role change cannot manufacture or rebind a private identity.
                    if role.upper() == "PERSONNEL" or user.personnel_id:
                        raise ValueError("Account binding incompatible with role change")
                    if role.upper() in ("COMMANDER", "WELFARE_OFFICER") and not user.unit_id:
                        raise ValueError("Assigned unit required")
                user.role = role.upper()
            else:
                raise ValueError("Invalid role")
        sessions = (await self.user_repo.session.execute(select(AuthSession).where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None)))).scalars().all()
        for session in sessions:
            session.revoked_at = datetime.now(timezone.utc)
            session.revoke_reason = "ACCOUNT_CHANGED"
        await self.audit_repo.log_event(None, "ADMIN", "ACCOUNT_CHANGED", "users", user.id)
        return {
            "id": str(user.id),
            "username": user.username,
            "role": user.role,
            "is_active": user.is_active,
        }

    async def list_personnel(self, limit: int = 100, offset: int = 0, query=None, unit_id=None) -> List[Dict[str, Any]]:
        if not self.personnel_repo:
            return []
        persons = await self.personnel_repo.search(limit=limit, offset=offset, query=query, unit_id=unit_id, include_name=True)
        return [
            {
                "id": str(p.id),
                "personnel_code": p.personnel_code,
                "pseudo_id": p.pseudo_id,
                "full_name": p.full_name,
                "rank_or_grade": p.rank_or_grade,
                "role_title": p.role_title,
                "status": p.status,
                "unit_id": str(p.unit_id),
                "service_years": float(p.service_years) if p.service_years is not None else None,
            }
            for p in persons
        ]

    async def list_units(self, limit=100, offset=0, query=None, is_active=None) -> List[Dict[str, Any]]:
        if not self.unit_repo:
            return []
        units = await self.unit_repo.list_units(limit, offset, query, is_active)
        return [
            {
                "id": str(u.id),
                "unit_code": u.unit_code,
                "unit_name": u.unit_name,
                "unit_type": u.unit_type,
                "location_label": u.location_label,
                "sanctioned_strength": u.sanctioned_strength,
                "is_active": u.is_active,
            }
            for u in units
        ]

    async def list_policies(self) -> List[Dict[str, Any]]:
        policies = await self.audit_repo.list_policies()
        return [
            {
                "id": str(p.id),
                "policy_key": p.policy_key,
                "policy_value": p.policy_value_json,
                "version": p.version,
                "effective_from": p.effective_from.isoformat(),
            }
            for p in policies
        ]

    async def list_audit_metadata(self, limit=50, offset=0):
        events = await self.audit_repo.list_events(limit=limit, offset=offset)
        # Retained historical reason/metadata fields may predate redaction.
        return [{"id": str(e.id), "actor_role": e.actor_role, "action": e.action, "resource_type": e.resource_type, "resource_id": str(e.resource_id) if e.resource_id else None, "result": e.result, "created_at": e.created_at.isoformat()} for e in events]

    def model_governance(self):
        from app.ml.runtime_loader import model_a_runtime
        from app.ml.features_hr import FEATURE_SET_B
        return {"model_a": {"status": model_a_runtime.status, "artifact_sha256": model_a_runtime.artifact_hash, "feature_count": len(FEATURE_SET_B), "threshold": 0.15, "threshold_policy": "PROVISIONAL_SYNTHETIC_PROTOTYPE_THRESHOLD_V1", "synthetic_prototype": True}, "engine_b": {"status": "INSTRUMENT_NOT_ACTIVATED", "training_status": "NOT_TRAINED"}, "model_c": {"rules_version": "v1.1-truthful-source", "type": "DETERMINISTIC_EVIDENCE_CONVERGENCE"}}
