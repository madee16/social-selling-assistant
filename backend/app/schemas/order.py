import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

OrderStatus = Literal["pending", "confirmed", "preparing", "shipped", "delivered", "cancelled"]


class OrderItemCreate(BaseModel):
    product_id: uuid.UUID
    quantity: int = Field(gt=0)
    # Retained for frontend compatibility. The server always uses the catalog price.
    unit_price: float = Field(ge=0)


class OrderCreate(BaseModel):
    conversation_id: uuid.UUID | None = None
    customer_name: str = Field(min_length=1, max_length=255)
    customer_phone: str | None = None
    customer_address: str | None = None
    items: list[OrderItemCreate] = Field(min_length=1)


class OrderItemResponse(BaseModel):
    id: uuid.UUID
    order_id: uuid.UUID
    product_id: uuid.UUID | None
    product_name: str | None = None
    quantity: int
    unit_price: float
    subtotal: float

    model_config = {"from_attributes": True}



class OrderResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    conversation_id: uuid.UUID | None = None
    customer_name: str
    customer_phone: str | None = None
    customer_address: str | None = None
    status: str
    total_amount: float
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemResponse] = []

    model_config = {"from_attributes": True}


class OrderListResponse(BaseModel):
    items: list[OrderResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class OrderStatusUpdate(BaseModel):
    status: OrderStatus
