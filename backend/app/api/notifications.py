"""Authenticated recipient notification projections."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.security.deps import get_db_with_rls
from app.services.notification_service import NotificationService


router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("")
async def list_notifications(db: AsyncSession = Depends(get_db_with_rls)):
    return await NotificationService(db).list()


@router.get("/unread-count")
async def unread_count(db: AsyncSession = Depends(get_db_with_rls)):
    return {"unread_count": await NotificationService(db).unread_count()}


@router.get("/{notification_id}")
async def notification_detail(notification_id: uuid.UUID, db: AsyncSession = Depends(get_db_with_rls)):
    row = await NotificationService(db).detail(notification_id)
    if row is None:
        raise HTTPException(404, "Notification not found")
    return row


@router.post("/{notification_id}/read")
async def mark_notification_read(notification_id: uuid.UUID, db: AsyncSession = Depends(get_db_with_rls)):
    return await NotificationService(db).mark_read(notification_id)
