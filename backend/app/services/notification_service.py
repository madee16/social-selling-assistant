import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification


async def create_notification(
    db: AsyncSession,
    user_id: uuid.UUID,
    type: str,
    title: str,
    message: str | None = None,
    link: str | None = None,
) -> Notification:
    notif = Notification(
        user_id=user_id, type=type, title=title, message=message, link=link
    )
    db.add(notif)
    await db.commit()
    await db.refresh(notif)
    return notif


async def list_notifications(
    db: AsyncSession, user_id: uuid.UUID, limit: int = 20, unread_only: bool = False
):
    query = select(Notification).where(Notification.user_id == user_id)
    if unread_only:
        query = query.where(not Notification.read)
    query = query.order_by(Notification.created_at.desc()).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


async def mark_read(db: AsyncSession, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    result = await db.execute(
        update(Notification)
        .where(Notification.id == notification_id, Notification.user_id == user_id)
        .values(read=True)
    )
    await db.commit()
    return result.rowcount > 0


async def mark_all_read(db: AsyncSession, user_id: uuid.UUID) -> int:
    result = await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, not Notification.read)
        .values(read=True)
    )
    await db.commit()
    return result.rowcount


async def get_unread_count(db: AsyncSession, user_id: uuid.UUID) -> int:
    result = await db.scalar(
        select(func.count()).where(
            Notification.user_id == user_id, not Notification.read
        )
    )
    return result or 0
