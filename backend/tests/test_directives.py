"""Directive CRUD, role permissions, tenant isolation and prompt injection."""

import httpx
from app.models.user import User

from tests.conftest import FakeLLMProvider, auth_headers


async def _create_directive(
    client: httpx.AsyncClient, actor: User, content: str, priority: str = "high"
) -> dict[str, object]:
    response = await client.post(
        "/directives/",
        json={"content": content, "priority": priority},
        headers=auth_headers(actor),
    )
    assert response.status_code == 201
    body: dict[str, object] = response.json()
    return body


async def test_commercial_cannot_write_directives(
    client: httpx.AsyncClient, commercial: User
) -> None:
    response = await client.post(
        "/directives/",
        json={"content": "je me donne des ordres"},
        headers=auth_headers(commercial),
    )
    assert response.status_code == 403


async def test_crud_and_commercial_sees_active_only(
    client: httpx.AsyncClient, manager: User, commercial: User
) -> None:
    active = await _create_directive(client, manager, "Poussez la gamme bio")
    archived = await _create_directive(client, manager, "Ancienne consigne", priority="low")

    patch = await client.patch(
        f"/directives/{archived['id']}",
        json={"status": "archived"},
        headers=auth_headers(manager),
    )
    assert patch.status_code == 200
    assert patch.json()["status"] == "archived"

    # Manager sees everything, commercial only the active directives
    as_manager = await client.get("/directives/", headers=auth_headers(manager))
    assert len(as_manager.json()) == 2
    as_commercial = await client.get("/directives/", headers=auth_headers(commercial))
    assert [d["id"] for d in as_commercial.json()] == [active["id"]]

    delete = await client.delete(f"/directives/{archived['id']}", headers=auth_headers(manager))
    assert delete.status_code == 204
    as_manager = await client.get("/directives/", headers=auth_headers(manager))
    assert len(as_manager.json()) == 1


async def test_cross_tenant_directive_looks_like_404(
    client: httpx.AsyncClient, manager: User, other_tenant_manager: User
) -> None:
    directive = await _create_directive(client, other_tenant_manager, "Consigne du tenant B")

    patch = await client.patch(
        f"/directives/{directive['id']}",
        json={"status": "archived"},
        headers=auth_headers(manager),
    )
    assert patch.status_code == 404

    listing = await client.get("/directives/", headers=auth_headers(manager))
    assert listing.json() == []


async def test_active_directives_injected_into_collector_prompt(
    client: httpx.AsyncClient,
    manager: User,
    commercial: User,
    fake_llm: FakeLLMProvider,
) -> None:
    await _create_directive(client, manager, "Poussez la gamme bio cette semaine")
    archived = await _create_directive(client, manager, "Consigne périmée")
    await client.patch(
        f"/directives/{archived['id']}",
        json={"status": "archived"},
        headers=auth_headers(manager),
    )

    # Opening prompt carries the active directive, not the archived one
    create = await client.post(
        "/conversations/", json={"agent_type": "collector"}, headers=auth_headers(commercial)
    )
    assert create.status_code == 201
    opening_prompt = str(fake_llm.calls[0]["system_prompt"])
    assert "DIRECTIVES DU MANAGEMENT" in opening_prompt
    assert "Poussez la gamme bio cette semaine" in opening_prompt
    assert "PRIORITÉ HAUTE" in opening_prompt
    assert "Consigne périmée" not in opening_prompt

    # Replies are generated with the directives too
    reply = await client.post(
        f"/conversations/{create.json()['id']}/messages",
        json={"content": "Journée correcte"},
        headers=auth_headers(commercial),
    )
    assert reply.status_code == 201
    assert "Poussez la gamme bio cette semaine" in str(fake_llm.calls[1]["system_prompt"])
