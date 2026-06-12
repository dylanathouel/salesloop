import json

import httpx
from app.models.user import User

from tests.conftest import FakeLLMProvider, auth_headers

EXTRACTION_JSON = {
    "sentiment": "positif",
    "client_name": "Pharma-Corp",
    "order_result": "commande",
    "objections": ["prix trop élevé"],
    "competitors": [{"name": "ConcurrentX", "price_mentioned": True, "price_detail": "-10%"}],
    "follow_up_needed": True,
}


async def _create_conversation(client: httpx.AsyncClient, user: User) -> str:
    response = await client.post(
        "/conversations/", json={"agent_type": "collector"}, headers=auth_headers(user)
    )
    assert response.status_code == 201
    conversation_id: str = response.json()["id"]
    return conversation_id


async def test_collector_opens_the_conversation(
    client: httpx.AsyncClient, commercial: User, fake_llm: FakeLLMProvider
) -> None:
    fake_llm.enqueue(
        "Salut ! Comment s'est passée ta journée ?", prompt_tokens=12, completion_tokens=7
    )
    response = await client.post(
        "/conversations/", json={"agent_type": "collector"}, headers=auth_headers(commercial)
    )
    assert response.status_code == 201
    body = response.json()
    assert body["first_message"]["sender"] == "agent"
    assert body["first_message"]["content"] == "Salut ! Comment s'est passée ta journée ?"
    assert body["total_tokens"] == 19

    # The opening is persisted as the first message of the history
    listing = await client.get(
        f"/conversations/{body['id']}/messages", headers=auth_headers(commercial)
    )
    assert [m["sender"] for m in listing.json()] == ["agent"]


async def test_trainer_conversation_opens_too(
    client: httpx.AsyncClient, commercial: User, fake_llm: FakeLLMProvider
) -> None:
    fake_llm.enqueue("Prêt pour un entraînement ?")
    response = await client.post(
        "/conversations/", json={"agent_type": "trainer"}, headers=auth_headers(commercial)
    )
    assert response.status_code == 201
    assert response.json()["first_message"]["content"] == "Prêt pour un entraînement ?"


async def test_full_collector_flow(
    client: httpx.AsyncClient, commercial: User, fake_llm: FakeLLMProvider
) -> None:
    # Creation consumes one LLM call for the opening (default fake reply: 10+5 tokens)
    conversation_id = await _create_conversation(client, commercial)

    # User message -> agent reply (both returned)
    fake_llm.enqueue("Salut ! Comment ça s'est passé ?", prompt_tokens=20, completion_tokens=8)
    response = await client.post(
        f"/conversations/{conversation_id}/messages",
        json={"content": "Je rentre de RDV chez Pharma-Corp"},
        headers=auth_headers(commercial),
    )
    assert response.status_code == 201
    messages = response.json()
    assert [m["sender"] for m in messages] == ["user", "agent"]
    assert messages[1]["content"] == "Salut ! Comment ça s'est passé ?"
    assert messages[1]["token_count"] == 8

    # History is persisted: opening + user + agent reply
    listing = await client.get(
        f"/conversations/{conversation_id}/messages", headers=auth_headers(commercial)
    )
    assert listing.status_code == 200
    assert len(listing.json()) == 3

    # Closing triggers the structured extraction
    fake_llm.enqueue(json.dumps(EXTRACTION_JSON), prompt_tokens=30, completion_tokens=15)
    close = await client.post(
        f"/conversations/{conversation_id}/close", headers=auth_headers(commercial)
    )
    assert close.status_code == 200
    body = close.json()
    assert body["status"] == "completed"
    assert body["ended_at"] is not None
    assert body["extracted_data"]["sentiment"] == "positif"
    assert body["extracted_data"]["competitors"][0]["name"] == "ConcurrentX"
    # Real token usage: (10+5) opening + (20+8) message + (30+15) extraction
    assert body["total_tokens"] == 88


async def test_extraction_invalid_json_retries_then_stores_error(
    client: httpx.AsyncClient, commercial: User, fake_llm: FakeLLMProvider
) -> None:
    conversation_id = await _create_conversation(client, commercial)

    fake_llm.enqueue("pas du json")
    fake_llm.enqueue("toujours pas du json")
    close = await client.post(
        f"/conversations/{conversation_id}/close", headers=auth_headers(commercial)
    )
    assert close.status_code == 200
    extracted = close.json()["extracted_data"]
    assert extracted["error"] == "extraction_failed"
    # Opening at creation + one extraction attempt + one corrective retry
    assert len(fake_llm.calls) == 3


async def test_close_twice_rejected(
    client: httpx.AsyncClient, commercial: User, fake_llm: FakeLLMProvider
) -> None:
    conversation_id = await _create_conversation(client, commercial)

    fake_llm.enqueue(json.dumps(EXTRACTION_JSON))
    first = await client.post(
        f"/conversations/{conversation_id}/close", headers=auth_headers(commercial)
    )
    assert first.status_code == 200

    second = await client.post(
        f"/conversations/{conversation_id}/close", headers=auth_headers(commercial)
    )
    assert second.status_code == 400


async def test_invalid_uuid_rejected(client: httpx.AsyncClient, commercial: User) -> None:
    response = await client.get(
        "/conversations/pas-un-uuid/messages", headers=auth_headers(commercial)
    )
    assert response.status_code == 422
