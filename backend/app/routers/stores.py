import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.merchant import (
    StoreCreate,
    StoreMemberResponse,
    StoreResponse,
    StoreUpdate,
)
from app.services import merchant_service

router = APIRouter(prefix="/api/stores", tags=["stores"])


@router.get("")
async def list_stores(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await merchant_service.list_stores(db, current_user.id, page, page_size)
    return {
        "items": [StoreResponse.model_validate(item).model_dump() for item in result.items],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "total_pages": result.total_pages,
    }


@router.get("/{store_id}", response_model=StoreResponse)
async def get_store(
    store_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    store = await merchant_service.get_store(db, store_id, current_user.id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return store


@router.post("", response_model=StoreResponse, status_code=201)
async def create_store(
    data: StoreCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    store = await merchant_service.create_store(db, current_user.id, data)
    if not store:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return store


@router.put("/{store_id}", response_model=StoreResponse)
async def update_store(
    store_id: uuid.UUID,
    data: StoreUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    store = await merchant_service.get_store(db, store_id, current_user.id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    return await merchant_service.update_store(db, store, data)


@router.delete("/{store_id}", status_code=204)
async def delete_store(
    store_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    store = await merchant_service.get_store(db, store_id, current_user.id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    await merchant_service.delete_store(db, store)


@router.get("/{store_id}/members")
async def list_store_members(
    store_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    store = await merchant_service.get_store(db, store_id, current_user.id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")
    result = await merchant_service.list_store_members(db, store_id, page, page_size)
    return {
        "items": [StoreMemberResponse.model_validate(item).model_dump() for item in result.items],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "total_pages": result.total_pages,
    }
