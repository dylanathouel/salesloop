"""User management, always scoped to the current user's tenant and role.

Visibility rules: a commercial sees themselves, a manager sees their team
(plus themselves), direction sees the whole tenant.
"""

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError, UnauthorizedError
from app.core.security import hash_password, verify_password
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.users import PasswordChangeRequest, UserCreateRequest, UserUpdateRequest
from app.services.auth import ensure_email_available


async def list_visible_users(db: AsyncSession, current_user: User) -> list[User]:
    """Return the users visible to `current_user` according to their role."""
    query = select(User).where(User.tenant_id == current_user.tenant_id)

    if current_user.role == UserRole.COMMERCIAL:
        query = query.where(User.id == current_user.id)
    elif current_user.role == UserRole.MANAGER:
        query = query.where(or_(User.manager_id == current_user.id, User.id == current_user.id))

    result = await db.execute(query.order_by(User.full_name))
    return list(result.scalars().all())


async def _get_tenant_user(db: AsyncSession, actor: User, user_id: uuid.UUID) -> User:
    """Load a user of the actor's tenant; cross-tenant lookups look like a 404."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or user.tenant_id != actor.tenant_id:
        raise NotFoundError("Utilisateur introuvable")
    return user


async def _validate_manager_assignment(
    db: AsyncSession, actor: User, manager_id: uuid.UUID
) -> None:
    manager = await _get_tenant_user(db, actor, manager_id)
    if manager.role != UserRole.MANAGER:
        raise ForbiddenError("Le rattachement doit pointer vers un utilisateur de rôle manager")


async def create_user(db: AsyncSession, creator: User, data: UserCreateRequest) -> User:
    """Create an account in the creator's tenant.

    Direction creates any role; a manager only creates commercials, which are
    automatically attached to them.
    """
    await ensure_email_available(db, data.email)

    manager_id = data.manager_id
    if creator.role == UserRole.MANAGER:
        if data.role != UserRole.COMMERCIAL:
            raise ForbiddenError("Un manager ne peut créer que des comptes commerciaux")
        if manager_id is not None and manager_id != creator.id:
            raise ForbiddenError("Un manager ne peut rattacher un commercial qu'à lui-même")
        manager_id = creator.id
    elif manager_id is not None:
        await _validate_manager_assignment(db, creator, manager_id)

    user = User(
        tenant_id=creator.tenant_id,
        email=data.email,
        password_hash=hash_password(data.password),
        full_name=data.full_name,
        phone=data.phone,
        role=data.role,
        manager_id=manager_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def update_user(
    db: AsyncSession,
    actor: User,
    user_id: uuid.UUID,
    data: UserUpdateRequest,
) -> User:
    """Patch a user (activation, manager attachment).

    A manager may only toggle `is_active` on their own team; changing
    `manager_id` is reserved to direction.
    """
    target = await _get_tenant_user(db, actor, user_id)
    changes = data.model_dump(exclude_unset=True)

    if actor.role == UserRole.MANAGER:
        if target.manager_id != actor.id:
            raise ForbiddenError("Accès limité aux membres de votre équipe")
        if "manager_id" in changes:
            raise ForbiddenError("Seule la direction peut modifier le rattachement manager")

    if changes.get("manager_id") is not None:
        if changes["manager_id"] == target.id:
            raise ForbiddenError("Un utilisateur ne peut pas être son propre manager")
        await _validate_manager_assignment(db, actor, changes["manager_id"])

    for field, value in changes.items():
        setattr(target, field, value)

    await db.commit()
    await db.refresh(target)
    return target


async def change_password(db: AsyncSession, user: User, data: PasswordChangeRequest) -> None:
    """Change the current user's password after verifying the old one."""
    if not verify_password(data.old_password, user.password_hash):
        raise UnauthorizedError("Mot de passe actuel incorrect")
    user.password_hash = hash_password(data.new_password)
    await db.commit()
