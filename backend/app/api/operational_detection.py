"""Two detection entry points; mutations remain governance-only."""
from datetime import date
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import create_engine
from app.config import settings
from app.security.deps import get_current_user, require_roles
from app.services.operational_attention_service import OperationalAttentionService

router=APIRouter(prefix="/api/v1",tags=["operational-detection"])


class HistoricalRun(BaseModel):
    model_config=ConfigDict(extra="forbid")
    cutoff: date
    unit_id: Optional[UUID]=None


def service():
    # Dedicated bounded operation; engine is disposed by each route.
    return OperationalAttentionService(create_engine(settings.DATABASE_URL_SYNC,hide_parameters=True,pool_pre_ping=True))


@router.post("/admin/operational-runs")
def historical_run(body:HistoricalRun, actor=Depends(require_roles("ADMIN")),
                   idempotency_key:str=Header(...,alias="Idempotency-Key",min_length=8,max_length=128)):
    svc=service()
    try:
        return svc.run(body.cutoff,actor=actor,unit_id=body.unit_id,request_key=idempotency_key)
    except PermissionError:
        raise HTTPException(403,"Operation not permitted") from None
    except ValueError:
        raise HTTPException(409,"Operational request conflict") from None
    finally:
        svc.engine.dispose()


@router.get("/operational/attention")
def operational_attention(actor=Depends(get_current_user),cutoff:Optional[date]=None,
                          limit:int=Query(50,ge=1,le=200),cursor:Optional[UUID]=None):
    svc=service()
    try:
        return svc.project(actor,cutoff,limit,cursor)
    except PermissionError:
        raise HTTPException(403,"Operation not permitted") from None
    finally:
        svc.engine.dispose()
