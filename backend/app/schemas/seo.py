import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

SeoEntityType = Literal["product", "category", "collection", "store", "page"]


class SeoDataCreate(BaseModel):
    entity_type: SeoEntityType
    entity_id: uuid.UUID
    title: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=2000)
    keywords: list[str] | None = None
    slug: str | None = Field(None, max_length=255)
    canonical_url: str | None = Field(None, max_length=500)
    is_indexable: bool = True


class SeoDataUpdate(BaseModel):
    title: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=2000)
    keywords: list[str] | None = None
    slug: str | None = Field(None, max_length=255)
    canonical_url: str | None = Field(None, max_length=500)
    is_indexable: bool | None = None


class SeoDataResponse(BaseModel):
    id: uuid.UUID
    entity_type: str
    entity_id: uuid.UUID
    title: str | None = None
    description: str | None = None
    keywords: list[str] | None = None
    slug: str | None = None
    canonical_url: str | None = None
    is_indexable: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SeoScoreCreate(BaseModel):
    overall_score: float | None = Field(None, ge=0, le=100)
    keyword_score: float | None = Field(None, ge=0, le=100)
    meta_score: float | None = Field(None, ge=0, le=100)
    structure_score: float | None = Field(None, ge=0, le=100)
    detail: dict | None = None


class SeoScoreUpdate(BaseModel):
    overall_score: float | None = Field(None, ge=0, le=100)
    keyword_score: float | None = Field(None, ge=0, le=100)
    meta_score: float | None = Field(None, ge=0, le=100)
    structure_score: float | None = Field(None, ge=0, le=100)
    detail: dict | None = None


class SeoScoreResponse(BaseModel):
    id: uuid.UUID
    seo_data_id: uuid.UUID
    overall_score: float | None = None
    keyword_score: float | None = None
    meta_score: float | None = None
    structure_score: float | None = None
    detail: dict | None = None
    calculated_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class SeoGenerateResponse(BaseModel):
    seo_data: SeoDataResponse
    seo_score: SeoScoreResponse
    message: str = "SEO metadata and score generated successfully"

