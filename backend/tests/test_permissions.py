"""Explicit tenant-isolation tests (a tenant A user must NEVER see tenant B
resources) plus conversation visibility per role and auth rate limiting.
"""

import httpx
from app.core.ratelimit import limiter
from app.models.user import User

from tests.conftest import FakeLLMProvider, auth_headers


async def _create_conversation(client: httpx.AsyncClient, user: User) -> str:
    response = await client.post(
        "/conversations/", json={"agent_type": "collector"}, headers=auth_headers(user)
    )
    assert response.status_code == 201
    conversation_id: str = response.json()["id"]
    return conversation_id


# --- Tenant isolation -------------------------------------------------------


async def test_cross_tenant_conversation_looks_like_404(
    client: httpx.AsyncClient,
    commercial: User,
    other_tenant_user: User,
    fake_llm: FakeLLMProvider,
) -> None:
    conversation_id = await _create_conversation(client, commercial)

    for attempt in (
        client.get(
            f"/conversations/{conversation_id}/messages", headers=auth_headers(other_tenant_user)
        ),
        client.post(
            f"/conversations/{conversation_id}/messages",
            json={"content": "intrusion"},
            headers=auth_headers(other_tenant_user),
        ),
        client.post(
            f"/conversations/{conversation_id}/close", headers=auth_headers(other_tenant_user)
        ),
    ):
        response = await attempt
        assert response.status_code == 404

    listing = await client.get("/conversations/", headers=auth_headers(other_tenant_user))
    assert listing.json() == []


async def test_cross_tenant_user_patch_looks_like_404(
    client: httpx.AsyncClient, direction: User, other_tenant_user: User
) -> None:
    response = await client.patch(
        f"/users/{other_tenant_user.id}",
        json={"is_active": False},
        headers=auth_headers(direction),
    )
    assert response.status_code == 404


async def test_cross_tenant_users_invisible_in_listing(
    client: httpx.AsyncClient, direction: User, other_tenant_user: User
) -> None:
    response = await client.get("/users/", headers=auth_headers(direction))
    emails = [u["email"] for u in response.json()]
    assert other_tenant_user.email not in emails


# --- Conversation visibility per role ---------------------------------------


async def test_manager_sees_team_conversations_only(
    client: httpx.AsyncClient,
    manager: User,
    team_commercial: User,
    commercial: User,
) -> None:
    team_conv = await _create_conversation(client, team_commercial)
    outside_conv = await _create_conversation(client, commercial)

    listing = await client.get("/conversations/", headers=auth_headers(manager))
    ids = {c["id"] for c in listing.json()}
    assert team_conv in ids
    assert outside_conv not in ids

    # Direct access follows the same scope: outside conversations look like 404
    readable = await client.get(
        f"/conversations/{team_conv}/messages", headers=auth_headers(manager)
    )
    assert readable.status_code == 200
    hidden = await client.get(
        f"/conversations/{outside_conv}/messages", headers=auth_headers(manager)
    )
    assert hidden.status_code == 404


async def test_direction_sees_all_tenant_conversations(
    client: httpx.AsyncClient, direction: User, commercial: User, team_commercial: User
) -> None:
    conv_a = await _create_conversation(client, commercial)
    conv_b = await _create_conversation(client, team_commercial)

    listing = await client.get("/conversations/", headers=auth_headers(direction))
    ids = {c["id"] for c in listing.json()}
    assert {conv_a, conv_b} <= ids


async def test_commercial_cannot_see_colleague_conversation(
    client: httpx.AsyncClient, commercial: User, team_commercial: User
) -> None:
    conversation_id = await _create_conversation(client, team_commercial)

    response = await client.get(
        f"/conversations/{conversation_id}/messages", headers=auth_headers(commercial)
    )
    assert response.status_code == 404


async def test_manager_can_read_but_not_write_team_conversation(
    client: httpx.AsyncClient,
    manager: User,
    team_commercial: User,
    fake_llm: FakeLLMProvider,
) -> None:
    conversation_id = await _create_conversation(client, team_commercial)

    write = await client.post(
        f"/conversations/{conversation_id}/messages",
        json={"content": "je m'incruste"},
        headers=auth_headers(manager),
    )
    assert write.status_code == 403

    close = await client.post(
        f"/conversations/{conversation_id}/close", headers=auth_headers(manager)
    )
    assert close.status_code == 403


# --- Rate limiting -----------------------------------------------------------


async def test_login_rate_limited(client: httpx.AsyncClient) -> None:
    limiter.enabled = True
    try:
        # Default limit is 10/minute: the 11th attempt must be throttled
        for _ in range(10):
            response = await client.post(
                "/auth/login", json={"email": "inconnu@test.fr", "password": "n-importe-quoi"}
            )
            assert response.status_code == 401

        throttled = await client.post(
            "/auth/login", json={"email": "inconnu@test.fr", "password": "n-importe-quoi"}
        )
        assert throttled.status_code == 429
    finally:
        limiter.enabled = False
        limiter.reset()
