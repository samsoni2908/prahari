"""Typed, bounded operational review API."""
from typing import Literal
from uuid import UUID
from fastapi import APIRouter, Depends, Header, Query
from app.security.deps import get_db_with_rls, require_roles
from app.schemas.alerts import AlertAction, AlertPage, AlertView
from app.services.alert_service import AlertService

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"],
    dependencies=[Depends(require_roles("COMMANDER", "WELFARE_OFFICER"))])


@router.get("", response_model=AlertPage)
async def list_alerts(limit: int = Query(50, ge=1, le=200), cursor: str | None = Query(None, max_length=1024),
    status: Literal["OPEN", "ACKNOWLEDGED", "RESOLVED"] | None = None,
    db=Depends(get_db_with_rls, scope="function")):
    return await AlertService(db).list(limit, cursor, status)


@router.post("/{alert_id}/acknowledge", response_model=AlertView)
async def acknowledge(alert_id: UUID, body: AlertAction,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
    db=Depends(get_db_with_rls, scope="function")):
    return await AlertService(db).action(alert_id, body, idempotency_key, "ACKNOWLEDGED")


@router.post("/{alert_id}/resolve", response_model=AlertView)
async def resolve(alert_id: UUID, body: AlertAction,
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
    db=Depends(get_db_with_rls, scope="function")):
    return await AlertService(db).action(alert_id, body, idempotency_key, "RESOLVED")
