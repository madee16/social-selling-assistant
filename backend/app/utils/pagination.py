import math

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class Page(BaseModel):
    items: list
    total: int
    page: int
    page_size: int
    total_pages: int


async def paginate(db: AsyncSession, query, page: int = 1, page_size: int = 20):
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    total_pages = math.ceil(total / page_size) if total > 0 else 0
    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    items = result.scalars().all()
    return Page(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
