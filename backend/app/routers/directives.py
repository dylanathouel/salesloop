import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import CurrentUser, require_manager
from app.database import get_db
from app.models.user import User
from app.schemas.directives import DirectiveCreate, DirectiveResponse, DirectiveUpdate
from app.services import directives as directives_service

router = APIRouter(prefix="/directives", tags=["directives"])

DbSession = Annotated[AsyncSession, Depends(get_db)]
Manager = Annotated[User, require_manager]


@router.post("/", response_model=DirectiveResponse, status_code=status.HTTP_201_CREATED)
async def create_directive(
    data: DirectiveCreate, db: DbSession, actor: Manager
) -> DirectiveResponse:
    directive = await directives_service.create_directive(db, actor, data)
    return DirectiveResponse.model_validate(directive)


@router.get("/", response_model=list[DirectiveResponse])
async def list_directives(current_user: CurrentUser, db: DbSession) -> list[DirectiveResponse]:
    directives = await directives_service.list_directives(db, current_user)
    return [DirectiveResponse.model_validate(d) for d in directives]


@router.patch("/{directive_id}", response_model=DirectiveResponse)
async def update_directive(
    directive_id: uuid.UUID, data: DirectiveUpdate, db: DbSession, actor: Manager
) -> DirectiveResponse:
    directive = await directives_service.update_directive(db, actor, directive_id, data)
    return DirectiveResponse.model_validate(directive)


@router.delete("/{directive_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_directive(directive_id: uuid.UUID, db: DbSession, actor: Manager) -> None:
    await directives_service.delete_directive(db, actor, directive_id)
