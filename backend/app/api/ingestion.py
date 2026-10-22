"""Admin operational intake and safe bounded execution history."""
from uuid import UUID
from typing import Literal
from fastapi import APIRouter, Depends, Header, Query, Request
from app.security.deps import get_db_with_rls, require_roles
from app.repositories.ingestion_repository import SOURCE_MODELS, IngestionRepository
from app.schemas.ingestion import Dataset, ImportInput, ImportCommit, ImportValidation, ImportResult
from app.services.ingestion_service import IngestionService

router = APIRouter(prefix="/api/v1/admin", tags=["operational-ingestion"],
    dependencies=[Depends(require_roles("ADMIN"))])


@router.get("/imports/templates")
async def templates():
    return {"max_rows":2000, "max_bytes":2_000_000, "datasets":[{
        "dataset_type":name, "fields":[{"name":c.name, "type":str(c.type),
            "required":not c.nullable and c.name != "id", "nullable":c.nullable}
            for c in model.__table__.columns if c.name != "created_at"]}
        for name,model in SOURCE_MODELS.items()]}


@router.post("/imports/validate", response_model=ImportValidation)
async def validate(body:ImportInput, db=Depends(get_db_with_rls, scope="function")):
    return await IngestionService(db).validate(body)


@router.post("/imports/{import_id}/commit", response_model=ImportResult)
async def commit(import_id:UUID, body:ImportCommit,
    idempotency_key:str=Header(..., alias="Idempotency-Key", min_length=8, max_length=128),
    db=Depends(get_db_with_rls, scope="function")):
    return await IngestionService(db).commit(import_id, body, idempotency_key)


def event_view(event):
    meta = event.metadata_json or {}
    status = {"IMPORT_VALIDATED":"VALIDATED", "IMPORT_REJECTED":"REJECTED", "IMPORT_COMMITTED":"COMMITTED"}.get(event.action)
    if status is None:
        status = "PARTIAL_FAILURE" if meta.get("failed", 0) else "COMPLETED_UNAVAILABLE" if meta.get("unavailable", 0) else "COMPLETED"
    return {"id":str(event.resource_id) if event.resource_id else str(event.id),
        "event":event.action, "status":status, "created_at":event.created_at,
        **{key:meta[key] for key in ("dataset_type","row_count","source_hash","source_timestamp",
            "cutoff","processed","valid","unavailable","failed","alerts_created","alerts_suppressed") if key in meta}}


@router.get("/imports")
async def history(limit:int=Query(50, ge=1, le=200), offset:int=Query(0, ge=0),
    dataset_type:Dataset|None=None, status:Literal["VALIDATED", "REJECTED", "COMMITTED"]|None=None,
    db=Depends(get_db_with_rls, scope="function")):
    rows = await IngestionRepository(db).history(limit+1, offset, dataset_type=dataset_type, status=status)
    return {"items":[event_view(row) for row in rows[:limit]], "next_offset":offset+limit if len(rows)>limit else None}


@router.get("/jobs")
async def jobs(request:Request, limit:int=Query(50, ge=1, le=200), offset:int=Query(0, ge=0),
    db=Depends(get_db_with_rls, scope="function")):
    rows = await IngestionRepository(db).history(limit+1, offset, jobs=True)
    scheduler = getattr(request.app.state, "operational_scheduler", None)
    return {"items":[event_view(row) for row in rows[:limit]], "next_offset":offset+limit if len(rows)>limit else None,
        "scheduler_cadence":"00:15 UTC", "status":"RECORDED" if rows else "NOT_COMPUTED",
        "scheduler_status":"RUNNING" if scheduler and scheduler.scheduler.running and scheduler.owner is not None else "NOT_RUNNING"}
