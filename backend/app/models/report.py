import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Column, Date, DateTime, ForeignKey, Table, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import ReportPeriodType, db_enum

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.tenant import Tenant


# Many-to-many link between a report and the conversations it summarizes
report_conversation = Table(
    "report_conversation",
    Base.metadata,
    Column(
        "report_id",
        UUID(as_uuid=True),
        ForeignKey("report.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "conversation_id",
        UUID(as_uuid=True),
        ForeignKey("conversation.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Report(Base):
    __tablename__ = "report"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True
    )
    period_type: Mapped[ReportPeriodType] = mapped_column(
        db_enum(ReportPeriodType, "report_period_type"), nullable=False
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    insights: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relations
    tenant: Mapped["Tenant"] = relationship(back_populates="reports")
    conversations: Mapped[list["Conversation"]] = relationship(secondary=report_conversation)
