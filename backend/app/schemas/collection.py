import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    store_id: uuid.UUID | None = None
    description: str | None = Field(None, max_length=2000)
    sort_order: int = 0
    is_visible: bool = True


class CollectionUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    slug: str | None = Field(
        None, min_length=1, max_length=255, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    )
    store_id: uuid.UUID | None = None
    description: str | None = Field(None, max_length=2000)
    sort_order: int | None = None
    is_visible: bool | None = None


class CollectionResponse(BaseModel):
    id: uuid.UUID
    merchant_id: uuid.UUID
    store_id: uuid.UUID | None = None
    name: str
    slug: str
    description: str | None = None
    sort_order: int
    is_visible: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
