import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate
from app.utils.pagination import paginate


async def list_categories(db: AsyncSession, user_id: uuid.UUID, page: int = 1, page_size: int = 20):
    query = select(Category).where(Category.user_id == user_id).order_by(Category.name)
    return await paginate(db, query, page, page_size)


async def get_category(db: AsyncSession, category_id: uuid.UUID, user_id: uuid.UUID):
    result = await db.execute(
        select(Category).where(Category.id == category_id, Category.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_category(db: AsyncSession, user_id: uuid.UUID, data: CategoryCreate):
    category = Category(user_id=user_id, **data.model_dump())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


async def update_category(db: AsyncSession, category_id: uuid.UUID, user_id: uuid.UUID, data: CategoryUpdate):
    category = await get_category(db, category_id, user_id)
    if not category:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(category, key, value)
    await db.commit()
    await db.refresh(category)
    return category


async def delete_category(db: AsyncSession, category_id: uuid.UUID, user_id: uuid.UUID):
    category = await get_category(db, category_id, user_id)
    if not category:
        return False
    await db.delete(category)
    await db.commit()
    return True
