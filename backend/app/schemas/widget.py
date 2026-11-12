import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.utils.sanitize import normalize_domain, strip_html


class WidgetSettingsUpdate(BaseModel):
    enabled: bool | None = None
    title: str | None = Field(None, max_length=100)
    greeting: str | None = Field(None, max_length=500)
    primary_color: str | None = Field(None, max_length=7, pattern=r"^#[0-9a-fA-F]{6}$")
    position: str | None = Field(None, max_length=10)
    show_branding: bool | None = None
    allowed_domains: list[str] | None = None
    whatsapp_phone_number_id: str | None = Field(None, max_length=255)
    whatsapp_access_token: str | None = Field(None, max_length=500)
    messenger_page_id: str | None = Field(None, max_length=255)
    messenger_access_token: str | None = Field(None, max_length=500)
    webhook_verify_token: str | None = Field(None, max_length=100)

    @field_validator("title", "greeting")
    @classmethod
    def _sanitize_text(cls, value: str | None) -> str | None:
        return strip_html(value) if value is not None else value

    @field_validator("allowed_domains")
    @classmethod
    def _validate_allowed_domains(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        if len(value) > 50:
            raise ValueError("too many domains (max 50)")
        return [normalize_domain(domain) for domain in value]


class WidgetSettingsResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    enabled: bool
    title: str
    greeting: str
    primary_color: str
    position: str
    show_branding: bool
    allowed_domains: list[str] | None = None
    whatsapp_phone_number_id: str | None = None
    whatsapp_access_token: str | None = None
    messenger_page_id: str | None = None
    messenger_access_token: str | None = None
    webhook_verify_token: str = "social-selling-verify-2026"
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PublicWidgetConfig(BaseModel):
    title: str
    greeting: str
    primary_color: str
    position: str
    show_branding: bool
    company_name: str | None = None

    model_config = {"from_attributes": True}


class PublicChatRequest(BaseModel):
    widget_id: uuid.UUID
    message: str = Field(min_length=1, max_length=5000)
    customer_name: str | None = Field(None, max_length=255)
    customer_phone: str | None = Field(None, max_length=50)


class PublicChatResponse(BaseModel):
    reply: str
    conversation_id: uuid.UUID
    order: dict | None = None
    suggested_products: list[dict] | None = None
