import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.schemas.analytics import (
    AnalyticsResponse,
    CustomerMetrics,
    DateRangeParams,
    FunnelData,
    OrderStatusDistribution,
    RevenueSeriesPoint,
    SalesMetrics,
    TopProduct,
)


async def get_analytics(
    db: AsyncSession,
    user_id: uuid.UUID,
    params: DateRangeParams,
) -> AnalyticsResponse:
    end_date = params.end_date or datetime.now(UTC)
    start_date = params.start_date or (end_date - timedelta(days=30))

    period = params.period

    revenue_series = await _get_revenue(db, user_id, start_date, end_date, period)
    top_products = await _get_top_products(db, user_id, start_date, end_date)
    status_dist = await _get_status_distribution(db, user_id, start_date, end_date)
    funnel = await _get_funnel(db, user_id, start_date, end_date)
    customers = await _get_customer_metrics(db, user_id, start_date, end_date)

    total_revenue = sum(r.revenue for r in revenue_series)
    total_orders = sum(r.orders for r in revenue_series)
    avg_order = total_revenue / total_orders if total_orders > 0 else 0

    prev_start = start_date - (end_date - start_date)
    prev_revenue = await db.scalar(
        select(func.coalesce(func.sum(Order.total_amount), 0))
        .where(Order.user_id == user_id, Order.created_at >= prev_start, Order.created_at < start_date)
    )
    prev_orders = await db.scalar(
        select(func.count(Order.id))
        .where(Order.user_id == user_id, Order.created_at >= prev_start, Order.created_at < start_date)
    )
    revenue_change = round(((total_revenue - float(prev_revenue or 0)) / float(prev_revenue or 1)) * 100, 1)
    orders_change = round(((total_orders - (prev_orders or 0)) / (prev_orders or 1)) * 100, 1)

    sales = SalesMetrics(
        total_revenue=round(total_revenue, 2),
        total_orders=total_orders,
        avg_order_value=round(avg_order, 2),
        revenue_change=revenue_change,
        orders_change=orders_change,
    )

    return AnalyticsResponse(
        sales=sales,
        top_products=top_products,
        status_distribution=status_dist,
        funnel=funnel,
        customers=customers,
        revenue_series=[
            RevenueSeriesPoint(date=r.date, revenue=r.revenue, orders=r.orders)
            for r in revenue_series
        ],
        period=period,
        date_range={"start": start_date.isoformat(), "end": end_date.isoformat()},
    )


async def _get_revenue(
    db: AsyncSession,
    user_id: uuid.UUID,
    start_date: datetime,
    end_date: datetime,
    period: str,
) -> list[RevenueSeriesPoint]:
    trunc_map = {
        "day": func.date_trunc("day", Order.created_at),
        "week": func.date_trunc("week", Order.created_at),
        "month": func.date_trunc("month", Order.created_at),
    }
    trunc = trunc_map.get(period, func.date_trunc("day", Order.created_at))

    query = (
        select(
            trunc.label("period"),
            func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
            func.count(Order.id).label("orders_count"),
        )
        .where(
            Order.user_id == user_id,
            Order.created_at >= start_date,
            Order.created_at <= end_date,
        )
        .group_by(trunc)
        .order_by(trunc)
    )
    result = await db.execute(query)
    rows = result.all()

    return [
        RevenueSeriesPoint(
            date=r.period.strftime("%Y-%m-%d"),
            revenue=float(r.revenue or 0),
            orders=r.orders_count or 0,
        )
        for r in rows
    ]


async def _get_top_products(
    db: AsyncSession,
    user_id: uuid.UUID,
    start_date: datetime,
    end_date: datetime,
    limit: int = 10,
) -> list[TopProduct]:
    query = (
        select(
            Product.id,
            Product.name,
            func.coalesce(func.sum(OrderItem.quantity), 0).label("total_quantity"),
            func.coalesce(func.sum(OrderItem.subtotal), 0).label("total_revenue"),
            func.count(func.distinct(Order.id)).label("order_count"),
        )
        .join(OrderItem, OrderItem.product_id == Product.id)
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            Product.user_id == user_id,
            Order.user_id == user_id,
            Order.created_at >= start_date,
            Order.created_at <= end_date,
        )
        .group_by(Product.id, Product.name)
        .order_by(func.sum(OrderItem.subtotal).desc())
        .limit(limit)
    )
    result = await db.execute(query)
    rows = result.all()

    return [
        TopProduct(
            product_id=str(r.id),
            name=r.name,
            total_quantity=r.total_quantity or 0,
            total_revenue=float(r.total_revenue or 0),
            order_count=r.order_count or 0,
        )
        for r in rows
    ]


