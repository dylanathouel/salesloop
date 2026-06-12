from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser
from app.database import get_db
from app.schemas.users import UserResponse
from app.services import users as users_service

router = APIRouter(prefix="/users", tags=["users"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.get("/", response_model=list[UserResponse])
async def list_users(current_user: CurrentUser, db: DbSession) -> list[UserResponse]:
    users = await users_service.list_tenant_users(db, current_user)
    return [UserResponse.model_validate(u) for u in users]
