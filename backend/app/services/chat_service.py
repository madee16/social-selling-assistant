import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message


async def create_conversation(
    db: AsyncSession,
    user_id: uuid.UUID,
    customer_name: str | None = None,
    customer_phone: str | None = None,
    customer_address: str | None = None,
    language: str | None = "fr",
    platform: str | None = None,
    platform_conversation_id: str | None = None,
) -> Conversation:
    conv = Conversation(
        user_id=user_id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_address=customer_address,
        language=language,
        platform=platform,
        platform_conversation_id=platform_conversation_id,
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conv


async def get_conversation_by_platform(
    db: AsyncSession, user_id: uuid.UUID, platform: str, platform_conversation_id: str
) -> Conversation | None:
    result = await db.execute(
        select(Conversation).where(
            Conversation.user_id == user_id,
            Conversation.platform == platform,
            Conversation.platform_conversation_id == platform_conversation_id,
        )
    )
    return result.scalar_one_or_none()


async def get_or_create_conversation(
    db: AsyncSession,
    user_id: uuid.UUID,
    platform: str,
    platform_conversation_id: str,
    customer_name: str | None = None,
    customer_phone: str | None = None,
    language: str | None = "fr",
) -> Conversation:
    """Fetch the conversation for a platform channel, creating it if missing.

    A unique partial index on (user_id, platform, platform_conversation_id)
    guards against concurrent webhook deliveries creating duplicates; a lost
    race simply re-fetches the winner's conversation.
    """
    conv = await get_conversation_by_platform(db, user_id, platform, platform_conversation_id)
    if conv:
        return conv
    try:
        return await create_conversation(
            db,
            user_id=user_id,
            customer_name=customer_name,
            customer_phone=customer_phone,
            language=language,
            platform=platform,
            platform_conversation_id=platform_conversation_id,
        )
    except IntegrityError:
        await db.rollback()
        conv = await get_conversation_by_platform(db, user_id, platform, platform_conversation_id)
        if conv:
            return conv
        raise


async def get_conversation(
    db: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID
) -> Conversation | None:
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id, Conversation.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


async def list_conversations(
    db: AsyncSession, user_id: uuid.UUID, page: int = 1, page_size: int = 20
):
    query = (
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
    )
    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    items = result.scalars().all()
    total = await db.scalar(
        select(func.count()).where(Conversation.user_id == user_id)
    ) or 0
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": -(-total // page_size) if total > 0 else 1,
    }


async def update_conversation_info(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    user_id: uuid.UUID,
    customer_name: str | None = None,
    customer_phone: str | None = None,
    customer_address: str | None = None,
) -> Conversation | None:
    conv = await get_conversation(db, conversation_id, user_id)
    if not conv:
        return None
    if customer_name is not None:
        conv.customer_name = customer_name
    if customer_phone is not None:
        conv.customer_phone = customer_phone
    if customer_address is not None:
        conv.customer_address = customer_address
    await db.commit()
    await db.refresh(conv)
    return conv


async def close_conversation(
    db: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID
) -> bool:
    conv = await get_conversation(db, conversation_id, user_id)
    if not conv:
        return False
    conv.status = "closed"
    await db.commit()
    return True


async def save_message(
    db: AsyncSession,
    conversation_id: uuid.UUID,
    role: str,
    content: str,
    language: str | None = None,
    extra_data: dict | None = None,
) -> Message:
    msg = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        language=language,
        extra_data=extra_data,
    )
    db.add(msg)

    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if conv:
        conv.updated_at = datetime.now(UTC)
        if conv.status != "open":
            conv.status = "open"

    await db.commit()
    await db.refresh(msg)
    return msg


async def get_conversation_messages(
    db: AsyncSession, conversation_id: uuid.UUID, user_id: uuid.UUID
):
    conv = await get_conversation(db, conversation_id, user_id)
    if not conv:
        return None, None
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    messages = result.scalars().all()
    return conv, messages
