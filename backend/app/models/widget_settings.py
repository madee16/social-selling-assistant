import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base
from app.utils.crypto import EncryptedString


class WidgetSettings(Base):
    __tablename__ = "widget_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True)
    merchant_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("merchants.id", ondelete="SET NULL"), nullable=True, index=True)
    store_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("stores.id", ondelete="SET NULL"), nullable=True, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    title: Mapped[str] = mapped_column(String(100), default="Chat with us")
    greeting: Mapped[str] = mapped_column(String(500), default="Hi! How can I help you today?")
    primary_color: Mapped[str] = mapped_column(String(7), default="#2563eb")
    position: Mapped[str] = mapped_column(String(10), default="right")
    show_branding: Mapped[bool] = mapped_column(Boolean, default=True)
    allowed_domains: Mapped[dict] = mapped_column(JSONB, nullable=True, default=list)
    whatsapp_phone_number_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    whatsapp_access_token: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    messenger_page_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    messenger_access_token: Mapped[str | None] = mapped_column(EncryptedString, nullable=True)
    webhook_verify_token: Mapped[str] = mapped_column(String(100), default="social-selling-verify-2026")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
