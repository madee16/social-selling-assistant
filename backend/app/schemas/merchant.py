import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class MerchantCreate(BaseModel):
    company_name: str = Field(min_length=1, max_length=255)
    verification_status: Literal["pending", "verified", "rejected"] = "pending"


class MerchantUpdate(BaseModel):
    company_name: str | None = Field(None, min_length=1, max_length=255)
    verification_status: Literal["pending", "verified", "rejected"] | None = None


class MerchantResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    company_name: str
    verification_status: str
    trust_score_ref: float | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class StoreCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(min_length=1, max_length=255, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    domain: str | None = Field(None, max_length=500)
    settings: dict | None = None
    status: Literal["active", "inactive", "suspended"] = "active"


class StoreUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    slug: str | None = Field(
        None, min_length=1, max_length=255, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    )
    domain: str | None = Field(None, max_length=500)
    settings: dict | None = None
    status: Literal["active", "inactive", "suspended"] | None = None


class StoreResponse(BaseModel):
    id: uuid.UUID
    merchant_id: uuid.UUID
    slug: str
    name: str
    domain: str | None = None
    settings: dict | None = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


class StoreMemberCreate(BaseModel):
    user_id: uuid.UUID
    role: Literal["admin", "manager", "staff", "viewer"] = Field(min_length=1, max_length=50)


class StoreMemberResponse(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID
    user_id: uuid.UUID
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}
