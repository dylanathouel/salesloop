"""Training content management: upload, chunking, embedding, deletion.

If the embedding provider is down or not configured, the upload still
succeeds: chunks are stored unembedded (is_embedded=False) and excluded
from retrieval until re-embedded.
"""

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EmbeddingUnavailableError, NotFoundError
from app.models.training_chunk import TrainingChunk
from app.models.training_content import TrainingContent
from app.models.user import User
from app.schemas.training import TrainingContentCreate
from app.services.rag.chunking import chunk_text
from app.services.rag.embeddings import EmbeddingProvider

logger = logging.getLogger(__name__)


async def create_training_content(
    db: AsyncSession,
    embedder: EmbeddingProvider,
    actor: User,
    data: TrainingContentCreate,
) -> TrainingContent:
    """Store a training document: chunk it, then try to embed the chunks."""
    chunks = chunk_text(data.content)

    embeddings: list[list[float]] | None = None
    try:
        embeddings = await embedder.embed(chunks)
    except EmbeddingUnavailableError as exc:
        logger.warning("Embeddings unavailable, storing content unembedded: %s", exc.message)

    content = TrainingContent(
        tenant_id=actor.tenant_id,
        title=data.title,
        raw_content=data.content,
        content_type=data.content_type,
        is_embedded=embeddings is not None,
        chunk_metadata={"chunk_count": len(chunks)},
    )
    db.add(content)
    await db.flush()

    for index, text in enumerate(chunks):
        db.add(
            TrainingChunk(
                training_content_id=content.id,
                chunk_text=text,
                chunk_index=index,
                embedding=embeddings[index] if embeddings is not None else None,
            )
        )

    await db.commit()
    await db.refresh(content)
    return content


async def list_training_contents(db: AsyncSession, actor: User) -> list[TrainingContent]:
    result = await db.execute(
        select(TrainingContent)
        .where(TrainingContent.tenant_id == actor.tenant_id)
        .order_by(TrainingContent.created_at.desc())
    )
    return list(result.scalars().all())


async def delete_training_content(db: AsyncSession, actor: User, content_id: uuid.UUID) -> None:
    result = await db.execute(select(TrainingContent).where(TrainingContent.id == content_id))
    content = result.scalar_one_or_none()
    if content is None or content.tenant_id != actor.tenant_id:
        raise NotFoundError("Contenu de formation introuvable")
    await db.delete(content)  # chunks follow via FK ondelete CASCADE
    await db.commit()
