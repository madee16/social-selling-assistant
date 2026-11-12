import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

SessionStatus = Literal["active", "closed", "escalated"]


class AISessionCreate(BaseModel):
    store_id: uuid.UUID | None = None
    buyer_id: uuid.UUID | None = None
    intent: str | None = Field(None, max_length=100)
    status: SessionStatus = "active"
    conversation_summary: str | None = None


class AISessionUpdate(BaseModel):
    intent: str | None = Field(None, max_length=100)
    status: SessionStatus | None = None
    conversation_summary: str | None = None


class AISessionResponse(BaseModel):
    id: uuid.UUID
    store_id: uuid.UUID | None = None
    buyer_id: uuid.UUID | None = None
    intent: str | None = None
    status: str
    conversation_summary: str | None = None
    total_messages: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AIMessageCreate(BaseModel):
    role: Literal["system", "user", "assistant", "tool"] = Field(min_length=1, max_length=20)
    content: str = Field(min_length=1)
    tool_calls: dict | None = None
    confidence: float | None = Field(None, ge=0, le=1)
    sequence: int = 0


class AIMessageResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    tool_calls: dict | None = None
    confidence: float | None = None
    sequence: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AIToolCallCreate(BaseModel):
    tool_name: str = Field(min_length=1, max_length=100)
    arguments: dict | None = None
    result: dict | None = None
    status: Literal["pending", "running", "completed", "failed"] = "pending"


class AIToolCallResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    message_id: uuid.UUID
    tool_name: str
    arguments: dict | None = None
    result: dict | None = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}
