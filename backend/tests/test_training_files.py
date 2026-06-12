"""PDF/file upload, document edition and re-indexing."""

import io

import httpx
from app.models.training_chunk import TrainingChunk
from app.models.user import User
from fpdf import FPDF
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import FakeEmbeddingProvider, auth_headers

PDF_SENTENCE = "La gamme bio est certifiee AB et se conserve douze mois a temperature ambiante."


def _pdf_bytes(text: str) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.multi_cell(0, 10, text)
    return bytes(pdf.output())


async def test_pdf_upload_extracts_text_and_indexes(
    client: httpx.AsyncClient, direction: User
) -> None:
    response = await client.post(
        "/training/upload",
        data={"title": "Fiche gamme bio"},
        files={"file": ("fiche.pdf", io.BytesIO(_pdf_bytes(PDF_SENTENCE)), "application/pdf")},
        headers=auth_headers(direction),
    )
    assert response.status_code == 201
    body = response.json()
    assert body["content_type"] == "pdf"
    assert body["is_embedded"] is True
    assert "certifiee AB" in body["raw_content"]


async def test_scanned_pdf_without_text_rejected(
    client: httpx.AsyncClient, direction: User
) -> None:
    pdf = FPDF()
    pdf.add_page()  # blank page: no text layer, like a scanned document
    response = await client.post(
        "/training/upload",
        data={"title": "Scan illisible"},
        files={"file": ("scan.pdf", io.BytesIO(bytes(pdf.output())), "application/pdf")},
        headers=auth_headers(direction),
    )
    assert response.status_code == 400


async def test_plain_text_file_upload(client: httpx.AsyncClient, direction: User) -> None:
    content = "Les conditions de livraison standard sont de 48 heures ouvrees."
    response = await client.post(
        "/training/upload",
        data={"title": "Livraison"},
        files={"file": ("livraison.txt", io.BytesIO(content.encode()), "text/plain")},
        headers=auth_headers(direction),
    )
    assert response.status_code == 201
    assert response.json()["content_type"] == "text"
    assert response.json()["raw_content"] == content


async def test_file_upload_reserved_to_direction(client: httpx.AsyncClient, manager: User) -> None:
    response = await client.post(
        "/training/upload",
        data={"title": "Interdit"},
        files={"file": ("doc.txt", io.BytesIO(b"x" * 50), "text/plain")},
        headers=auth_headers(manager),
    )
    assert response.status_code == 403


async def test_edit_title_keeps_chunks(
    client: httpx.AsyncClient, direction: User, db: AsyncSession
) -> None:
    created = await client.post(
        "/training/",
        json={"title": "Ancien titre", "content": "Contenu initial du document de formation."},
        headers=auth_headers(direction),
    )
    content_id = created.json()["id"]

    response = await client.patch(
        f"/training/{content_id}",
        json={"title": "Nouveau titre"},
        headers=auth_headers(direction),
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Nouveau titre"
    assert response.json()["raw_content"] == "Contenu initial du document de formation."


async def test_edit_content_rechunks_and_reembeds(
    client: httpx.AsyncClient, direction: User, db: AsyncSession
) -> None:
    created = await client.post(
        "/training/",
        json={"title": "Doc", "content": "Contenu initial du document de formation."},
        headers=auth_headers(direction),
    )
    content_id = created.json()["id"]

    new_content = "Contenu entièrement réécrit qui parle de la gamme bio et des prix."
    response = await client.patch(
        f"/training/{content_id}",
        json={"content": new_content},
        headers=auth_headers(direction),
    )
    assert response.status_code == 200
    assert response.json()["is_embedded"] is True

    result = await db.execute(select(TrainingChunk))
    chunks = result.scalars().all()
    assert len(chunks) == response.json()["chunk_metadata"]["chunk_count"]
    assert all(c.chunk_text == new_content for c in chunks)


async def test_reindex_recovers_unembedded_document(
    client: httpx.AsyncClient,
    direction: User,
    fake_embedder: FakeEmbeddingProvider,
) -> None:
    # Uploaded while the embedding provider is down -> stored unembedded
    fake_embedder.fail = True
    created = await client.post(
        "/training/",
        json={"title": "Doc orphelin", "content": "Document stocké sans vectorisation."},
        headers=auth_headers(direction),
    )
    assert created.json()["is_embedded"] is False

    # Provider back up: reindex embeds the existing chunks
    fake_embedder.fail = False
    response = await client.post(
        f"/training/{created.json()['id']}/reindex", headers=auth_headers(direction)
    )
    assert response.status_code == 200
    assert response.json()["is_embedded"] is True


async def test_reindex_fails_cleanly_when_still_down(
    client: httpx.AsyncClient,
    direction: User,
    fake_embedder: FakeEmbeddingProvider,
) -> None:
    fake_embedder.fail = True
    created = await client.post(
        "/training/",
        json={"title": "Doc orphelin", "content": "Document stocké sans vectorisation."},
        headers=auth_headers(direction),
    )

    response = await client.post(
        f"/training/{created.json()['id']}/reindex", headers=auth_headers(direction)
    )
    assert response.status_code == 503


async def test_cross_tenant_edit_looks_like_404(
    client: httpx.AsyncClient, direction: User, other_tenant_direction: User
) -> None:
    created = await client.post(
        "/training/",
        json={"title": "Doc B", "content": "Document du tenant B, inaccessible au tenant A."},
        headers=auth_headers(other_tenant_direction),
    )
    response = await client.patch(
        f"/training/{created.json()['id']}",
        json={"title": "Piraté"},
        headers=auth_headers(direction),
    )
    assert response.status_code == 404
