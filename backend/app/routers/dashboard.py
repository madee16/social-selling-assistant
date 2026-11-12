
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, literal, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.ai_session import AISession
from app.models.approval import Approval
from app.models.attribute_def import AttributeDef
from app.models.buyer import Buyer
from app.models.collection import Collection
from app.models.conversation import Conversation
from app.models.merchant import Merchant
from app.models.order import Order
from app.models.product import Product
from app.models.store import Store
from app.models.user import User
from app.services import platform_service

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv_count = await db.scalar(
        select(func.count(Conversation.id)).where(Conversation.user_id == current_user.id)
    )
    order_count = await db.scalar(
        select(func.count(Order.id)).where(Order.user_id == current_user.id)
    )
    product_count = await db.scalar(
        select(func.count(Product.id)).where(Product.user_id == current_user.id)
    )

    merchant_ids = list(
        (
            await db.execute(
                select(Merchant.id).where(Merchant.user_id == current_user.id)
            )
        ).scalars().all()
    )

    store_count = 0
    collection_count = 0
    attribute_def_count = 0
    if merchant_ids:
        store_count = await db.scalar(
            select(func.count(Store.id)).where(Store.merchant_id.in_(merchant_ids))
        )
        collection_count = await db.scalar(
            select(func.count(Collection.id)).where(Collection.merchant_id.in_(merchant_ids))
        )
        attribute_def_count = await db.scalar(
            select(func.count(AttributeDef.id)).where(AttributeDef.merchant_id.in_(merchant_ids))
        )
    store_count = store_count or 0
    collection_count = collection_count or 0
    attribute_def_count = attribute_def_count or 0

    buyer_count = await db.scalar(select(func.count(Buyer.id)))
    buyer_count = buyer_count or 0

    pending_approvals = await db.scalar(
        select(func.count(Approval.id)).where(
            ((Approval.requester_id == current_user.id) | (Approval.approver_id == current_user.id))
            & (Approval.status == "pending")
        )
    )
    pending_approvals = pending_approvals or 0

    store_ids = await platform_service.user_store_ids(db, current_user.id)
    active_sessions = 0
    if store_ids:
        active_sessions = await db.scalar(
            select(func.count(AISession.id)).where(
                AISession.store_id.in_(store_ids) & (AISession.status == "active")
            )
        )
    active_sessions = active_sessions or 0

    return {
        "total_conversations": conv_count or 0,
        "total_orders": order_count or 0,
        "total_products": product_count or 0,
        "total_stores": store_count,
        "total_collections": collection_count,
        "total_attribute_defs": attribute_def_count,
        "total_buyers": buyer_count,
        "pending_approvals": pending_approvals,
        "active_ai_sessions": active_sessions,
    }


@router.get("/activity")
async def get_activity(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    recent_orders = await db.execute(
        select(
            literal("order_created").label("type"),
            Order.customer_name.label("title"),
            Order.total_amount.label("value"),
            Order.created_at.label("timestamp"),
        )
        .where(Order.user_id == current_user.id)
        .order_by(Order.created_at.desc())
        .limit(limit)
    )
    recent_convs = await db.execute(
        select(
            literal("conversation_started").label("type"),
            Conversation.customer_name.label("title"),
            literal(None).label("value"),
            Conversation.created_at.label("timestamp"),
        )
        .where(
            Conversation.user_id == current_user.id,
            Conversation.customer_name.isnot(None),
        )
        .order_by(Conversation.created_at.desc())
        .limit(limit)
    )
    orders = recent_orders.all()
    convs = recent_convs.all()

    items = []
    for o in orders:
        items.append({
            "type": "order_created",
            "customer_name": o.title or "Unknown",
            "detail": f"{float(o.value or 0):.2f} TND" if o.value else None,
            "timestamp": o.timestamp.isoformat() if o.timestamp else None,
        })
    for c in convs:
        if c.title:
            items.append({
                "type": "conversation_started",
                "customer_name": c.title,
                "detail": None,
                "timestamp": c.timestamp.isoformat() if c.timestamp else None,
            })

    items.sort(key=lambda x: x["timestamp"] or "", reverse=True)
    return {"items": items[:limit]}
