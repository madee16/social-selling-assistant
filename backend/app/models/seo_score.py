import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class SeoScore(Base):
    __tablename__ = "seo_scores"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seo_data_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("seo_data.id", ondelete="CASCADE"), index=True)
    overall_score: Mapped[float | None] = mapped_column(nullable=True)
    keyword_score: Mapped[float | None] = mapped_column(nullable=True)
    meta_score: Mapped[float | None] = mapped_column(nullable=True)
    structure_score: Mapped[float | None] = mapped_column(nullable=True)
    detail: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    calculated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
