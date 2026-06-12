import uuid
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser, require_manager
from app.database import get_db
from app.models.user import User
from app.schemas.users import UserResponse, UserUpdateRequest
from app.services import users as users_service

router = APIRouter(prefix="/users", tags=["users"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.get("/", response_model=list[UserResponse])
async def list_users(current_user: CurrentUser, db: DbSession) -> list[UserResponse]:
    users = await users_service.list_visible_users(db, current_user)
    return [UserResponse.model_validate(u) for u in users]


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdateRequest,
    db: DbSession,
    actor: Annotated[User, require_manager],
) -> UserResponse:
    """Activation / manager attachment. Managers are limited to their own team."""
    user = await users_service.update_user(db, actor, user_id, data)
    return UserResponse.model_validate(user)
