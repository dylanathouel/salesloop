import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import UserRole, db_enum

if TYPE_CHECKING:
    from app.models.conversation import Conversation
    from app.models.directive import Directive
    from app.models.tenant import Tenant


class User(Base):
    __tablename__ = "user"
    __table_args__ = (
        # Email is globally unique (login without tenant), the per-tenant
        # constraint is kept as documentation of the tenancy boundary
        UniqueConstraint("email"),
        UniqueConstraint("tenant_id", "email"),
        Index("ix_user_tenant_role", "tenant_id", "role"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False, index=True
    )
    manager_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("user.id", ondelete="SET NULL"), nullable=True, index=True
    )
    email: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[UserRole] = mapped_column(db_enum(UserRole, "user_role"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relations
    tenant: Mapped["Tenant"] = relationship(back_populates="users")
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    directives: Mapped[list["Directive"]] = relationship(
        back_populates="created_by_user", cascade="all, delete-orphan"
    )

    # Manager <-> team members (self-referential)
    manager: Mapped["User | None"] = relationship(remote_side=[id], back_populates="team_members")
    team_members: Mapped[list["User"]] = relationship(back_populates="manager")
