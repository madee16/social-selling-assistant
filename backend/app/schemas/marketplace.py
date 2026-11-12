import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ListingStatus = Literal["draft", "active", "inactive", "archived"]
SyncStatus = Literal["pending", "synced", "failed"]


class MarketplaceListingCreate(BaseModel):
    store_id: uuid.UUID
    marketplace: str = Field(min_length=1, max_length=100)
    marketplace_product_id: str | None = Field(None, max_length=255)
    listing_status: ListingStatus = "draft"
    sync_status: SyncStatus = "pending"


class MarketplaceListingUpdate(BaseModel):
    marketplace: str | None = Field(None, min_length=1, max_length=100)
    marketplace_product_id: str | None = Field(None, max_length=255)
    listing_status: ListingStatus | None = None
    sync_status: SyncStatus | None = None
    error_message: str | None = Field(None, max_length=2000)


class MarketplaceListingResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    store_id: uuid.UUID
    marketplace: str
    marketplace_product_id: str | None = None
    listing_status: str
    sync_status: str
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
