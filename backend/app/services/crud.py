"""Generic async CRUD helpers shared by routers."""
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.utils.pagination import Page, paginate


async def list_records(
    db: AsyncSession,
    model: type,
    where=None,
    page: int = 1,
    page_size: int = 20,
    order_by=None,
) -> Page:
    query = select(model)
    if where is not None:
        query = query.where(where)
    query = query.order_by(order_by if order_by is not None else model.created_at.desc())
    return await paginate(db, query, page, page_size)


async def get_record(db: AsyncSession, model: type, where) -> Any | None:
    result = await db.execute(select(model).where(where))
    return result.scalars().first()


async def create_record(db: AsyncSession, model: type, data: dict) -> Any:
    obj = model(**data)
    db.add(obj)
    await db.commit()
    await db.refresh(obj)
    return obj


async def update_record(db: AsyncSession, obj: Any, data: dict, skip: set = frozenset()) -> Any:
    for key, value in data.items():
        if key in skip or not hasattr(obj, key):
            continue
        setattr(obj, key, value)
    await db.commit()
    await db.refresh(obj)
    return obj


async def delete_record(db: AsyncSession, obj: Any) -> None:
    await db.delete(obj)
    await db.commit()


async def get_merchant_for_user(db: AsyncSession, user_id: uuid.UUID):
    from app.models.merchant import Merchant

    result = await db.execute(select(Merchant).where(Merchant.user_id == user_id))
    return result.scalars().first()
