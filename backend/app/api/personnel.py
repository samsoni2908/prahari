import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.security.deps import get_current_user, require_roles, get_db_with_rls
from app.repositories.personnel_repository import PersonnelRepository
from app.repositories.unit_repository import UnitRepository
from app.repositories.wellbeing_repository import WellbeingRepository
from app.repositories.analytics_repository import AnalyticsRepository
from app.repositories.operational_repository import OperationalRepository
from app.repositories.audit_repository import AuditRepository
from app.services.welfare_case_service import WelfareCaseService
from app.services.personnel_service import PersonnelService
from app.schemas.operational_analytics import OperationalAnalyticsView

router = APIRouter(
    prefix="/api/v1/personnel",
    tags=["personnel"],
    dependencies=[Depends(require_roles("PERSONNEL"))],
)


class ConsentRequest(BaseModel):
    model_config = {"extra": "forbid"}
    action: str  # "CONSENT" or "WITHDRAW"
    purpose: Optional[str] = "Voluntary confidential personnel wellbeing self-reflection"


class SelfCheckRequest(BaseModel):
    model_config = {"extra": "forbid"}
    answers: Dict[str, Any]
    instrument_name: Optional[str] = "WELLBEING_SELF_CHECK_V2"


class SupportRequestInput(BaseModel):
    model_config = {"extra": "forbid"}
    request_type: str
    priority: str = "NORMAL"
    details: str


def _get_personnel_service(db: AsyncSession):
    return PersonnelService(
        personnel_repo=PersonnelRepository(db),
        unit_repo=UnitRepository(db),
        wellbeing_repo=WellbeingRepository(db),
        analytics_repo=AnalyticsRepository(db),
        operational_repo=OperationalRepository(db),
        audit_repo=AuditRepository(db),
    )


def _get_target_personnel_id(current_user: Dict[str, Any]) -> uuid.UUID:
    pid = current_user.get("personnel_id")
    if not pid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No personnel profile linked to this user account",
        )
    return uuid.UUID(pid)


@router.get("/profile")
@router.get("/me")
async def get_profile(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_rls, scope="function"),
):
    service = _get_personnel_service(db)
    pid = _get_target_personnel_id(current_user)
    profile = await service.get_profile(pid)
    if not profile:
        raise HTTPException(status_code=404, detail="Personnel profile not found")
    return profile


@router.get("/me/deployments")
async def get_my_deployments(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_rls, scope="function"),
):
    service = _get_personnel_service(db)
    pid = _get_target_personnel_id(current_user)
    return await service.get_deployments(pid)


@router.get("/me/duties")
async def get_my_duties(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_rls, scope="function"),
):
    service = _get_personnel_service(db)
    pid = _get_target_personnel_id(current_user)
    return await service.get_duties(pid)


@router.get("/me/leave")
async def get_my_leave(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_rls, scope="function"),
):
    service = _get_personnel_service(db)
    pid = _get_target_personnel_id(current_user)
    return await service.get_leave(pid)


@router.get("/me/risk", response_model=OperationalAnalyticsView)
async def get_my_risk(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_rls, scope="function"),
):
    service = _get_personnel_service(db)
    pid = _get_target_personnel_id(current_user)
    return await service.get_risk(pid)


@router.get("/me/rest")
async def get_my_rest(limit: int = Query(30, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_rls, scope="function")):
    return await _get_personnel_service(db).get_rest(_get_target_personnel_id(current_user), limit)


@router.get("/me/wellbeing")
async def get_my_wellbeing(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_rls, scope="function"),
):
    service = _get_personnel_service(db)
    pid = _get_target_personnel_id(current_user)
    consent = await service.get_consent(pid)
    checks = await service.list_self_checks(pid)
    derived = await service.list_wellbeing_results(pid)
    return {
        "consent": consent,
        "history": checks,
        "derived_results": derived,
        "current_governed_wellbeing": {
            "status": "INSTRUMENT_NOT_ACTIVATED",
            "attention_category": "UNAVAILABLE",
            "trend_direction": "INSUFFICIENT_GOVERNED_HISTORY",
            "notes": "No clinical questionnaire is currently activated under PRAHARI Engine-B.",
        },
    }


@router.post("/me/wellbeing")
async def submit_my_wellbeing(
    req: SelfCheckRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_rls, scope="function"),
):
    service = _get_personnel_service(db)
    pid = _get_target_personnel_id(current_user)
    try:
        return await service.submit_self_check(
            personnel_id=pid,
            answers=req.answers,
            instrument_name=req.instrument_name,
        )
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Request could not be completed")



@router.get("/consent")
async def get_consent(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_rls, scope="function"),
):
    service = _get_personnel_service(db)
    pid = _get_target_personnel_id(current_user)
    return await service.get_consent(pid)


@router.post("/consent")
async def update_consent(
    req: ConsentRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_rls, scope="function"),
):
    service = _get_personnel_service(db)
    pid = _get_target_personnel_id(current_user)
    return await service.update_consent(pid, action=req.action, purpose=req.purpose)


@router.post("/self-check")
async def submit_self_check(
    req: SelfCheckRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_rls, scope="function"),
):
    service = _get_personnel_service(db)
    pid = _get_target_personnel_id(current_user)
    try:
        return await service.submit_self_check(
            personnel_id=pid,
            answers=req.answers,
            instrument_name=req.instrument_name,
        )
    except PermissionError as pe:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(pe))
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Request could not be completed")


@router.get("/self-checks")
async def list_self_checks(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_rls, scope="function"),
):
    service = _get_personnel_service(db)
    pid = _get_target_personnel_id(current_user)
    return await service.list_self_checks(pid)


@router.post("/support-request")
async def create_support_request(
    req: SupportRequestInput,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_rls, scope="function"),
):
    service = _get_personnel_service(db)
    pid = _get_target_personnel_id(current_user)
    return await service.create_support_request(
        personnel_id=pid,
        request_type=req.request_type,
        priority=req.priority,
        details=req.details,
        idempotency_key=idempotency_key,
    )


@router.get("/support-requests")
async def list_support_requests(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_rls, scope="function"),
):
    service = _get_personnel_service(db)
    pid = _get_target_personnel_id(current_user)
    return await service.list_support_requests(pid)


@router.get("/support-requests/{request_id}/actions")
async def own_support_actions(request_id: uuid.UUID, db: AsyncSession = Depends(get_db_with_rls, scope="function")):
    return await WelfareCaseService(db).list_actions(request_id)


class WithdrawSupportInput(BaseModel):
    model_config = {"extra": "forbid"}
    reason_code: str


@router.post("/support-requests/{request_id}/withdraw")
async def withdraw_support_request(request_id: uuid.UUID, req: WithdrawSupportInput,
                                   db: AsyncSession = Depends(get_db_with_rls, scope="function")):
    return await WelfareCaseService(db).withdraw(request_id, req.reason_code)


@router.get("/privacy-history")
async def get_privacy_history(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_rls, scope="function"),
):
    service = _get_personnel_service(db)
    pid = _get_target_personnel_id(current_user)
    return await service.get_privacy_history(pid)
