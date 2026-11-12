import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ApprovalCreate(BaseModel):
    approval_type: str = Field(min_length=1, max_length=100)
    entity_type: str = Field(min_length=1, max_length=100)
    entity_id: str = Field(min_length=1)
    title: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=2000)
    approver_id: uuid.UUID | None = None
    status: Literal["pending", "approved", "rejected", "cancelled"] = "pending"
    meta_data: dict | None = None


class ApprovalUpdate(BaseModel):
    status: Literal["pending", "approved", "rejected", "cancelled"] | None = None
    approver_id: uuid.UUID | None = None
    rejection_reason: str | None = Field(None, max_length=2000)
    title: str | None = Field(None, max_length=255)
    description: str | None = Field(None, max_length=2000)


class ApprovalResponse(BaseModel):
    id: uuid.UUID
    approval_type: str
    entity_type: str
    entity_id: str
    title: str | None = None
    description: str | None = None
    requester_id: uuid.UUID
    approver_id: uuid.UUID | None = None
    status: str
    rejection_reason: str | None = None
    meta_data: dict | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AutomationRuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    event_type: str = Field(min_length=1, max_length=100)
    conditions: dict | None = None
    actions: dict | None = None
    is_active: bool = True
    priority: int = 0


class AutomationRuleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=2000)
    event_type: str | None = Field(None, min_length=1, max_length=100)
    conditions: dict | None = None
    actions: dict | None = None
    is_active: bool | None = None
    priority: int | None = None


class AutomationRuleResponse(BaseModel):
    id: uuid.UUID
    merchant_id: uuid.UUID
    name: str
    description: str | None = None
    event_type: str
    conditions: dict | None = None
    actions: dict | None = None
    is_active: bool
    priority: int
    execution_count: int
    last_executed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConsentRecordCreate(BaseModel):
    buyer_id: uuid.UUID
    consent_type: str = Field(min_length=1, max_length=100)
    consent_text: str | None = None
    granted: bool = False
    meta_data: dict | None = None


class ConsentRecordUpdate(BaseModel):
    granted: bool | None = None
    consent_text: str | None = None
    meta_data: dict | None = None


class ConsentRecordResponse(BaseModel):
    id: uuid.UUID
    buyer_id: uuid.UUID
    consent_type: str
    consent_text: str | None = None
    granted: bool
    meta_data: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditLogCreate(BaseModel):
    action: str = Field(min_length=1, max_length=100)
    entity_type: str | None = Field(None, max_length=100)
    entity_id: str | None = None
    details: dict | None = None
    ip_address: str | None = None


class AuditLogResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID | None = None
    action: str
    entity_type: str | None = None
    entity_id: str | None = None
    details: dict | None = None
    ip_address: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
