"""Reusable FastAPI dependencies for authentication and role-based access."""

from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_access_token
from app.database import get_db
from app.models.enums import UserRole
from app.models.user import User

security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Resolve the authenticated user from the Bearer token."""
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise UnauthorizedError("Token invalide ou expiré")

    user_id = payload.get("sub")
    if user_id is None:
        raise UnauthorizedError("Token invalide")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise UnauthorizedError("Utilisateur introuvable ou désactivé")

    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> object:
    """Dependency factory: only let through users having one of `roles`."""

    async def checker(current_user: CurrentUser) -> User:
        if current_user.role not in roles:
            raise ForbiddenError("Accès refusé : rôle insuffisant")
        return current_user

    return Depends(checker)


# Ready-to-use role gates (manager and above, direction only)
require_manager = require_roles(UserRole.MANAGER, UserRole.DIRECTION)
require_direction = require_roles(UserRole.DIRECTION)
