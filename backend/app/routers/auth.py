from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.permissions import require_manager
from app.core.ratelimit import limiter
from app.database import get_db
from app.models.user import User
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest
from app.schemas.users import UserCreateRequest, UserResponse
from app.services import auth as auth_service
from app.services import users as users_service

router = APIRouter(prefix="/auth", tags=["auth"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.auth_rate_limit)
async def register(request: Request, data: RegisterRequest, db: DbSession) -> AuthResponse:
    """Company signup: creates the tenant and its first `direction` user."""
    user, token = await auth_service.register_company(db, data)
    return AuthResponse(access_token=token, user_id=user.id, role=user.role)


@router.post("/login", response_model=AuthResponse)
@limiter.limit(settings.auth_rate_limit)
async def login(request: Request, data: LoginRequest, db: DbSession) -> AuthResponse:
    user, token = await auth_service.login_user(db, data)
    return AuthResponse(access_token=token, user_id=user.id, role=user.role)


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    data: UserCreateRequest,
    db: DbSession,
    creator: Annotated[User, require_manager],
) -> UserResponse:
    """Manager/direction creates an account inside their own tenant."""
    user = await users_service.create_user(db, creator, data)
    return UserResponse.model_validate(user)
