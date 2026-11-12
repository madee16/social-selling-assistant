import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attribute_def import AttributeDef
from app.models.inventory import Inventory
from app.models.price import Price
from app.models.product import Product
from app.models.product_attribute import ProductAttribute
from app.models.product_variant import ProductVariant
from app.schemas.catalog import (
    AttributeDefCreate,
    AttributeDefUpdate,
    InventoryCreate,
    InventoryUpdate,
    PriceCreate,
    PriceUpdate,
    ProductVariantCreate,
    ProductVariantUpdate,
)
from app.services import crud


async def attribute_defs_for(db: AsyncSession, user_id: uuid.UUID, page=1, page_size=20):
    merchant = await crud.get_merchant_for_user(db, user_id)
    if not merchant:
        return None
    return await crud.list_records(
        db, AttributeDef, where=AttributeDef.merchant_id == merchant.id, page=page, page_size=page_size
    )


async def get_attribute_def(db, attribute_def_id, user_id):
    merchant = await crud.get_merchant_for_user(db, user_id)
    if not merchant:
        return None
    return await crud.get_record(
        db, AttributeDef, (AttributeDef.id == attribute_def_id) & (AttributeDef.merchant_id == merchant.id)
    )


async def create_attribute_def(db, user_id, data: AttributeDefCreate):
    merchant = await crud.get_merchant_for_user(db, user_id)
    if not merchant:
        return None
    return await crud.create_record(db, AttributeDef, {"merchant_id": merchant.id, **data.model_dump()})


async def update_attribute_def(db, attr, data: AttributeDefUpdate):
    return await crud.update_record(db, attr, data.model_dump(exclude_unset=True))


async def delete_attribute_def(db, attr):
    await crud.delete_record(db, attr)


def _product_owned(product_id: uuid.UUID, user_id: uuid.UUID):
    return (Product.id == product_id) & (Product.user_id == user_id)


async def product_owned(db, product_id: uuid.UUID, user_id: uuid.UUID) -> Product | None:
    return await crud.get_record(db, Product, _product_owned(product_id, user_id))


async def list_product_attributes(db, product_id, user_id, page=1, page_size=20):
    if not await product_owned(db, product_id, user_id):
        return None
    return await crud.list_records(
        db, ProductAttribute, where=ProductAttribute.product_id == product_id, page=page, page_size=page_size
    )


async def get_product_attribute(db, attr_id):
    return await crud.get_record(db, ProductAttribute, ProductAttribute.id == attr_id)


async def create_product_attribute(db, product_id, user_id, data) -> ProductAttribute | None:
    if not await product_owned(db, product_id, user_id):
        return None
    return await crud.create_record(
        db, ProductAttribute, {"product_id": product_id, **data.model_dump()}
    )


async def delete_product_attribute(db, attr):
    await crud.delete_record(db, attr)


async def list_variants(db, product_id, user_id, page=1, page_size=20):
    if not await product_owned(db, product_id, user_id):
        return None
    return await crud.list_records(
        db, ProductVariant, where=ProductVariant.product_id == product_id, page=page, page_size=page_size
    )


async def get_variant(db, variant_id):
    return await crud.get_record(db, ProductVariant, ProductVariant.id == variant_id)


async def create_variant(db, product_id, user_id, data: ProductVariantCreate) -> ProductVariant | None:
    if not await product_owned(db, product_id, user_id):
        return None
    return await crud.create_record(
        db, ProductVariant, {"product_id": product_id, **data.model_dump()}
    )


async def update_variant(db, variant, data: ProductVariantUpdate):
    return await crud.update_record(db, variant, data.model_dump(exclude_unset=True))


async def delete_variant(db, variant):
    await crud.delete_record(db, variant)


async def list_inventory(db, product_id, user_id, page=1, page_size=20):
    if not await product_owned(db, product_id, user_id):
        return None
    return await crud.list_records(
        db, Inventory, where=Inventory.product_id == product_id, page=page, page_size=page_size
    )


async def get_inventory_record(db, inventory_id):
    return await crud.get_record(db, Inventory, Inventory.id == inventory_id)


async def create_inventory(db, product_id, user_id, data: InventoryCreate) -> Inventory | None:
    if not await product_owned(db, product_id, user_id):
        return None
    return await crud.create_record(
        db, Inventory, {"product_id": product_id, **data.model_dump()}
    )


async def update_inventory(db, record, data: InventoryUpdate):
    return await crud.update_record(db, record, data.model_dump(exclude_unset=True))


async def delete_inventory(db, record):
    await crud.delete_record(db, record)


async def list_prices(db, product_id, user_id, page=1, page_size=20):
    if not await product_owned(db, product_id, user_id):
        return None
    return await crud.list_records(
        db, Price, where=Price.product_id == product_id, page=page, page_size=page_size
    )


async def get_price(db, price_id):
    return await crud.get_record(db, Price, Price.id == price_id)


async def create_price(db, product_id, user_id, data: PriceCreate) -> Price | None:
    if not await product_owned(db, product_id, user_id):
        return None
    return await crud.create_record(db, Price, {"product_id": product_id, **data.model_dump()})


async def update_price(db, price, data: PriceUpdate):
    return await crud.update_record(db, price, data.model_dump(exclude_unset=True))


async def delete_price(db, price):
    await crud.delete_record(db, price)
