"""User listing and lookup, always scoped to the current user's tenant."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def list_tenant_users(db: AsyncSession, current_user: User) -> list[User]:
    """Every role only ever sees users of its own tenant."""
    result = await db.execute(select(User).where(User.tenant_id == current_user.tenant_id))
    return list(result.scalars().all())
