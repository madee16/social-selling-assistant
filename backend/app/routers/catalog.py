import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.catalog import (
    AttributeDefCreate,
    AttributeDefResponse,
    AttributeDefUpdate,
    InventoryCreate,
    InventoryResponse,
    InventoryUpdate,
    PriceCreate,
    PriceResponse,
    PriceUpdate,
    ProductAttributeCreate,
    ProductAttributeResponse,
    ProductVariantCreate,
    ProductVariantResponse,
    ProductVariantUpdate,
)
from app.services import catalog_service

router = APIRouter(prefix="/api", tags=["catalog"])


def _page_result(result, schema):
    return {
        "items": [schema.model_validate(item).model_dump() for item in result.items],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "total_pages": result.total_pages,
    }


# ---- Attribute definitions ----


@router.get("/attribute-defs")
async def list_attribute_defs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await catalog_service.attribute_defs_for(db, current_user.id, page, page_size)
    if result is None:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return _page_result(result, AttributeDefResponse)


@router.post("/attribute-defs", response_model=AttributeDefResponse, status_code=201)
async def create_attribute_def(
    data: AttributeDefCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attr = await catalog_service.create_attribute_def(db, current_user.id, data)
    if not attr:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return attr


@router.put("/attribute-defs/{def_id}", response_model=AttributeDefResponse)
async def update_attribute_def(
    def_id: uuid.UUID,
    data: AttributeDefUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attr = await catalog_service.get_attribute_def(db, def_id, current_user.id)
    if not attr:
        raise HTTPException(status_code=404, detail="Attribute definition not found")
    return await catalog_service.update_attribute_def(db, attr, data)


@router.delete("/attribute-defs/{def_id}", status_code=204)
async def delete_attribute_def(
    def_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attr = await catalog_service.get_attribute_def(db, def_id, current_user.id)
    if not attr:
        raise HTTPException(status_code=404, detail="Attribute definition not found")
    await catalog_service.delete_attribute_def(db, attr)


# ---- Product attributes ----


@router.get("/products/{product_id}/attributes")
async def list_product_attributes(
    product_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await catalog_service.list_product_attributes(db, product_id, current_user.id, page, page_size)
    if result is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return _page_result(result, ProductAttributeResponse)


@router.post("/products/{product_id}/attributes", response_model=ProductAttributeResponse, status_code=201)
async def create_product_attribute(
    product_id: uuid.UUID,
    data: ProductAttributeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attr = await catalog_service.create_product_attribute(db, product_id, current_user.id, data)
    if not attr:
        raise HTTPException(status_code=404, detail="Product not found")
    return attr


@router.delete("/product-attributes/{attr_id}", status_code=204)
async def delete_product_attribute(
    attr_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    attr = await catalog_service.get_product_attribute(db, attr_id)
    if not attr:
        raise HTTPException(status_code=404, detail="Product attribute not found")
    await catalog_service.delete_product_attribute(db, attr)


# ---- Variants ----


@router.get("/products/{product_id}/variants")
async def list_variants(
    product_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await catalog_service.list_variants(db, product_id, current_user.id, page, page_size)
    if result is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return _page_result(result, ProductVariantResponse)


@router.post("/products/{product_id}/variants", response_model=ProductVariantResponse, status_code=201)
async def create_variant(
    product_id: uuid.UUID,
    data: ProductVariantCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    variant = await catalog_service.create_variant(db, product_id, current_user.id, data)
    if not variant:
        raise HTTPException(status_code=404, detail="Product not found")
    return variant


@router.put("/variants/{variant_id}", response_model=ProductVariantResponse)
async def update_variant(
    variant_id: uuid.UUID,
    data: ProductVariantUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    variant = await catalog_service.get_variant(db, variant_id)
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    return await catalog_service.update_variant(db, variant, data)


@router.delete("/variants/{variant_id}", status_code=204)
async def delete_variant(
    variant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    variant = await catalog_service.get_variant(db, variant_id)
    if not variant:
        raise HTTPException(status_code=404, detail="Variant not found")
    await catalog_service.delete_variant(db, variant)


# ---- Inventory ----


@router.get("/products/{product_id}/inventory")
async def list_inventory(
    product_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await catalog_service.list_inventory(db, product_id, current_user.id, page, page_size)
    if result is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return _page_result(result, InventoryResponse)


@router.post("/products/{product_id}/inventory", response_model=InventoryResponse, status_code=201)
async def create_inventory(
    product_id: uuid.UUID,
    data: InventoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await catalog_service.create_inventory(db, product_id, current_user.id, data)
    if not record:
        raise HTTPException(status_code=404, detail="Product not found")
    return record


@router.put("/inventory/{inv_id}", response_model=InventoryResponse)
async def update_inventory(
    inv_id: uuid.UUID,
    data: InventoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await catalog_service.get_inventory_record(db, inv_id)
    if not record:
        raise HTTPException(status_code=404, detail="Inventory record not found")
    return await catalog_service.update_inventory(db, record, data)


@router.delete("/inventory/{inv_id}", status_code=204)
async def delete_inventory(
    inv_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await catalog_service.get_inventory_record(db, inv_id)
    if not record:
        raise HTTPException(status_code=404, detail="Inventory record not found")
    await catalog_service.delete_inventory(db, record)


# ---- Prices ----


@router.get("/products/{product_id}/prices")
async def list_prices(
    product_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await catalog_service.list_prices(db, product_id, current_user.id, page, page_size)
    if result is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return _page_result(result, PriceResponse)


@router.post("/products/{product_id}/prices", response_model=PriceResponse, status_code=201)
async def create_price(
    product_id: uuid.UUID,
    data: PriceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    price = await catalog_service.create_price(db, product_id, current_user.id, data)
    if not price:
        raise HTTPException(status_code=404, detail="Product not found")
    return price


@router.put("/prices/{price_id}", response_model=PriceResponse)
async def update_price(
    price_id: uuid.UUID,
    data: PriceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    price = await catalog_service.get_price(db, price_id)
    if not price:
        raise HTTPException(status_code=404, detail="Price not found")
    return await catalog_service.update_price(db, price, data)


@router.delete("/prices/{price_id}", status_code=204)
async def delete_price(
    price_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    price = await catalog_service.get_price(db, price_id)
    if not price:
        raise HTTPException(status_code=404, detail="Price not found")
    await catalog_service.delete_price(db, price)
