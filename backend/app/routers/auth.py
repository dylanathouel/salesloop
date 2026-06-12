from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

DbSession = Annotated[AsyncSession, Depends(get_db)]


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterRequest, db: DbSession) -> AuthResponse:
    user, token = await auth_service.register_user(db, data)
    return AuthResponse(access_token=token, user_id=user.id, role=user.role)


@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, db: DbSession) -> AuthResponse:
    user, token = await auth_service.login_user(db, data)
    return AuthResponse(access_token=token, user_id=user.id, role=user.role)
