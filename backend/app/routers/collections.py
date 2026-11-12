import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.collection import CollectionCreate, CollectionResponse, CollectionUpdate
from app.services import platform_service

router = APIRouter(prefix="/api/collections", tags=["collections"])


@router.get("")
async def list_collections(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await platform_service.list_collections(db, current_user.id, page, page_size)
    return {
        "items": [CollectionResponse.model_validate(item).model_dump() for item in result.items],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "total_pages": result.total_pages,
    }


@router.get("/{collection_id}", response_model=CollectionResponse)
async def get_collection(
    collection_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await platform_service.get_collection(db, collection_id, current_user.id)
    if not record:
        raise HTTPException(status_code=404, detail="Collection not found")
    return record


@router.post("", response_model=CollectionResponse, status_code=201)
async def create_collection(
    data: CollectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await platform_service.create_collection(db, current_user.id, data)
    if not record:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return record


@router.put("/{collection_id}", response_model=CollectionResponse)
async def update_collection(
    collection_id: uuid.UUID,
    data: CollectionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await platform_service.get_collection(db, collection_id, current_user.id)
    if not record:
        raise HTTPException(status_code=404, detail="Collection not found")
    return await platform_service.update_collection(db, record, data)


@router.delete("/{collection_id}", status_code=204)
async def delete_collection(
    collection_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await platform_service.get_collection(db, collection_id, current_user.id)
    if not record:
        raise HTTPException(status_code=404, detail="Collection not found")
    await platform_service.delete_collection(db, record)
