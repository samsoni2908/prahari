import uuid
from datetime import date
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from typing import Literal
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.security.deps import get_current_user, require_roles, get_db_with_rls
from app.repositories.wellbeing_repository import WellbeingRepository
from app.repositories.personnel_repository import PersonnelRepository
from app.repositories.unit_repository import UnitRepository
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.operational_repository import OperationalRepository
from app.repositories.audit_repository import AuditRepository
from app.services.welfare_service import WelfareService
from app.services.welfare_case_service import WelfareCaseService
from app.services.welfare_intake_service import WelfareIntakeService
from app.schemas.welfare_intake import NamedSearch, NamedSearchResult, OpenCase, OpenedCase


router = APIRouter(
    prefix="/api/v1/welfare",
    tags=["welfare"],
    dependencies=[Depends(require_roles("WELFARE_OFFICER"))],
)


class DraftScenarioRequest(BaseModel):
    model_config = {"extra": "forbid"}
    unit_id: Optional[str] = None
    scenario_name: Optional[str] = None
    target_reduction_percent: float = 15.0
    idempotency_key: Optional[str] = None


class UpdateCaseRequest(BaseModel):
    model_config = {"extra": "forbid"}
    status: str
    follow_up_date: Optional[date] = None
    notes: Optional[str] = None


class ClaimCaseRequest(BaseModel):
    model_config = {"extra": "forbid"}
    reason: str


class CaseActionRequest(BaseModel):
    model_config = {"extra": "forbid"}
    action_type: str
    note: Optional[str] = None
    visibility: str = "OFFICER"
    follow_up_date: Optional[date] = None
    case_status: Optional[str] = None


class CasePriorityRequest(BaseModel):
    model_config = {"extra": "forbid"}
    priority: str
    reason: str


class CaseReassignRequest(BaseModel):
    model_config = {"extra": "forbid"}
    target_officer_user_id: uuid.UUID
    reason: str


class RecordActionRequest(BaseModel):
    model_config = {"extra": "forbid"}
    action_type: str  # "MONITOR" | "CONTACT_PERSONNEL" | "WELFARE_FOLLOWUP" | "RECORD_OUTCOME"
    details: str
    notes: Optional[str] = None
    follow_up_date: Optional[date] = None
    outcome: Optional[str] = None


def _get_welfare_service(db: AsyncSession):
    return WelfareService(
        wellbeing_repo=WellbeingRepository(db),
        personnel_repo=PersonnelRepository(db),
        unit_repo=UnitRepository(db),
        analytics_repo=AnalyticsRepository(db),
        audit_repo=AuditRepository(db),
        operational_repo=OperationalRepository(db),
    )


@router.get("/personnel/search")
async def search_personnel(
    query: Optional[str] = None,
    risk_filter: Optional[str] = None,
    unit_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db_with_rls, scope="function"),
):
    service = _get_welfare_service(db)
    u_uuid = uuid.UUID(unit_id) if unit_id else None
    return await service.search_personnel(query=query, risk_filter=risk_filter, unit_id=u_uuid)


@router.post("/personnel/search", response_model=NamedSearchResult)
async def named_case_search(body: NamedSearch, db=Depends(get_db_with_rls, scope="function")):
    return await WelfareIntakeService(db).search(body)


@router.post("/cases", response_model=OpenedCase)
async def open_case(body: OpenCase,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
    db=Depends(get_db_with_rls, scope="function")):
    return await WelfareIntakeService(db).open(body, idempotency_key)


@router.get("/personnel/{personnel_id}")
async def get_personnel_profile(
    personnel_id: str,
    db: AsyncSession = Depends(get_db_with_rls, scope="function"),
):
    service = _get_welfare_service(db)
    try:
        profile = await service.get_personnel_profile(uuid.UUID(personnel_id))
        if not profile:
            raise HTTPException(status_code=404, detail="Personnel profile not found")
        return profile
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")


@router.get("/personnel/{personnel_id}/history")
async def get_personnel_history(
    personnel_id: str,
    db: AsyncSession = Depends(get_db_with_rls, scope="function"),
):
    service = _get_welfare_service(db)
    profile = await service.get_personnel_profile(uuid.UUID(personnel_id))
    if not profile:
        raise HTTPException(status_code=404, detail="Personnel not found")
    return {
        "service_history": profile["service_history"],
        "deployment": profile["deployment"],
        "leave_and_rest": profile["leave_and_rest"],
        "training": profile["training"],
    }


@router.get("/personnel/{personnel_id}/risk")
async def get_personnel_risk(
    personnel_id: str,
    db: AsyncSession = Depends(get_db_with_rls, scope="function"),
):
    service = _get_welfare_service(db)
    profile = await service.get_personnel_profile(uuid.UUID(personnel_id))
    if not profile:
        raise HTTPException(status_code=404, detail="Personnel not found")
    return profile["risk_analysis"]


@router.get("/personnel/{personnel_id}/wellbeing")
async def get_personnel_wellbeing(
    personnel_id: str,
    db: AsyncSession = Depends(get_db_with_rls, scope="function"),
):
    service = _get_welfare_service(db)
    profile = await service.get_personnel_profile(uuid.UUID(personnel_id))
    if not profile:
        raise HTTPException(status_code=404, detail="Personnel not found")
    return profile["wellbeing"]


@router.get("/personnel/{personnel_id}/factors")
async def get_personnel_factors(
    personnel_id: str,
    db: AsyncSession = Depends(get_db_with_rls, scope="function"),
):
    service = _get_welfare_service(db)
    profile = await service.get_personnel_profile(uuid.UUID(personnel_id))
    if not profile:
        raise HTTPException(status_code=404, detail="Personnel not found")
    return profile["risk_analysis"]["contributing_factors"]


