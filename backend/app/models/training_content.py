import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TrainingContent(Base):
    __tablename__ = "training_content"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    raw_content: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str] = mapped_column(String, nullable=False)
    chunk_metadata: Mapped[dict] = mapped_column(JSONB, default={})
    is_embedded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relations
    tenant = relationship("Tenant", back_populates="training_contents")