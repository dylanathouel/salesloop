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


async def test_full_collector_flow(
    client: httpx.AsyncClient, commercial: User, fake_llm: FakeLLMProvider
) -> None:
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

    # History is persisted
    listing = await client.get(
        f"/conversations/{conversation_id}/messages", headers=auth_headers(commercial)
    )
    assert listing.status_code == 200
    assert len(listing.json()) == 2

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
    # Real token usage accumulated: (20+8) message + (30+15) extraction
    assert body["total_tokens"] == 73


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
    # One initial attempt + one corrective retry
    assert len(fake_llm.calls) == 2


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
