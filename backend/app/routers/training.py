import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Form, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidStateError
from app.core.permissions import require_direction, require_manager
from app.database import get_db
from app.models.user import User
from app.schemas.training import (
    TrainingContentCreate,
    TrainingContentResponse,
    TrainingContentUpdate,
)
from app.services import training as training_service
from app.services.rag.embeddings import EmbeddingProvider, get_embedding_provider
from app.services.training import MAX_UPLOAD_BYTES, MIN_TEXT_CHARS

router = APIRouter(prefix="/training", tags=["training"])

DbSession = Annotated[AsyncSession, Depends(get_db)]
Direction = Annotated[User, require_direction]
Manager = Annotated[User, require_manager]
Embedder = Annotated[EmbeddingProvider, Depends(get_embedding_provider)]


@router.post("/", response_model=TrainingContentResponse, status_code=status.HTTP_201_CREATED)
async def upload_training_content(
    data: TrainingContentCreate, db: DbSession, actor: Direction, embedder: Embedder
) -> TrainingContentResponse:
    """Upload a raw-text training document (direction only)."""
    content = await training_service.create_training_content(db, embedder, actor, data)
    return TrainingContentResponse.model_validate(content)


@router.post("/upload", response_model=TrainingContentResponse, status_code=status.HTTP_201_CREATED)
async def upload_training_file(
    file: UploadFile,
    title: Annotated[str, Form(min_length=2, max_length=200)],
    db: DbSession,
    actor: Direction,
    embedder: Embedder,
) -> TrainingContentResponse:
    """Upload a training document as a file: PDF (text layer) or plain text."""
    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise InvalidStateError("Fichier trop volumineux (10 Mo maximum)")

    is_pdf = (file.content_type == "application/pdf") or (file.filename or "").lower().endswith(
        ".pdf"
    )
    if is_pdf:
        text = training_service.extract_pdf_text(raw)
        content_type = "pdf"
    else:
        text = raw.decode("utf-8", errors="replace")
        content_type = "text"

    if len(text.strip()) < MIN_TEXT_CHARS:
        raise InvalidStateError("Le document ne contient pas assez de texte")

    data = TrainingContentCreate(title=title, content=text, content_type=content_type)
    content = await training_service.create_training_content(db, embedder, actor, data)
    return TrainingContentResponse.model_validate(content)


@router.get("/", response_model=list[TrainingContentResponse])
async def list_training_contents(db: DbSession, actor: Manager) -> list[TrainingContentResponse]:
    contents = await training_service.list_training_contents(db, actor)
    return [TrainingContentResponse.model_validate(c) for c in contents]


@router.patch("/{content_id}", response_model=TrainingContentResponse)
async def update_training_content(
    content_id: uuid.UUID,
    data: TrainingContentUpdate,
    db: DbSession,
    actor: Direction,
    embedder: Embedder,
) -> TrainingContentResponse:
    """Edit a document (direction only); a content change re-indexes it."""
    content = await training_service.update_training_content(db, embedder, actor, content_id, data)
    return TrainingContentResponse.model_validate(content)


@router.post("/{content_id}/reindex", response_model=TrainingContentResponse)
async def reindex_training_content(
    content_id: uuid.UUID, db: DbSession, actor: Direction, embedder: Embedder
) -> TrainingContentResponse:
    """Re-embed a document uploaded while embeddings were unavailable."""
    content = await training_service.reindex_training_content(db, embedder, actor, content_id)
    return TrainingContentResponse.model_validate(content)


@router.delete("/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_training_content(content_id: uuid.UUID, db: DbSession, actor: Direction) -> None:
    await training_service.delete_training_content(db, actor, content_id)
