from typing import Any, Dict, List
from fastapi import APIRouter, Depends
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
    if current_user.get("role") in ("COMMANDER", "WELFARE_OFFICER"):
        require_unit(current_user)
    repo = UnitRepository(db)
    units = await repo.list_active_units()
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
