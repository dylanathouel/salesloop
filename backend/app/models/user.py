import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    __tablename__ = "user"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tenant.id", ondelete="CASCADE"), nullable=False)
    manager_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    email: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relations
    tenant = relationship("Tenant", back_populates="users")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    directives = relationship("Directive", back_populates="created_by_user", cascade="all, delete-orphan")

    # Relation manager ↔ commerciaux (self-referential)
    manager = relationship("User", remote_side=[id], back_populates="team_members")
    team_members = relationship("User", back_populates="manager")