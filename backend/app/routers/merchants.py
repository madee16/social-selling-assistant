
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.merchant import MerchantCreate, MerchantResponse, MerchantUpdate
from app.services import merchant_service

router = APIRouter(prefix="/api/merchants", tags=["merchants"])


@router.get("/me", response_model=MerchantResponse)
async def get_my_merchant(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    merchant = await merchant_service.get_merchant(db, current_user.id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return merchant


@router.post("", response_model=MerchantResponse, status_code=201)
async def create_merchant(
    data: MerchantCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = await merchant_service.get_merchant(db, current_user.id)
    if existing:
        raise HTTPException(status_code=409, detail="Merchant already exists")
    return await merchant_service.create_merchant(db, current_user.id, data)


@router.put("/me", response_model=MerchantResponse)
async def update_my_merchant(
    data: MerchantUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    merchant = await merchant_service.get_merchant(db, current_user.id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return await merchant_service.update_merchant(db, merchant, data)
