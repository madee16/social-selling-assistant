import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.marketplace import (
    MarketplaceListingCreate,
    MarketplaceListingResponse,
    MarketplaceListingUpdate,
)
from app.schemas.scoring import (
    ProductScoreCreate,
    ProductScoreResponse,
    ProductScoreUpdate,
    SellerTrustScoreCreate,
    SellerTrustScoreResponse,
    SellerTrustScoreUpdate,
)
from app.services import platform_service

router = APIRouter(prefix="/api", tags=["marketplace & scoring"])


def _page_result(result, schema):
    return {
        "items": [schema.model_validate(item).model_dump() for item in result.items],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "total_pages": result.total_pages,
    }


# ---- Marketplace listings ----


@router.get("/products/{product_id}/listings")
async def list_marketplace_listings(
    product_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await platform_service.list_marketplace_listings(
        db, product_id, current_user.id, page, page_size
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return _page_result(result, MarketplaceListingResponse)


@router.post("/products/{product_id}/listings", response_model=MarketplaceListingResponse, status_code=201)
async def create_marketplace_listing(
    product_id: uuid.UUID,
    data: MarketplaceListingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await platform_service.create_marketplace_listing(
        db, product_id, current_user.id, data
    )
    if not record:
        raise HTTPException(status_code=404, detail="Product not found")
    return record


@router.put("/marketplace-listings/{listing_id}", response_model=MarketplaceListingResponse)
async def update_marketplace_listing(
    listing_id: uuid.UUID,
    data: MarketplaceListingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await platform_service.get_marketplace_listing(db, listing_id)
    if not record:
        raise HTTPException(status_code=404, detail="Listing not found")
    return await platform_service.update_marketplace_listing(db, record, data)


@router.delete("/marketplace-listings/{listing_id}", status_code=204)
async def delete_marketplace_listing(
    listing_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await platform_service.get_marketplace_listing(db, listing_id)
    if not record:
        raise HTTPException(status_code=404, detail="Listing not found")
    await platform_service.delete_marketplace_listing(db, record)


# ---- Product scores ----


@router.get("/products/{product_id}/scores")
async def list_product_scores(
    product_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await platform_service.list_product_scores(db, product_id, page, page_size)
    return _page_result(result, ProductScoreResponse)


@router.post("/products/{product_id}/scores", response_model=ProductScoreResponse, status_code=201)
async def create_product_score(
    product_id: uuid.UUID,
    data: ProductScoreCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await platform_service.create_product_score(db, product_id, data)


@router.put("/product-scores/{score_id}", response_model=ProductScoreResponse)
async def update_product_score(
    score_id: uuid.UUID,
    data: ProductScoreUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await platform_service.get_product_score(db, score_id)
    if not record:
        raise HTTPException(status_code=404, detail="Product score not found")
    return await platform_service.update_product_score(db, record, data)


@router.delete("/product-scores/{score_id}", status_code=204)
async def delete_product_score(
    score_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await platform_service.get_product_score(db, score_id)
    if not record:
        raise HTTPException(status_code=404, detail="Product score not found")
    await platform_service.delete_product_score(db, record)


# ---- Seller trust scores ----


@router.get("/seller-trust")
async def list_seller_trust(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await platform_service.list_seller_trust(db, current_user.id, page, page_size)
    return _page_result(result, SellerTrustScoreResponse)


@router.post("/seller-trust", response_model=SellerTrustScoreResponse, status_code=201)
async def create_seller_trust(
    data: SellerTrustScoreCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await platform_service.create_seller_trust(db, current_user.id, data)
    if not record:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return record


@router.put("/seller-trust/{trust_id}", response_model=SellerTrustScoreResponse)
async def update_seller_trust(
    trust_id: uuid.UUID,
    data: SellerTrustScoreUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await platform_service.get_seller_trust(db, trust_id)
    if not record:
        raise HTTPException(status_code=404, detail="Trust score not found")
    return await platform_service.update_seller_trust(db, record, data)


@router.delete("/seller-trust/{trust_id}", status_code=204)
async def delete_seller_trust(
    trust_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await platform_service.get_seller_trust(db, trust_id)
    if not record:
        raise HTTPException(status_code=404, detail="Trust score not found")
    await platform_service.delete_seller_trust(db, record)
