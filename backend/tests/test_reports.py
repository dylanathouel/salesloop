"""Report generation: scope aggregation, metrics, LLM synthesis, isolation."""

import json
from datetime import UTC, date, datetime
from typing import Any

import httpx
import pytest
from app.models.conversation import Conversation
from app.models.enums import AgentType, ConversationStatus
from app.models.user import User
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import FakeLLMProvider, auth_headers

REPORT_JSON = {
    "summary": "Semaine correcte avec une pression concurrentielle sur les prix.",
    "insights": {
        "trends": ["volume stable"],
        "recurring_objections": ["prix"],
        "competitor_alerts": ["ConcurrentX agressif sur les prix"],
        "training_needs": ["conservation produit"],
    },
}


@pytest.fixture
def closed_conversation(db: AsyncSession) -> Any:
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


def _period() -> dict[str, str]:
    today = date.today().isoformat()
    return {"period_type": "weekly", "period_start": today, "period_end": today}


async def test_manager_report_covers_team_scope_only(
    client: httpx.AsyncClient,
    manager: User,
    team_commercial: User,
    commercial: User,
    direction: User,
    closed_conversation: Any,
    fake_llm: FakeLLMProvider,
) -> None:
    await closed_conversation(
        team_commercial,
        {"sentiment": "positif", "objections": ["prix"], "competitors": [{"name": "ConcurrentX"}]},
    )
    await closed_conversation(
        commercial,
        {"sentiment": "négatif", "objections": ["délais"], "product_knowledge_gap": True},
    )

    # Manager: only the team conversation is aggregated
    fake_llm.enqueue(json.dumps(REPORT_JSON))
    as_manager = await client.post(
        "/reports/generate", json=_period(), headers=auth_headers(manager)
    )
    assert as_manager.status_code == 201
    body = as_manager.json()
    assert body["metrics"]["conversation_count"] == 1
    assert body["metrics"]["sentiments"] == {"positif": 1}
    assert body["summary"] == REPORT_JSON["summary"]
    assert body["insights"]["competitor_alerts"] == ["ConcurrentX agressif sur les prix"]

    # Direction: the whole tenant (2 conversations, metrics aggregated)
    fake_llm.enqueue(json.dumps(REPORT_JSON))
    as_direction = await client.post(
        "/reports/generate", json=_period(), headers=auth_headers(direction)
    )
    metrics = as_direction.json()["metrics"]
    assert metrics["conversation_count"] == 2
    assert metrics["knowledge_gap_count"] == 1
    assert set(metrics["top_objections"]) == {"prix", "délais"}


async def test_report_requires_closed_conversations_in_period(
    client: httpx.AsyncClient, direction: User, fake_llm: FakeLLMProvider
) -> None:
    response = await client.post(
        "/reports/generate",
        json={"period_type": "daily", "period_start": "2020-01-01", "period_end": "2020-01-01"},
        headers=auth_headers(direction),
    )
    assert response.status_code == 400


async def test_report_generation_forbidden_to_commercial(
    client: httpx.AsyncClient, commercial: User
) -> None:
    response = await client.post(
        "/reports/generate", json=_period(), headers=auth_headers(commercial)
    )
    assert response.status_code == 403


async def test_reports_isolated_between_tenants(
    client: httpx.AsyncClient,
    direction: User,
    commercial: User,
    other_tenant_manager: User,
    closed_conversation: Any,
    fake_llm: FakeLLMProvider,
) -> None:
    await closed_conversation(commercial, {"sentiment": "positif"})
    fake_llm.enqueue(json.dumps(REPORT_JSON))
    created = await client.post(
        "/reports/generate", json=_period(), headers=auth_headers(direction)
    )
    report_id = created.json()["id"]

    listing = await client.get("/reports/", headers=auth_headers(other_tenant_manager))
    assert listing.json() == []

    detail = await client.get(f"/reports/{report_id}", headers=auth_headers(other_tenant_manager))
    assert detail.status_code == 404

    # The owner tenant sees it
    detail = await client.get(f"/reports/{report_id}", headers=auth_headers(direction))
    assert detail.status_code == 200


async def test_report_degrades_cleanly_on_llm_garbage(
    client: httpx.AsyncClient,
    direction: User,
    commercial: User,
    closed_conversation: Any,
    fake_llm: FakeLLMProvider,
) -> None:
    await closed_conversation(commercial, {"sentiment": "positif"})
    fake_llm.enqueue("pas du json")
    fake_llm.enqueue("toujours pas du json")

    response = await client.post(
        "/reports/generate", json=_period(), headers=auth_headers(direction)
    )
    assert response.status_code == 201
    body = response.json()
    assert body["summary"] == "toujours pas du json"
    assert body["insights"] == {"error": "parsing_failed"}
