import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class BuyerCreate(BaseModel):
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    name: str | None = Field(None, max_length=255)
    preferences: dict | None = None


class BuyerUpdate(BaseModel):
    email: str | None = Field(None, max_length=255)
    phone: str | None = Field(None, max_length=50)
    name: str | None = Field(None, max_length=255)
    preferences: dict | None = None


class BuyerResponse(BaseModel):
    id: uuid.UUID
    email: str | None = None
    phone: str | None = None
    name: str | None = None
    preferences: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
