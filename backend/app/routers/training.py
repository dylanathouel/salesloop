import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_direction, require_manager
from app.database import get_db
from app.models.user import User
from app.schemas.training import TrainingContentCreate, TrainingContentResponse
from app.services import training as training_service
from app.services.rag.embeddings import EmbeddingProvider, get_embedding_provider

router = APIRouter(prefix="/training", tags=["training"])

DbSession = Annotated[AsyncSession, Depends(get_db)]
Direction = Annotated[User, require_direction]
Manager = Annotated[User, require_manager]
Embedder = Annotated[EmbeddingProvider, Depends(get_embedding_provider)]


@router.post("/", response_model=TrainingContentResponse, status_code=status.HTTP_201_CREATED)
async def upload_training_content(
    data: TrainingContentCreate, db: DbSession, actor: Direction, embedder: Embedder
) -> TrainingContentResponse:
    """Upload a training document (direction only): chunked then embedded."""
    content = await training_service.create_training_content(db, embedder, actor, data)
    return TrainingContentResponse.model_validate(content)


@router.get("/", response_model=list[TrainingContentResponse])
async def list_training_contents(db: DbSession, actor: Manager) -> list[TrainingContentResponse]:
    contents = await training_service.list_training_contents(db, actor)
    return [TrainingContentResponse.model_validate(c) for c in contents]


@router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_training_content(content_id: uuid.UUID, db: DbSession, actor: Direction) -> None:
    await training_service.delete_training_content(db, actor, content_id)
