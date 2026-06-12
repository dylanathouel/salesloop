"""Training content management: upload (text or PDF), chunking, embedding,
edition, re-indexing, deletion.

If the embedding provider is down or not configured, uploads and edits still
succeed: chunks are stored unembedded (is_embedded=False) and excluded from
retrieval until re-indexed.
"""

import io
import logging
import uuid

from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EmbeddingUnavailableError, InvalidStateError, NotFoundError
from app.models.training_chunk import TrainingChunk
from app.models.training_content import TrainingContent
from app.models.user import User
from app.schemas.training import TrainingContentCreate, TrainingContentUpdate
from app.services.rag.chunking import chunk_text
from app.services.rag.embeddings import EmbeddingProvider

logger = logging.getLogger(__name__)

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MIN_TEXT_CHARS = 20


def extract_pdf_text(data: bytes) -> str:
    """Extract the text layer of a PDF. Scanned PDFs (no text) are rejected."""
    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
    except PdfReadError as exc:
        raise InvalidStateError("Fichier PDF illisible ou corrompu") from exc

    text = "\n\n".join(p.strip() for p in pages if p.strip())
    if len(text.strip()) < MIN_TEXT_CHARS:
        raise InvalidStateError(
            "Ce PDF ne contient pas de texte exploitable (PDF scanné ?). "
            "Copie le contenu en texte ou utilise un PDF avec du texte."
        )
    return text


async def _chunk_and_embed(
    embedder: EmbeddingProvider, text: str
) -> tuple[list[str], list[list[float]] | None]:
    """Chunk a document and try to embed it; None embeddings = degraded."""
    chunks = chunk_text(text)
    try:
        return chunks, await embedder.embed(chunks)
    except EmbeddingUnavailableError as exc:
        logger.warning("Embeddings unavailable, storing content unembedded: %s", exc.message)
        return chunks, None


def _make_chunks(
    content_id: uuid.UUID, chunks: list[str], embeddings: list[list[float]] | None
) -> list[TrainingChunk]:
    return [
        TrainingChunk(
            training_content_id=content_id,
            chunk_text=text,
            chunk_index=index,
            embedding=embeddings[index] if embeddings is not None else None,
        )
        for index, text in enumerate(chunks)
    ]


async def _get_tenant_content(
    db: AsyncSession, actor: User, content_id: uuid.UUID
) -> TrainingContent:
    result = await db.execute(select(TrainingContent).where(TrainingContent.id == content_id))
    content = result.scalar_one_or_none()
    if content is None or content.tenant_id != actor.tenant_id:
        raise NotFoundError("Contenu de formation introuvable")
    return content


async def create_training_content(
    db: AsyncSession,
    embedder: EmbeddingProvider,
    actor: User,
    data: TrainingContentCreate,
) -> TrainingContent:
    """Store a training document: chunk it, then try to embed the chunks."""
    chunks, embeddings = await _chunk_and_embed(embedder, data.content)

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

    for chunk in _make_chunks(content.id, chunks, embeddings):
        db.add(chunk)

    await db.commit()
    await db.refresh(content)
    return content


async def update_training_content(
    db: AsyncSession,
    embedder: EmbeddingProvider,
    actor: User,
    content_id: uuid.UUID,
    data: TrainingContentUpdate,
) -> TrainingContent:
    """Edit a document; a content change rebuilds chunks and embeddings."""
    content = await _get_tenant_content(db, actor, content_id)

    if data.title is not None:
        content.title = data.title

    if data.content is not None and data.content != content.raw_content:
        chunks, embeddings = await _chunk_and_embed(embedder, data.content)
        await db.execute(
            delete(TrainingChunk).where(TrainingChunk.training_content_id == content.id)
        )
        for chunk in _make_chunks(content.id, chunks, embeddings):
            db.add(chunk)
        content.raw_content = data.content
        content.is_embedded = embeddings is not None
        content.chunk_metadata = {"chunk_count": len(chunks)}

    await db.commit()
    await db.refresh(content)
    return content


async def reindex_training_content(
    db: AsyncSession,
    embedder: EmbeddingProvider,
    actor: User,
    content_id: uuid.UUID,
) -> TrainingContent:
    """Re-embed the existing chunks of a document (e.g. uploaded while the
    embedding provider was down). Raises a clean 503 if it is still down."""
    content = await _get_tenant_content(db, actor, content_id)

    result = await db.execute(
        select(TrainingChunk)
        .where(TrainingChunk.training_content_id == content.id)
        .order_by(TrainingChunk.chunk_index)
    )
    chunks = list(result.scalars().all())
    if not chunks:
        raise InvalidStateError("Ce document n'a aucun segment à indexer")

    embeddings = await embedder.embed([chunk.chunk_text for chunk in chunks])
    for chunk, embedding in zip(chunks, embeddings, strict=True):
        chunk.embedding = embedding
    content.is_embedded = True

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
    content = await _get_tenant_content(db, actor, content_id)
    await db.delete(content)  # chunks follow via FK ondelete CASCADE
    await db.commit()
