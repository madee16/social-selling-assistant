import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.buyer import Buyer
from app.models.store import Store
from app.models.user import User
from app.schemas.order import OrderCreate, OrderListResponse, OrderResponse, OrderStatusUpdate
from app.services import order_service

router = APIRouter(prefix="/api/orders", tags=["orders"])


@router.post("", response_model=OrderResponse, status_code=201)
async def create_order(
    data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = await order_service.create_order(db, current_user.id, data)
    return await order_service.get_order(db, order.id, current_user.id)


@router.get("", response_model=OrderListResponse)
async def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await order_service.list_orders(db, current_user.id, page, page_size, status)
    return {
        "items": [OrderResponse.model_validate(o).model_dump() for o in result["items"]],
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
        "total_pages": result["total_pages"],
    }


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = await order_service.get_order(db, order_id, current_user.id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: uuid.UUID,
    data: OrderStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    order = await order_service.update_order_status(db, order_id, current_user.id, data.status)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@router.delete("/{order_id}", status_code=204)
async def delete_order(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = await order_service.delete_order(db, order_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Order not found")


@router.get("/{order_id}/invoice.pdf")
async def get_order_invoice_pdf(
    order_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate and return a French/Bilingual Bon de Livraison / Facture PDF for the order."""
    order = await order_service.get_order(db, order_id, current_user.id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    store = None
    buyer = None
    if order.store_id:
        store_res = await db.execute(select(Store).where(Store.id == order.store_id))
        store = store_res.scalar_one_or_none()
    if order.buyer_id:
        buyer_res = await db.execute(select(Buyer).where(Buyer.id == order.buyer_id))
        buyer = buyer_res.scalar_one_or_none()

    pdf_bytes = order_service.generate_order_invoice_pdf(
        order=order,
        merchant=current_user,
        store=store,
        buyer=buyer,
    )

    filename = f"bon-de-livraison-{order.id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )

