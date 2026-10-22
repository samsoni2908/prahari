import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Literal
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.security.deps import get_current_user, require_roles
from app.security.scope import require_unit
from app.repositories.unit_repository import UnitRepository
from app.repositories.personnel_repository import PersonnelRepository
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.operational_repository import OperationalRepository
from app.repositories.scenario_repository import ScenarioRepository
from app.repositories.audit_repository import AuditRepository
from app.services.commander_service import CommanderService
from app.services.scenario_service import ScenarioService
from app.services.implementation_service import ImplementationService
from app.services.verify_service import VerifyService

router = APIRouter(
    prefix="/api/v1/commander",
    tags=["commander"],
    dependencies=[Depends(require_roles("COMMANDER"))],
)


class CreateScenarioRequest(BaseModel):
    model_config = {"extra": "forbid"}
    unit_id: Optional[str] = None
    scenario_name: Optional[str] = None
    target_reduction_percent: float = 15.0
    cutoff: Optional[datetime] = None
    idempotency_key: Optional[str] = None


class DecisionRequest(BaseModel):
    model_config = {"extra": "forbid"}
    decision: str
    reason: str
    expected_revision: Optional[str] = None
    idempotency_key: Optional[str] = None
    target_reduction_percent: Optional[float] = Field(default=None, ge=0, le=100)


class OutcomeRequest(BaseModel):
    model_config = {"extra": "forbid"}
    synthetic_replay_clock: Optional[datetime] = None


class OutcomeReviewRequest(BaseModel):
    model_config = {"extra": "forbid"}
    expected_revision: str
    review_note: str


class ImplementationAssignment(BaseModel):
    model_config = {"extra": "forbid"}
    shift_id: uuid.UUID
    personnel_id: uuid.UUID


class ImplementationRequest(BaseModel):
    model_config = {"extra": "forbid"}
    approval_id: uuid.UUID
    result: Literal["IMPLEMENTED", "NOT_IMPLEMENTED"]
    expected_revision: str
    effective_at: Optional[datetime] = None
    actual_assignments: Optional[List[ImplementationAssignment]] = None
    confirm_approved_assignments: bool = False
    external_reference: Optional[str] = None
    reason_code: Optional[str] = None
    synthetic_replay_clock: Optional[datetime] = None


def _get_services(db: AsyncSession):
    require_unit(db.info.get("actor", {}))
    unit_repo = UnitRepository(db)
    personnel_repo = PersonnelRepository(db)
    analytics_repo = AnalyticsRepository(db)
    op_repo = OperationalRepository(db)
    audit_repo = AuditRepository(db)
    scenario_repo = ScenarioRepository(db)

    cmd_service = CommanderService(
        unit_repo=unit_repo,
        personnel_repo=personnel_repo,
        analytics_repo=analytics_repo,
        operational_repo=op_repo,
        audit_repo=audit_repo,
    )
    scen_service = ScenarioService(
        scenario_repo=scenario_repo,
        unit_repo=unit_repo,
        analytics_repo=analytics_repo,
        personnel_repo=personnel_repo,
        audit_repo=audit_repo,
    )
    return cmd_service, scen_service, unit_repo


@router.get("/overview")
async def get_overview(
    unit_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    cmd_service, _, unit_repo = _get_services(db)

    target_unit_id = str(require_unit(current_user, unit_id))

    try:
        return await cmd_service.get_unit_overview(uuid.UUID(target_unit_id))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail="Operation failed")


