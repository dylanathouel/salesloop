"""Similarity search over training chunks, strictly filtered by tenant."""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.training_chunk import TrainingChunk
from app.models.training_content import TrainingContent
from app.services.rag.embeddings import EmbeddingProvider

DEFAULT_TOP_K = 4


@dataclass(frozen=True)
class RetrievedChunk:
    title: str
    text: str


async def retrieve(
    db: AsyncSession,
    embedder: EmbeddingProvider,
    tenant_id: uuid.UUID,
    query: str,
    k: int = DEFAULT_TOP_K,
) -> list[RetrievedChunk]:
    """Return the tenant's k most similar chunks for `query` (cosine distance).

    Raises EmbeddingUnavailableError if the embedding provider is down;
    callers decide whether to degrade (the trainer coaches without context).
    """
    query_vector = (await embedder.embed([query]))[0]

    result = await db.execute(
        select(TrainingChunk.chunk_text, TrainingContent.title)
        .join(TrainingContent, TrainingChunk.training_content_id == TrainingContent.id)
        .where(
            TrainingContent.tenant_id == tenant_id,
            TrainingChunk.embedding.is_not(None),
        )
        .order_by(TrainingChunk.embedding.cosine_distance(query_vector))
        .limit(k)
    )
    return [RetrievedChunk(title=title, text=text) for text, title in result.all()]
