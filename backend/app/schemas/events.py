import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

EventType = Literal["holiday", "season", "campaign", "sale", "custom"]


class EventCreate(BaseModel):
    event_type: EventType = "custom"
    entity_type: str | None = Field(None, max_length=100)
    entity_id: str | None = None
    payload: dict | None = None
    meta_data: dict | None = None


class EventUpdate(BaseModel):
    event_type: EventType | None = None
    entity_type: str | None = Field(None, max_length=100)
    entity_id: str | None = None
    payload: dict | None = None
    meta_data: dict | None = None


class EventResponse(BaseModel):
    id: uuid.UUID
    event_type: str
    entity_type: str | None = None
    entity_id: str | None = None
    payload: dict | None = None
    meta_data: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EventCollectionCreate(BaseModel):
    collection_type: str = Field(min_length=1, max_length=100)
    collection_id: str = Field(min_length=1)
    meta_data: dict | None = None


class EventCollectionResponse(BaseModel):
    id: uuid.UUID
    event_id: uuid.UUID
    collection_type: str
    collection_id: str
    meta_data: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EventProductGapCreate(BaseModel):
    product_id: uuid.UUID
    gap_type: str = Field(min_length=1, max_length=100)
    details: dict | None = None


class EventProductGapResponse(BaseModel):
    id: uuid.UUID
    event_collection_id: uuid.UUID
    product_id: uuid.UUID
    gap_type: str
    details: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
