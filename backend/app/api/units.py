import uuid
from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.security.deps import get_current_user
from app.security.scope import require_unit
from app.repositories.unit_repository import UnitRepository

router = APIRouter(prefix="/api/v1/units", tags=["units"])


@router.get("")
async def list_active_units(
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = UnitRepository(db)
    role = current_user.get("role")
    if role == "ADMIN":
        units = await repo.list_active_units()
    else:
        if role in ("COMMANDER", "WELFARE_OFFICER"):
            unit_id = require_unit(current_user)
        else:
            raw_unit_id = current_user.get("unit_id")
            if not raw_unit_id:
                raise HTTPException(403, "Unit scope is not configured")
            unit_id = uuid.UUID(raw_unit_id)
        unit = await repo.get_by_id(unit_id)
        units = [unit] if unit and unit.is_active else []
    return [
        {
            "id": str(u.id),
            "unit_code": u.unit_code,
            "unit_name": u.unit_name,
            "unit_type": u.unit_type,
            "location_label": u.location_label,
            "sanctioned_strength": u.sanctioned_strength,
        }
        for u in units
    ]
