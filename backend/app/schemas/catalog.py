import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AttributeDefCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    attribute_type: Literal["text", "number", "boolean", "select", "multi_select"] = "text"
    values: list[str] | None = None
    is_required: bool = False
    is_filterable: bool = False
    sort_order: int = 0


class AttributeDefUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    attribute_type: Literal["text", "number", "boolean", "select", "multi_select"] | None = None
    values: list[str] | None = None
    is_required: bool | None = None
    is_filterable: bool | None = None
    sort_order: int | None = None


class AttributeDefResponse(BaseModel):
    id: uuid.UUID
    merchant_id: uuid.UUID
    name: str
    attribute_type: str
    values: list[str] | None = None
    is_required: bool
    is_filterable: bool
    sort_order: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductAttributeCreate(BaseModel):
    attribute_def_id: uuid.UUID
    value: str = Field(min_length=1)


class ProductAttributeResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    attribute_def_id: uuid.UUID
    value: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductVariantCreate(BaseModel):
    sku: str | None = Field(None, max_length=255)
    name: str | None = Field(None, max_length=255)
    options: dict | None = None
    quantity: int = Field(default=0, ge=0)


class ProductVariantUpdate(BaseModel):
    sku: str | None = Field(None, max_length=255)
    name: str | None = Field(None, max_length=255)
    options: dict | None = None
    quantity: int | None = Field(None, ge=0)


class ProductVariantResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    sku: str | None = None
    name: str | None = None
    options: dict | None = None
    quantity: int
    created_at: datetime

    model_config = {"from_attributes": True}


class InventoryCreate(BaseModel):
    store_id: uuid.UUID
    quantity: int = Field(default=0, ge=0)
    reserved_quantity: int = Field(default=0, ge=0)
    low_stock_threshold: int = Field(default=5, ge=0)


class InventoryUpdate(BaseModel):
    quantity: int | None = Field(None, ge=0)
    reserved_quantity: int | None = Field(None, ge=0)
    low_stock_threshold: int | None = Field(None, ge=0)


class InventoryResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    store_id: uuid.UUID
    quantity: int
    reserved_quantity: int
    low_stock_threshold: int
    updated_at: datetime

    model_config = {"from_attributes": True}


class PriceCreate(BaseModel):
    store_id: uuid.UUID
    amount: float = Field(ge=0, le=999999.99)
    currency: str = Field(default="TND", min_length=3, max_length=10)
    sale_price: float | None = Field(None, ge=0, le=999999.99)
    effective_from: datetime | None = None
    effective_to: datetime | None = None


class PriceUpdate(BaseModel):
    amount: float | None = Field(None, ge=0, le=999999.99)
    currency: str | None = Field(None, min_length=3, max_length=10)
    sale_price: float | None = Field(None, ge=0, le=999999.99)
    effective_from: datetime | None = None
    effective_to: datetime | None = None


class PriceResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    store_id: uuid.UUID
    amount: float
    currency: str
    sale_price: float | None = None
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