@router.post("/personnel/{personnel_id}/actions")
async def record_welfare_action(
    personnel_id: str,
    req: RecordActionRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_rls, scope="function"),
):
    service = _get_welfare_service(db)
    user_id = current_user.get("user_id") or current_user.get("sub")
    try:
        return await service.record_welfare_action(
            personnel_id=uuid.UUID(personnel_id),
            officer_user_id=uuid.UUID(user_id),
            action_type=req.action_type,
            details=req.details,
            notes=req.notes,
            follow_up_date=req.follow_up_date,
            outcome=req.outcome,
            idempotency_key=idempotency_key,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid UUID format")



@router.get("/cases")
async def list_cases(
    status: Optional[Literal["OPEN", "ASSIGNED", "IN_PROGRESS", "CLOSED", "WITHDRAWN"]] = None,
    limit: int = Query(100, ge=1, le=200),
    offset: int = Query(0, ge=0),
    query: Optional[str] = Query(None, min_length=1, max_length=150),
    assigned_to_me: bool = False,
    db: AsyncSession = Depends(get_db_with_rls, scope="function"),
):
    service = _get_welfare_service(db)
    return await service.list_cases(status_filter=status, limit=limit, offset=offset, query=query, assigned_to_me=assigned_to_me)


@router.get("/cases/{request_id}")
async def get_case_detail(
    request_id: str,
    db: AsyncSession = Depends(get_db_with_rls, scope="function"),
):
    service = _get_welfare_service(db)
    try:
        case = await service.get_case_detail(uuid.UUID(request_id))
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        return case
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request UUID format")


@router.post("/cases/{request_id}/assign")
async def claim_case(request_id: uuid.UUID, req: ClaimCaseRequest,
                     idempotency_key: str = Header(..., alias="Idempotency-Key"),
                     db: AsyncSession = Depends(get_db_with_rls, scope="function")):
    return await WelfareCaseService(db).claim(
        request_id, req.reason, idempotency_key,
    )


@router.post("/cases/{request_id}/actions")
async def append_case_action(request_id: uuid.UUID, req: CaseActionRequest,
                             idempotency_key: str = Header(..., alias="Idempotency-Key"),
                             db: AsyncSession = Depends(get_db_with_rls, scope="function")):
    return await WelfareCaseService(db).action(
        request_id, req.action_type, req.note, req.visibility,
        req.follow_up_date, req.case_status, idempotency_key,
    )


@router.get("/cases/{request_id}/actions")
async def list_case_actions(request_id: uuid.UUID, db: AsyncSession = Depends(get_db_with_rls, scope="function")):
    return await WelfareCaseService(db).list_actions(request_id)


@router.post("/cases/{request_id}/priority")
async def set_case_priority(request_id: uuid.UUID, req: CasePriorityRequest,
                            idempotency_key: str = Header(..., alias="Idempotency-Key"),
                            db: AsyncSession = Depends(get_db_with_rls, scope="function")):
    return await WelfareCaseService(db).set_priority(
        request_id, req.priority, req.reason, idempotency_key,
    )


@router.post("/cases/{request_id}/reassign")
async def reassign_case(request_id: uuid.UUID, req: CaseReassignRequest,
                        idempotency_key: str = Header(..., alias="Idempotency-Key"),
                        db: AsyncSession = Depends(get_db_with_rls, scope="function")):
    return await WelfareCaseService(db).reassign(
        request_id, req.target_officer_user_id, req.reason, idempotency_key,
    )


@router.patch("/cases/{request_id}")
async def update_case(
    request_id: str,
    req: UpdateCaseRequest,
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_rls, scope="function"),
):
    service = _get_welfare_service(db)
    user_id = current_user.get("user_id") or current_user.get("sub")
    try:
        updated = await service.update_case(
            request_id=uuid.UUID(request_id),
            officer_user_id=uuid.UUID(user_id),
            status=req.status,
            follow_up_date=req.follow_up_date,
            notes=req.notes,
            idempotency_key=idempotency_key,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Case not found")
        return updated
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid request UUID format")


@router.post("/scenarios/draft")
async def create_welfare_draft_scenario(
    req: DraftScenarioRequest,
    idempotency_key_header: Optional[str] = Header(None, alias="Idempotency-Key"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_rls, scope="function"),
):
    from app.security.scope import require_unit
    from app.repositories.scenario_repository import ScenarioRepository
    from app.services.scenario_service import ScenarioService

    target_unit_id = str(require_unit(current_user, req.unit_id))
    user_id = current_user.get("user_id") or current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID missing")

    scenario_repo = ScenarioRepository(db)
    unit_repo = UnitRepository(db)
    analytics_repo = AnalyticsRepository(db)
    personnel_repo = PersonnelRepository(db)
    audit_repo = AuditRepository(db)

    scen_service = ScenarioService(
        scenario_repo=scenario_repo,
        unit_repo=unit_repo,
        analytics_repo=analytics_repo,
        personnel_repo=personnel_repo,
        audit_repo=audit_repo,
    )

    try:
        return await scen_service.create_what_if_scenario(
            unit_id=uuid.UUID(target_unit_id),
            created_by_user_id=uuid.UUID(user_id),
            scenario_name=req.scenario_name,
            target_reduction_percent=req.target_reduction_percent,
            idempotency_key=idempotency_key_header or req.idempotency_key,
            is_welfare_draft=True,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail="Operation failed")
