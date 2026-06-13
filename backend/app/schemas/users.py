import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import UserRole


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    phone: str | None = None
    is_active: bool
    manager_id: uuid.UUID | None = None


class UserCreateRequest(BaseModel):
    """Account created by a manager/direction inside their own tenant."""

    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = Field(min_length=2, max_length=120)
    phone: str | None = None
    role: UserRole = UserRole.COMMERCIAL
    manager_id: uuid.UUID | None = None


class UserUpdateRequest(BaseModel):
    """Partial update; only provided fields are applied (manager_id=null detaches)."""

    is_active: bool | None = None
    manager_id: uuid.UUID | None = None


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str = Field(min_length=8)
