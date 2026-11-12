import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.buyer import BuyerCreate, BuyerResponse, BuyerUpdate
from app.services import merchant_service

router = APIRouter(prefix="/api/buyers", tags=["buyers"])


@router.get("")
async def list_buyers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await merchant_service.list_buyers(db, page, page_size, search)
    return {
        "items": [BuyerResponse.model_validate(item).model_dump() for item in result.items],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "total_pages": result.total_pages,
    }


@router.get("/{buyer_id}", response_model=BuyerResponse)
async def get_buyer(
    buyer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    buyer = await merchant_service.get_buyer(db, buyer_id)
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer not found")
    return buyer


@router.post("", response_model=BuyerResponse, status_code=201)
async def create_buyer(
    data: BuyerCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await merchant_service.create_buyer(db, data)


@router.put("/{buyer_id}", response_model=BuyerResponse)
async def update_buyer(
    buyer_id: uuid.UUID,
    data: BuyerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    buyer = await merchant_service.get_buyer(db, buyer_id)
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer not found")
    return await merchant_service.update_buyer(db, buyer, data)


@router.delete("/{buyer_id}", status_code=204)
async def delete_buyer(
    buyer_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    buyer = await merchant_service.get_buyer(db, buyer_id)
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer not found")
    await merchant_service.delete_buyer(db, buyer)
