import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    conversation_id: uuid.UUID | None = None
    customer_name: str | None = Field(None, max_length=255)
    customer_phone: str | None = Field(None, max_length=50)
    customer_address: str | None = Field(None, max_length=500)
    language: str | None = Field(None, max_length=10)
    message: str = Field(min_length=1, max_length=5000)


class CreatedOrderInfo(BaseModel):
    id: uuid.UUID
    total: float
    items: int


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    reply: str
    language: str | None = "fr"
    suggested_products: list[dict] | None = None
    order: CreatedOrderInfo | None = None


class ConversationResponse(BaseModel):
    id: uuid.UUID
    customer_name: str | None = None
    customer_phone: str | None = None
    customer_address: str | None = None
    language: str | None = None
    platform: str | None = None
    platform_conversation_id: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    language: str | None = None
    extra_data: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetailResponse(BaseModel):
    conversation: ConversationResponse
    messages: list[MessageResponse]
