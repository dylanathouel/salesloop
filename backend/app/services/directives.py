"""Directive business logic: manager guidelines pushed to the agents.

Active directives of a tenant are injected into the collector system prompt
of its commercials (see services/agents/collector.py).
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.directive import Directive
from app.models.enums import DirectivePriority, DirectiveStatus, UserRole
from app.models.user import User
from app.schemas.directives import DirectiveCreate, DirectiveUpdate

_PRIORITY_LABELS = {
    DirectivePriority.LOW: "priorité basse",
    DirectivePriority.MEDIUM: "priorité moyenne",
    DirectivePriority.HIGH: "PRIORITÉ HAUTE",
}


async def get_active_contents(db: AsyncSession, tenant_id: uuid.UUID) -> list[str]:
    """Active directives of the tenant, formatted for prompt injection."""
    result = await db.execute(
        select(Directive)
        .where(Directive.tenant_id == tenant_id, Directive.status == DirectiveStatus.ACTIVE)
        .order_by(Directive.created_at)
    )
    return [f"[{_PRIORITY_LABELS[d.priority]}] {d.content}" for d in result.scalars().all()]


async def list_directives(db: AsyncSession, current_user: User) -> list[Directive]:
    """Commercials only see active directives; manager+ see everything."""
    query = select(Directive).where(Directive.tenant_id == current_user.tenant_id)
    if current_user.role == UserRole.COMMERCIAL:
        query = query.where(Directive.status == DirectiveStatus.ACTIVE)

    result = await db.execute(query.order_by(Directive.created_at.desc()))
    return list(result.scalars().all())


async def _get_tenant_directive(
    db: AsyncSession, actor: User, directive_id: uuid.UUID
) -> Directive:
    result = await db.execute(select(Directive).where(Directive.id == directive_id))
    directive = result.scalar_one_or_none()
    if directive is None or directive.tenant_id != actor.tenant_id:
        raise NotFoundError("Directive introuvable")
    return directive


async def create_directive(db: AsyncSession, actor: User, data: DirectiveCreate) -> Directive:
    directive = Directive(
        tenant_id=actor.tenant_id,
        created_by=actor.id,
        content=data.content,
        priority=data.priority,
    )
    db.add(directive)
    await db.commit()
    await db.refresh(directive)
    return directive


async def update_directive(
    db: AsyncSession, actor: User, directive_id: uuid.UUID, data: DirectiveUpdate
) -> Directive:
    directive = await _get_tenant_directive(db, actor, directive_id)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(directive, field, value)
    await db.commit()
    await db.refresh(directive)
    return directive


async def delete_directive(db: AsyncSession, actor: User, directive_id: uuid.UUID) -> None:
    directive = await _get_tenant_directive(db, actor, directive_id)
    await db.delete(directive)
    await db.commit()
