from typing import AsyncGenerator, Optional
from uuid import UUID
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from fastapi import Request
from app.config import settings
import app.security.scope  # Register query/write scope enforcement.

# Create async engine for PostgreSQL 16
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    hide_parameters=True,
    future=True,
    pool_pre_ping=True,
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides an asynchronous database session."""
    async with AsyncSessionLocal() as session:
        session.info["actor"] = getattr(request.state, "actor", None)
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def set_rls_context(
    session: AsyncSession,
    user_id: Optional[UUID | str] = None,
    role: Optional[str] = None,
    unit_id: Optional[UUID | str] = None,
) -> None:
    """
    Formalized RLS session context convention:
    Sets transaction-scoped PostgreSQL settings via SET LOCAL inside the current transaction.
    These are derived server-side from authenticated token context, never directly from untrusted input.
    """
    if user_id:
        await session.execute(
            text("SELECT set_config('app.current_user_id', :val, true)"),
            {"val": str(user_id)},
        )
    if role:
        await session.execute(
            text("SELECT set_config('app.current_role', :val, true)"),
            {"val": str(role)},
        )
    if unit_id:
        await session.execute(
            text("SELECT set_config('app.current_unit_id', :val, true)"),
            {"val": str(unit_id)},
        )
