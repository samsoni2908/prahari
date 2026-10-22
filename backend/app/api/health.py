from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from pathlib import Path
from alembic.config import Config
from alembic.script import ScriptDirectory

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """Confirms that the API process is running."""
    return {
        "status": "healthy",
        "service": "prahari-backend",
        "version": "0.1.0",
    }


@router.get("/ready")
async def ready_check(db: AsyncSession = Depends(get_db)):
    """Confirms that the API can successfully communicate with PostgreSQL 16."""
    try:
        result = await db.execute(text("SELECT 1"))
        if result.scalar() == 1:
            config = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
            heads = set(ScriptDirectory.from_config(config).get_heads())
            applied = await db.execute(text("SELECT version_num FROM alembic_version"))
            if set(applied.scalars().all()) != heads:
                raise HTTPException(503, "Migration compatibility unavailable")
            return {
                "status": "ready",
                "database": "connected",
                "service": "prahari-backend",
            }
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database readiness check returned unexpected response",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database unavailable",
        )
