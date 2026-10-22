import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from typing import Literal
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.security.deps import require_roles
from app.repositories.user_repository import UserRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.personnel_repository import PersonnelRepository
from app.repositories.unit_repository import UnitRepository
from app.services.admin_service import AdminService
from app.services.personnel_transfer_service import PersonnelTransferService

router = APIRouter(
    prefix="/api/v1/admin",
    tags=["admin"],
    dependencies=[Depends(require_roles("ADMIN"))],
)


class CreateUserRequest(BaseModel):
    model_config = {"extra": "forbid"}
    username: str
    password: str
    role: str
    unit_id: Optional[str] = None
    personnel_id: Optional[str] = None


class UpdateUserRequest(BaseModel):
    model_config = {"extra": "forbid"}
    is_active: Optional[bool] = None
    role: Optional[str] = None


class TransferPersonnelRequest(BaseModel):
    model_config = {"extra": "forbid"}
    target_unit_id: uuid.UUID
    reason_code: str


@router.post("/personnel/{personnel_id}/transfer")
async def transfer_personnel(personnel_id: uuid.UUID, req: TransferPersonnelRequest,
                             db: AsyncSession = Depends(get_db, scope="function")):
    return await PersonnelTransferService(db).transfer(
        personnel_id, req.target_unit_id, req.reason_code,
    )


def _get_admin_service(db: AsyncSession):
    return AdminService(
        user_repo=UserRepository(db),
        audit_repo=AuditRepository(db),
        personnel_repo=PersonnelRepository(db),
        unit_repo=UnitRepository(db),
    )


@router.get("/health")
async def get_system_health(db: AsyncSession = Depends(get_db, scope="function")):
    service = _get_admin_service(db)
    return await service.get_system_health()


@router.get("/users")
async def list_users(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    query: Optional[str] = Query(None, min_length=1, max_length=150),
    role: Optional[Literal["PERSONNEL", "COMMANDER", "WELFARE_OFFICER", "ADMIN"]] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db, scope="function"),
):
    service = _get_admin_service(db)
    return await service.list_users(limit=limit, offset=offset, query=query, role=role, is_active=is_active)


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(
    req: CreateUserRequest,
    db: AsyncSession = Depends(get_db, scope="function"),
):
    service = _get_admin_service(db)
    try:
        u_uuid = uuid.UUID(req.unit_id) if req.unit_id else None
        p_uuid = uuid.UUID(req.personnel_id) if req.personnel_id else None
        return await service.create_user(
            username=req.username,
            password_clear=req.password,
            role=req.role,
            unit_id=u_uuid,
            personnel_id=p_uuid,
        )
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    req: UpdateUserRequest,
    db: AsyncSession = Depends(get_db, scope="function"),
):
    service = _get_admin_service(db)
    try:
        updated = await service.update_user(
            user_id=uuid.UUID(user_id),
            is_active=req.is_active,
            role=req.role,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="User not found")
        return updated
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID format")


@router.get("/personnel")
async def list_personnel(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    query: Optional[str] = Query(None, min_length=1, max_length=150),
    unit_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db, scope="function"),
):
    service = _get_admin_service(db)
    return await service.list_personnel(limit=limit, offset=offset, query=query, unit_id=unit_id)


@router.get("/units")
async def list_units(limit: int = Query(100, ge=1, le=200), offset: int = Query(0, ge=0),
                     query: Optional[str] = Query(None, min_length=1, max_length=150),
                     is_active: Optional[bool] = None, db: AsyncSession = Depends(get_db, scope="function")):
    service = _get_admin_service(db)
    return await service.list_units(limit, offset, query, is_active)


@router.get("/policies")
async def list_policies(db: AsyncSession = Depends(get_db, scope="function")):
    service = _get_admin_service(db)
    return await service.list_policies()


@router.get("/audit")
async def list_audit_metadata(limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), db: AsyncSession = Depends(get_db, scope="function")):
    return await _get_admin_service(db).list_audit_metadata(limit, offset)


@router.get("/models")
async def model_governance(db: AsyncSession = Depends(get_db, scope="function")):
    return _get_admin_service(db).model_governance()
