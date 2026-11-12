import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.models.widget_settings import WidgetSettings
from app.schemas.widget import (
    PublicWidgetConfig,
    WidgetSettingsResponse,
    WidgetSettingsUpdate,
)
from app.services import widget_service

router = APIRouter(prefix="/api/widget", tags=["widget"])


@router.get("/settings", response_model=WidgetSettingsResponse)
async def get_settings(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ws = await widget_service.get_widget_settings(db, current_user.id)
    if not ws:
        ws = WidgetSettings(user_id=current_user.id)
        db.add(ws)
        await db.commit()
        await db.refresh(ws)
    return ws


@router.put("/settings", response_model=WidgetSettingsResponse)
async def update_settings(
    data: WidgetSettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await widget_service.upsert_widget_settings(db, current_user.id, data)


@router.get("/config/{widget_id}", response_model=PublicWidgetConfig)
async def get_public_config(
    widget_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    ws = await widget_service.get_widget_settings_by_id(db, widget_id)
    if not ws or not ws.enabled:
        raise HTTPException(status_code=404, detail="Widget not found or disabled")

    user_result = await db.execute(
        select(User).where(User.id == ws.user_id)
    )
    user = user_result.scalar_one_or_none()
    company_name = user.company_name if user else None

    return PublicWidgetConfig(
        title=ws.title,
        greeting=ws.greeting,
        primary_color=ws.primary_color,
        position=ws.position,
        show_branding=ws.show_branding,
        company_name=company_name,
    )
