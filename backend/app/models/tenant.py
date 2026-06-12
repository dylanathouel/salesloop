import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import TenantPlan, db_enum

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.directive import Directive
    from app.models.report import Report
    from app.models.training_content import TrainingContent
    from app.models.user import User


class Tenant(Base):
    __tablename__ = "tenant"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    plan: Mapped[TenantPlan] = mapped_column(
        db_enum(TenantPlan, "tenant_plan"), nullable=False, default=TenantPlan.TRIAL
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relations: everything in the platform belongs to a tenant
    users: Mapped[list["User"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    reports: Mapped[list["Report"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    directives: Mapped[list["Directive"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    training_contents: Mapped[list["TrainingContent"]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
