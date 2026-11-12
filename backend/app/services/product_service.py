import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.schemas.product import ProductCreate, ProductUpdate
from app.utils.pagination import paginate


async def list_products(
    db: AsyncSession,
    user_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    search: str | None = None,
    category_id: uuid.UUID | None = None,
    active_only: bool = False,
):
    query = select(Product).where(Product.user_id == user_id)

    if active_only:
        query = query.where(Product.is_active)
    if category_id:
        query = query.where(Product.category_id == category_id)
    if search:
        pattern = f"%{search}%"
        query = query.where(
            Product.name.ilike(pattern) | Product.description.ilike(pattern)
        )

    query = query.order_by(Product.created_at.desc())
    return await paginate(db, query, page, page_size)


async def get_product(db: AsyncSession, product_id: uuid.UUID, user_id: uuid.UUID):
    result = await db.execute(
        select(Product).where(Product.id == product_id, Product.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def create_product(db: AsyncSession, user_id: uuid.UUID, data: ProductCreate):
    product = Product(user_id=user_id, **data.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product


async def update_product(db: AsyncSession, product_id: uuid.UUID, user_id: uuid.UUID, data: ProductUpdate):
    product = await get_product(db, product_id, user_id)
    if not product:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    await db.commit()
    await db.refresh(product)
    return product


async def delete_product(db: AsyncSession, product_id: uuid.UUID, user_id: uuid.UUID):
    product = await get_product(db, product_id, user_id)
    if not product:
        return False
    await db.delete(product)
    await db.commit()
    return True