async def _get_status_distribution(
    db: AsyncSession,
    user_id: uuid.UUID,
    start_date: datetime,
    end_date: datetime,
) -> list[OrderStatusDistribution]:
    query = (
        select(
            Order.status,
            func.count(Order.id).label("count"),
        )
        .where(
            Order.user_id == user_id,
            Order.created_at >= start_date,
            Order.created_at <= end_date,
        )
        .group_by(Order.status)
    )
    result = await db.execute(query)
    rows = result.all()

    total = sum(r.count for r in rows)
    return [
        OrderStatusDistribution(
            status=r.status,
            count=r.count,
            percentage=round((r.count / total * 100) if total > 0 else 0, 1),
        )
        for r in rows
    ]


async def _get_funnel(
    db: AsyncSession,
    user_id: uuid.UUID,
    start_date: datetime,
    end_date: datetime,
) -> FunnelData:
    conversations = await db.execute(
        select(func.count(Conversation.id)).where(
            Conversation.user_id == user_id,
            Conversation.created_at >= start_date,
            Conversation.created_at <= end_date,
        )
    )
    conversations_count = conversations.scalar() or 0

    conv_with_messages = await db.execute(
        select(func.count(func.distinct(Conversation.id)))
        .join(Message, Message.conversation_id == Conversation.id)
        .where(
            Conversation.user_id == user_id,
            Conversation.created_at >= start_date,
            Conversation.created_at <= end_date,
        )
    )
    conv_msg_count = conv_with_messages.scalar() or 0

    orders_created = await db.execute(
        select(func.count(Order.id)).where(
            Order.user_id == user_id,
            Order.created_at >= start_date,
            Order.created_at <= end_date,
        )
    )
    orders_count = orders_created.scalar() or 0

    orders_completed = await db.execute(
        select(func.count(Order.id)).where(
            Order.user_id == user_id,
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.status.in_(["delivered", "shipped"]),
        )
    )
    completed_count = orders_completed.scalar() or 0

    conversion = (
        round(orders_count / conversations_count * 100, 1) if conversations_count > 0 else 0
    )

    return FunnelData(
        conversations=conversations_count,
        conversations_with_messages=conv_msg_count,
        orders_created=orders_count,
        orders_completed=completed_count,
        conversion_rate=conversion,
    )


async def _get_customer_metrics(
    db: AsyncSession,
    user_id: uuid.UUID,
    start_date: datetime,
    end_date: datetime,
) -> CustomerMetrics:
    customer_query = (
        select(Order.customer_phone)
        .where(
            Order.user_id == user_id,
            Order.created_at >= start_date,
            Order.created_at <= end_date,
            Order.customer_phone.isnot(None),
        )
        .distinct()
    )
    result = await db.execute(customer_query)
    phones = [r[0] for r in result.all()]
    total_customers = len(phones)

    first_order_subq = (
        select(
            Order.customer_phone,
            func.min(Order.created_at).label("first_order"),
        )
        .where(
            Order.user_id == user_id,
            Order.customer_phone.isnot(None),
        )
        .group_by(Order.customer_phone)
        .subquery()
    )

    new_customers = await db.execute(
        select(func.count(first_order_subq.c.customer_phone)).where(
            first_order_subq.c.first_order >= start_date,
            first_order_subq.c.first_order <= end_date,
        )
    )
    new_count = new_customers.scalar() or 0

    returning = total_customers - new_count

    avg_query = (
        select(func.avg(Order.total_amount))
        .where(
            Order.user_id == user_id,
            Order.created_at >= start_date,
            Order.created_at <= end_date,
        )
    )
    avg_result = await db.execute(avg_query)
    avg_value = float(avg_result.scalar() or 0)

    return CustomerMetrics(
        total_customers=total_customers,
        new_customers=new_count,
        returning_customers=max(0, returning),
        avg_order_value=round(avg_value, 2),
    )