@router.get("/unit")
async def get_unit_details(
    unit_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    cmd_service, _, unit_repo = _get_services(db)
    target_unit_id = str(require_unit(current_user, unit_id))
    unit = await unit_repo.get_by_id(uuid.UUID(target_unit_id))
    if not unit:
        raise HTTPException(status_code=404, detail="Unit not found")
    return unit


@router.get("/unit/stats")
async def get_unit_stats(
    unit_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    overview = await get_overview(unit_id=unit_id, current_user=current_user, db=db)
    return overview.get("kpis", {})


@router.get("/unit/deployments")
async def get_unit_deployments(
    unit_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    cmd_service, _, unit_repo = _get_services(db)
    target_unit_id = str(require_unit(current_user, unit_id))
    return await cmd_service.get_unit_deployments(uuid.UUID(target_unit_id))


@router.get("/unit/leave")
async def get_unit_leave(
    unit_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    cmd_service, _, unit_repo = _get_services(db)
    target_unit_id = str(require_unit(current_user, unit_id))
    return await cmd_service.get_unit_leave(uuid.UUID(target_unit_id))


@router.get("/unit/workload")
async def get_unit_workload(
    unit_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    cmd_service, _, unit_repo = _get_services(db)
    target_unit_id = str(require_unit(current_user, unit_id))
    return await cmd_service.get_unit_workload(uuid.UUID(target_unit_id))


@router.get("/unit/risk-trends")
async def get_unit_risk_trends(
    unit_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    cmd_service, _, unit_repo = _get_services(db)
    target_unit_id = str(require_unit(current_user, unit_id))
    return await cmd_service.get_unit_risk_trends(uuid.UUID(target_unit_id))


@router.get("/priority-list")
async def get_priority_list(
    unit_id: Optional[str] = None,
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    query: Optional[str] = Query(None, min_length=1, max_length=150),
    status_filter: Optional[Literal["Critical", "Elevated", "Moderate", "Normal", "NOT_COMPUTED"]] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    cmd_service, _, unit_repo = _get_services(db)

    target_unit_id = str(require_unit(current_user, unit_id))

    try:
        return await cmd_service.get_priority_list(uuid.UUID(target_unit_id), limit, offset, query, status_filter)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail="Operation failed")


@router.get("/strain-card/{personnel_id}")
async def get_strain_card(
    personnel_id: str,
    db: AsyncSession = Depends(get_db, scope="function"),
):
    cmd_service, _, _ = _get_services(db)
    try:
        card = await cmd_service.get_strain_card(uuid.UUID(personnel_id))
        if not card:
            raise HTTPException(status_code=404, detail="Personnel not found")
        return card
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid personnel UUID format")


@router.post("/scenarios")
async def create_scenario(
    req: CreateScenarioRequest,
    idempotency_key_header: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    _, scen_service, unit_repo = _get_services(db)

    target_unit_id = str(require_unit(current_user, req.unit_id))

    user_id = current_user.get("user_id") or current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID missing")

    try:
        result = await scen_service.create_what_if_scenario(
            unit_id=uuid.UUID(target_unit_id),
            created_by_user_id=uuid.UUID(user_id),
            scenario_name=req.scenario_name,
            target_reduction_percent=req.target_reduction_percent,
            cutoff=req.cutoff or datetime.now(timezone.utc),
            idempotency_key=idempotency_key_header or req.idempotency_key,
        )
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail="Operation failed")


@router.get("/scenarios")
async def list_scenarios(
    unit_id: Optional[str] = None,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    _, scen_service, unit_repo = _get_services(db)
    target_unit_id = str(require_unit(current_user, unit_id))

    return await scen_service.list_scenarios(uuid.UUID(target_unit_id))


@router.get("/scenarios/{scenario_id}")
async def get_scenario(
    scenario_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    _, scen_service, _ = _get_services(db)
    scenario = await scen_service.get_scenario(uuid.UUID(scenario_id))
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    require_unit(current_user, scenario.get("unit_id"))
    return scenario


@router.get("/scenarios/{scenario_id}/comparison")
async def get_scenario_comparison(
    scenario_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    _, scen_service, _ = _get_services(db)
    scenario = await scen_service.get_scenario(uuid.UUID(scenario_id))
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    require_unit(current_user, scenario.get("unit_id"))
    return await scen_service.get_comparison(uuid.UUID(scenario_id))


@router.post("/scenarios/{scenario_id}/decide")
async def decide_scenario(
    scenario_id: str,
    req: DecisionRequest,
    idempotency_key_header: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    _, scen_service, _ = _get_services(db)
    user_id = current_user.get("user_id") or current_user.get("sub")
    try:
        return await scen_service.record_decision(
            scenario_id=uuid.UUID(scenario_id),
            user_id=uuid.UUID(user_id),
            decision=req.decision,
            reason=req.reason,
            expected_revision=req.expected_revision,
            idempotency_key=idempotency_key_header or req.idempotency_key,
            target_reduction_percent=req.target_reduction_percent,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail="Operation failed")


@router.post("/scenarios/{scenario_id}/outcome")
async def record_outcome(
    scenario_id: str,
    db: AsyncSession = Depends(get_db, scope="function"),
):
    raise HTTPException(410, "Human-entered outcome metrics are no longer accepted")


@router.get("/scenarios/{scenario_id}/outcomes")
async def get_scenario_outcome(scenario_id: uuid.UUID, db: AsyncSession = Depends(get_db, scope="function")):
    return await VerifyService(db).get(scenario_id)


@router.post("/scenarios/{scenario_id}/outcomes/observe")
async def observe_scenario_outcome(
    scenario_id: uuid.UUID,
    req: OutcomeRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    return await VerifyService(db).observe(scenario_id, req.synthetic_replay_clock)


@router.post("/scenarios/{scenario_id}/outcomes/review")
async def review_scenario_outcome(
    scenario_id: uuid.UUID,
    req: OutcomeReviewRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    return await VerifyService(db).review(scenario_id, req.expected_revision, req.review_note)


@router.post("/scenarios/{scenario_id}/implementation")
async def record_implementation(
    scenario_id: uuid.UUID,
    req: ImplementationRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db, scope="function"),
):
    assignments = [entry.model_dump(mode="json") for entry in req.actual_assignments] if req.actual_assignments is not None else None
    return await ImplementationService(db).record(
        scenario_id, req.approval_id, req.result, req.expected_revision,
        idempotency_key, req.effective_at, assignments, req.external_reference,
        req.reason_code, req.synthetic_replay_clock, req.confirm_approved_assignments,
    )
