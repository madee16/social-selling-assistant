import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ProductScoreCreate(BaseModel):
    store_id: uuid.UUID
    score: float = Field(ge=0, le=100)
    score_type: str = Field(default="ai", min_length=1, max_length=50)
    detail: dict | None = None


class ProductScoreUpdate(BaseModel):
    score: float | None = Field(None, ge=0, le=100)
    score_type: str | None = Field(None, min_length=1, max_length=50)
    detail: dict | None = None


class ProductScoreResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    store_id: uuid.UUID
    score: float
    score_type: str
    detail: dict | None = None
    calculated_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SellerTrustScoreCreate(BaseModel):
    score: float = Field(ge=0, le=100)
    components: dict | None = None
    level: str = Field(default="bronze", min_length=1, max_length=20)


class SellerTrustScoreUpdate(BaseModel):
    score: float | None = Field(None, ge=0, le=100)
    components: dict | None = None
    level: str | None = Field(None, min_length=1, max_length=20)


class SellerTrustScoreResponse(BaseModel):
    id: uuid.UUID
    seller_id: uuid.UUID
    score: float
    components: dict | None = None
    level: str
    calculated_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
