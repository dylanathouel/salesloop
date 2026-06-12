"""Training content upload: chunking, embedding, permissions, isolation."""

import httpx
from app.models.training_chunk import TrainingChunk
from app.models.user import User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import FakeEmbeddingProvider, auth_headers

DOC = {
    "title": "Gamme bio",
    "content": (
        "Notre gamme bio est certifiée AB et cultivée sans pesticides.\n\n"
        "Les produits bio se conservent 12 mois à température ambiante."
    ),
}


async def test_direction_uploads_content_chunked_and_embedded(
    client: httpx.AsyncClient, direction: User, db: AsyncSession
) -> None:
    response = await client.post("/training/", json=DOC, headers=auth_headers(direction))
    assert response.status_code == 201
    body = response.json()
    assert body["is_embedded"] is True
    assert body["chunk_metadata"]["chunk_count"] >= 1

    result = await db.execute(select(TrainingChunk))
    chunks = result.scalars().all()
    assert len(chunks) == body["chunk_metadata"]["chunk_count"]
    assert all(c.embedding is not None for c in chunks)


async def test_upload_degrades_when_embeddings_down(
    client: httpx.AsyncClient,
    direction: User,
    db: AsyncSession,
    fake_embedder: FakeEmbeddingProvider,
) -> None:
    fake_embedder.fail = True
    response = await client.post("/training/", json=DOC, headers=auth_headers(direction))
    assert response.status_code == 201
    assert response.json()["is_embedded"] is False

    result = await db.execute(select(TrainingChunk))
    assert all(c.embedding is None for c in result.scalars().all())


async def test_upload_reserved_to_direction(
    client: httpx.AsyncClient, manager: User, commercial: User
) -> None:
    for user in (manager, commercial):
        response = await client.post("/training/", json=DOC, headers=auth_headers(user))
        assert response.status_code == 403


async def test_listing_and_delete(
    client: httpx.AsyncClient, direction: User, manager: User, db: AsyncSession
) -> None:
    created = await client.post("/training/", json=DOC, headers=auth_headers(direction))
    content_id = created.json()["id"]

    listing = await client.get("/training/", headers=auth_headers(manager))
    assert [c["id"] for c in listing.json()] == [content_id]

    delete = await client.delete(f"/training/{content_id}", headers=auth_headers(direction))
    assert delete.status_code == 204

    # Chunks are gone with the content (FK cascade)
    result = await db.execute(select(TrainingChunk))
    assert result.scalars().all() == []


async def test_cross_tenant_training_delete_looks_like_404(
    client: httpx.AsyncClient, direction: User, other_tenant_direction: User
) -> None:
    created = await client.post(
        "/training/", json=DOC, headers=auth_headers(other_tenant_direction)
    )
    response = await client.delete(
        f"/training/{created.json()['id']}", headers=auth_headers(direction)
    )
    assert response.status_code == 404
