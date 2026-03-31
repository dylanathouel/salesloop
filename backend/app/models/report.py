import uuid
from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, ForeignKey, String, Table, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# Table de liaison many-to-many entre Report et Conversation
report_conversation = Table(
    "report_conversation",
    Base.metadata,
    Column("report_id", UUID(as_uuid=True), ForeignKey("report.id", ondelete="CASCADE"), primary_key=True),
    Column("conversation_id", UUID(as_uuid=True), ForeignKey("conversation.id", ondelete="CASCADE"), primary_key=True),
)


class Report(Base):
    __tablename__ = "report"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    period_type: Mapped[str] = mapped_column(String, nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    insights: Mapped[dict] = mapped_column(JSONB, default={})
    metrics: Mapped[dict] = mapped_column(JSONB, default={})
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Relations
    tenant = relationship("Tenant", back_populates="reports")
    conversations = relationship("Conversation", secondary=report_conversation)