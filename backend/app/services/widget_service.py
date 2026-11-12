import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.widget_settings import WidgetSettings
from app.schemas.widget import WidgetSettingsUpdate


async def get_widget_settings(
    db: AsyncSession, user_id: uuid.UUID
) -> WidgetSettings | None:
    result = await db.execute(
        select(WidgetSettings).where(WidgetSettings.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def get_widget_settings_by_id(
    db: AsyncSession, widget_id: uuid.UUID
) -> WidgetSettings | None:
    result = await db.execute(
        select(WidgetSettings).where(WidgetSettings.id == widget_id)
    )
    return result.scalar_one_or_none()


async def upsert_widget_settings(
    db: AsyncSession, user_id: uuid.UUID, data: WidgetSettingsUpdate
) -> WidgetSettings:
    existing = await get_widget_settings(db, user_id)
    if existing:
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(existing, field, value)
        await db.commit()
        await db.refresh(existing)
        return existing

    ws = WidgetSettings(
        user_id=user_id,
        enabled=data.enabled or False,
        title=data.title or "Chat with us",
        greeting=data.greeting or "Hi! How can I help you today?",
        primary_color=data.primary_color or "#2563eb",
        position=data.position or "right",
        show_branding=data.show_branding if data.show_branding is not None else True,
        allowed_domains=data.allowed_domains or [],
        whatsapp_phone_number_id=data.whatsapp_phone_number_id,
        whatsapp_access_token=data.whatsapp_access_token,
        messenger_page_id=data.messenger_page_id,
        messenger_access_token=data.messenger_access_token,
        webhook_verify_token=data.webhook_verify_token or "social-selling-verify-2026",
    )
    db.add(ws)
    await db.commit()
    await db.refresh(ws)
    return ws
