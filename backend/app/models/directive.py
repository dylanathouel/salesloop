import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Directive(Base):
    __tablename__ = "directive"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String, nullable=False, default="medium")
    status: Mapped[str] = mapped_column(String, nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relations
    tenant = relationship("Tenant", back_populates="directives")
    created_by_user = relationship("User", back_populates="directives")