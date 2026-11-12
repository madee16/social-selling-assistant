import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order, OrderItem
from app.models.product import Product
from app.schemas.order import OrderCreate, OrderItemCreate
from app.services.notification_service import create_notification
from app.services.pdf_service import generate_order_invoice_pdf


async def create_order(
    db: AsyncSession,
    user_id: uuid.UUID,
    data: OrderCreate,
) -> Order:
    requested_quantities: dict[uuid.UUID, int] = {}
    for item in data.items:
        requested_quantities[item.product_id] = requested_quantities.get(item.product_id, 0) + item.quantity

    products_result = await db.execute(
        select(Product).where(Product.user_id == user_id, Product.id.in_(requested_quantities), Product.is_active.is_(True))
    )
    products = {product.id: product for product in products_result.scalars().all()}
    if len(products) != len(requested_quantities):
        raise HTTPException(status_code=400, detail="One or more selected products are unavailable")
    for product_id, quantity in requested_quantities.items():
        if products[product_id].stock_quantity < quantity:
            raise HTTPException(status_code=400, detail=f"Insufficient stock for {products[product_id].name}")

    total = sum(quantity * float(products[product_id].price) for product_id, quantity in requested_quantities.items())

    order = Order(
        user_id=user_id,
        conversation_id=data.conversation_id,
        customer_name=data.customer_name,
        customer_phone=data.customer_phone,
        customer_address=data.customer_address,
        status="pending",
        total_amount=total,
    )
    db.add(order)
    await db.flush()

    for product_id, quantity in requested_quantities.items():
        product = products[product_id]
        product.stock_quantity -= quantity
        item = OrderItem(
            order_id=order.id,
            product_id=product_id,
            quantity=quantity,
            unit_price=float(product.price),
            subtotal=quantity * float(product.price),
        )
        db.add(item)

    await db.commit()
    await db.refresh(order)

    await create_notification(
        db, user_id, "new_order",
        f"New order from {data.customer_name}",
        f"Order total: {total:.2f} TND",
        "/orders",
    )

    return order


async def create_order_from_conversation(
    db: AsyncSession,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID,
    customer_name: str,
    customer_phone: str | None = None,
    customer_address: str | None = None,
    items: list[dict] | None = None,
) -> Order:
    """Create order from chat context with product details."""
    if items is None:
        items = []

    order_items = []
    for item in items:
        product_result = await db.execute(
            select(Product).where(Product.id == item["product_id"], Product.user_id == user_id)
        )
        product = product_result.scalar_one_or_none()
        if not product:
            continue
        order_items.append(OrderItemCreate(
            product_id=product.id,
            quantity=item.get("quantity", 1),
            unit_price=float(product.price),
        ))

    return await create_order(db, user_id, OrderCreate(
        conversation_id=conversation_id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_address=customer_address,
        items=order_items,
    ))


async def list_orders(
    db: AsyncSession,
    user_id: uuid.UUID,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
) -> dict:
    query = (
        select(Order)
        .where(Order.user_id == user_id)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
        .order_by(Order.created_at.desc())
    )

    if status:
        query = query.where(Order.status == status)

    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    orders = result.scalars().all()

    count_query = select(func.count(Order.id)).where(Order.user_id == user_id)
    if status:
        count_query = count_query.where(Order.status == status)
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    return {
        "items": orders,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": -(-total // page_size) if total > 0 else 1,
    }


async def get_order(
    db: AsyncSession,
    order_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Order | None:
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.user_id == user_id)
        .options(selectinload(Order.items).selectinload(OrderItem.product))
    )
    return result.scalar_one_or_none()


async def update_order_status(
    db: AsyncSession,
    order_id: uuid.UUID,
    user_id: uuid.UUID,
    status: str,
) -> Order | None:
    order = await get_order(db, order_id, user_id)
    if not order:
        return None
    order.status = status
    await db.commit()
    await db.refresh(order)
    return order


async def delete_order(
    db: AsyncSession,
    order_id: uuid.UUID,
    user_id: uuid.UUID,
) -> bool:
    order = await get_order(db, order_id, user_id)
    if not order:
        return False
    await db.delete(order)
    await db.commit()
    return True
