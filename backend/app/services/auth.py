"""Authentication business logic (company signup, login)."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.enums import UserRole
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest


def token_for(user: User) -> str:
    return create_access_token(
        {"sub": str(user.id), "role": user.role.value, "tenant_id": str(user.tenant_id)}
    )


async def ensure_email_available(db: AsyncSession, email: str) -> None:
    """Emails are globally unique on the platform (login without tenant)."""
    result = await db.execute(select(User).where(User.email == email))
    if result.scalar_one_or_none():
        raise ConflictError("Cet email est déjà utilisé")


async def register_company(db: AsyncSession, data: RegisterRequest) -> tuple[User, str]:
    """Company signup: tenant + first `direction` user in a single transaction."""
    await ensure_email_available(db, data.email)

    tenant = Tenant(name=data.company_name)
    db.add(tenant)
    await db.flush()  # get tenant.id without committing yet

    user = User(
        tenant_id=tenant.id,
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        phone=data.phone,
        role=UserRole.DIRECTION,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user, token_for(user)


async def login_user(db: AsyncSession, data: LoginRequest) -> tuple[User, str]:
    """Verify credentials (email is globally unique) and return a fresh token."""
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(data.password, user.password_hash):
        raise UnauthorizedError("Email ou mot de passe incorrect")
    if not user.is_active:
        raise ForbiddenError("Compte désactivé")

    return user, token_for(user)
