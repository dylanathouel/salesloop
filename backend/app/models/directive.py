import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import DirectivePriority, DirectiveStatus, db_enum

if TYPE_CHECKING:
    from app.models.tenant import Tenant
    from app.models.user import User


class Directive(Base):
    __tablename__ = "directive"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[DirectivePriority] = mapped_column(
        db_enum(DirectivePriority, "directive_priority"),
        nullable=False,
        default=DirectivePriority.MEDIUM,
    )
    status: Mapped[DirectiveStatus] = mapped_column(
        db_enum(DirectiveStatus, "directive_status"),
        nullable=False,
        default=DirectiveStatus.ACTIVE,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relations
    tenant: Mapped["Tenant"] = relationship(back_populates="directives")
    created_by_user: Mapped["User"] = relationship(back_populates="directives")
