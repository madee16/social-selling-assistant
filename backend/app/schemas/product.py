import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.utils.sanitize import strip_html


class ProductCreate(BaseModel):
    name: str = Field(max_length=255)
    description: str | None = Field(None, max_length=2000)
    price: float = Field(ge=0, le=999999.99)
    category_id: uuid.UUID | None = None
    image_url: str | None = Field(None, max_length=500)
    stock_quantity: int = Field(default=0, ge=0, le=999999)

    @field_validator("name", "description")
    @classmethod
    def _sanitize_text(cls, value: str | None) -> str | None:
        return strip_html(value) if value is not None else value


class ProductUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=2000)
    price: float | None = Field(None, ge=0, le=999999.99)
    category_id: uuid.UUID | None = None
    image_url: str | None = Field(None, max_length=500)
    stock_quantity: int | None = Field(None, ge=0, le=999999)
    is_active: bool | None = None

    @field_validator("name", "description")
    @classmethod
    def _sanitize_text(cls, value: str | None) -> str | None:
        return strip_html(value) if value is not None else value


class ProductResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    price: float
    category_id: uuid.UUID | None = None
    image_url: str | None = None
    stock_quantity: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
