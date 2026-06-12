import uuid

from pydantic import BaseModel, EmailStr

from app.models.enums import UserRole


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    phone: str | None = None
    role: UserRole = UserRole.COMMERCIAL
    tenant_id: uuid.UUID
    manager_id: uuid.UUID | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    tenant_id: uuid.UUID


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: uuid.UUID
    role: UserRole
