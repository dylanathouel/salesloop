"""Authentication business logic (registration, login)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest


def _token_for(user: User) -> str:
    return create_access_token(
        {"sub": str(user.id), "role": user.role.value, "tenant_id": str(user.tenant_id)}
    )


async def register_user(db: AsyncSession, data: RegisterRequest) -> tuple[User, str]:
    """Create a user in an existing tenant and return it with its token."""
    # Email is globally unique on the platform (login without tenant)
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise ConflictError("Cet email est déjà utilisé")

    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        phone=data.phone,
        role=data.role,
        tenant_id=data.tenant_id,
        manager_id=data.manager_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user, _token_for(user)


async def login_user(db: AsyncSession, data: LoginRequest) -> tuple[User, str]:
    """Verify credentials and return the user with a fresh token."""
    result = await db.execute(
        select(User).where(User.email == data.email, User.tenant_id == data.tenant_id)
    )
    user = result.scalar_one_or_none()

    if user is None or not verify_password(data.password, user.password_hash):
        raise UnauthorizedError("Email ou mot de passe incorrect")
    if not user.is_active:
        raise ForbiddenError("Compte désactivé")

    return user, _token_for(user)
