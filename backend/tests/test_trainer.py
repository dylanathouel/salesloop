"""Trainer agent: RAG context injection, detected gaps, degraded mode."""

from datetime import UTC, datetime
from typing import Any

import httpx
import pytest
from app.models.conversation import Conversation
from app.models.enums import AgentType, ConversationStatus
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import FakeEmbeddingProvider, FakeLLMProvider, auth_headers

BIO_DOC = {
    "title": "Gamme bio",
    "content": "La gamme bio est certifiée AB, cultivée sans pesticides, marge de 35%.",
}
TENANT_B_DOC = {
    "title": "Secret du tenant B",
    "content": "Document confidentiel du tenant B sur la gamme bio concurrente.",
}


@pytest.fixture
def closed_collector_conversation(db: AsyncSession) -> Any:
    async def _make(user: User, extracted: dict[str, Any]) -> Conversation:
        conversation = Conversation(
            tenant_id=user.tenant_id,
            user_id=user.id,
            agent_type=AgentType.COLLECTOR,
            status=ConversationStatus.COMPLETED,
            extracted_data=extracted,
            ended_at=datetime.now(UTC),
        )
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        return conversation

    return _make


async def _start_trainer_conversation(client: httpx.AsyncClient, user: User) -> str:
    response = await client.post(
        "/conversations/", json={"agent_type": "trainer"}, headers=auth_headers(user)
    )
    assert response.status_code == 201
    conversation_id: str = response.json()["id"]
    return conversation_id


async def test_trainer_opening_targets_detected_gaps(
    client: httpx.AsyncClient,
    commercial: User,
    fake_llm: FakeLLMProvider,
    closed_collector_conversation: Any,
) -> None:
    await closed_collector_conversation(
        commercial,
        {"product_knowledge_gap": True, "knowledge_gap_detail": "conservation du produit bio"},
    )

    await _start_trainer_conversation(client, commercial)
    opening_prompt = str(fake_llm.calls[0]["system_prompt"])
    assert "LACUNES DÉTECTÉES" in opening_prompt
    assert "conservation du produit bio" in opening_prompt


async def test_trainer_reply_includes_tenant_scoped_rag_context(
    client: httpx.AsyncClient,
    direction: User,
    commercial: User,
    other_tenant_direction: User,
    fake_llm: FakeLLMProvider,
) -> None:
    await client.post("/training/", json=BIO_DOC, headers=auth_headers(direction))
    await client.post("/training/", json=TENANT_B_DOC, headers=auth_headers(other_tenant_direction))

    conversation_id = await _start_trainer_conversation(client, commercial)
    response = await client.post(
        f"/conversations/{conversation_id}/messages",
        json={"content": "Fais-moi un quiz sur la gamme bio"},
        headers=auth_headers(commercial),
    )
    assert response.status_code == 201

    reply_prompt = str(fake_llm.calls[-1]["system_prompt"])
    assert "CONTEXTE DOCUMENTAIRE" in reply_prompt
    assert "certifiée AB" in reply_prompt
    # Tenant isolation: the other tenant's documents never leak into the prompt
    assert "tenant B" not in reply_prompt


async def test_trainer_coaches_without_context_when_embeddings_down(
    client: httpx.AsyncClient,
    direction: User,
    commercial: User,
    fake_llm: FakeLLMProvider,
    fake_embedder: FakeEmbeddingProvider,
) -> None:
    await client.post("/training/", json=BIO_DOC, headers=auth_headers(direction))
    conversation_id = await _start_trainer_conversation(client, commercial)

    fake_embedder.fail = True
    response = await client.post(
        f"/conversations/{conversation_id}/messages",
        json={"content": "Fais-moi un quiz sur la gamme bio"},
        headers=auth_headers(commercial),
    )
    assert response.status_code == 201
    # The document content is absent: the trainer coaches without retrieval
    assert "certifiée AB" not in str(fake_llm.calls[-1]["system_prompt"])


async def test_closing_trainer_conversation_skips_extraction(
    client: httpx.AsyncClient, commercial: User, fake_llm: FakeLLMProvider
) -> None:
    conversation_id = await _start_trainer_conversation(client, commercial)
    calls_before = len(fake_llm.calls)

    close = await client.post(
        f"/conversations/{conversation_id}/close", headers=auth_headers(commercial)
    )
    assert close.status_code == 200
    body = close.json()
    assert body["status"] == "completed"
    assert body["extracted_data"] == {}
    # No extraction call for a training session
    assert len(fake_llm.calls) == calls_before
