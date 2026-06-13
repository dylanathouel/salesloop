"""User creation (/auth/users), patching, role-scoped listing, password change."""

import httpx
from app.models.user import User

from tests.conftest import TEST_PASSWORD, auth_headers


def _payload(email: str, role: str = "commercial", **extra: object) -> dict[str, object]:
    return {
        "email": email,
        "password": "motdepasse8",
        "full_name": "Nouveau Compte",
        "role": role,
        **extra,
    }


async def test_direction_creates_manager(client: httpx.AsyncClient, direction: User) -> None:
    response = await client.post(
        "/auth/users",
        json=_payload("nouveau-manager@test.fr", role="manager"),
        headers=auth_headers(direction),
    )
    assert response.status_code == 201
    assert response.json()["role"] == "manager"


async def test_manager_creates_commercial_attached_to_them(
    client: httpx.AsyncClient, manager: User
) -> None:
    response = await client.post(
        "/auth/users",
        json=_payload("nouveau-commercial@test.fr"),
        headers=auth_headers(manager),
    )
    assert response.status_code == 201
    assert response.json()["manager_id"] == str(manager.id)


async def test_manager_cannot_create_direction(client: httpx.AsyncClient, manager: User) -> None:
    response = await client.post(
        "/auth/users",
        json=_payload("usurpateur@test.fr", role="direction"),
        headers=auth_headers(manager),
    )
    assert response.status_code == 403


async def test_commercial_cannot_create_users(client: httpx.AsyncClient, commercial: User) -> None:
    response = await client.post(
        "/auth/users",
        json=_payload("copain@test.fr"),
        headers=auth_headers(commercial),
    )
    assert response.status_code == 403


async def test_direction_attaches_commercial_to_manager(
    client: httpx.AsyncClient, direction: User, manager: User, commercial: User
) -> None:
    response = await client.patch(
        f"/users/{commercial.id}",
        json={"manager_id": str(manager.id)},
        headers=auth_headers(direction),
    )
    assert response.status_code == 200
    assert response.json()["manager_id"] == str(manager.id)


async def test_attachment_must_target_a_manager(
    client: httpx.AsyncClient, direction: User, commercial: User, team_commercial: User
) -> None:
    response = await client.patch(
        f"/users/{commercial.id}",
        json={"manager_id": str(team_commercial.id)},
        headers=auth_headers(direction),
    )
    assert response.status_code == 403


async def test_manager_deactivates_own_team_member_only(
    client: httpx.AsyncClient, manager: User, team_commercial: User, commercial: User
) -> None:
    own = await client.patch(
        f"/users/{team_commercial.id}", json={"is_active": False}, headers=auth_headers(manager)
    )
    assert own.status_code == 200
    assert own.json()["is_active"] is False

    outside_team = await client.patch(
        f"/users/{commercial.id}", json={"is_active": False}, headers=auth_headers(manager)
    )
    assert outside_team.status_code == 403


async def test_manager_cannot_change_attachment(
    client: httpx.AsyncClient, manager: User, team_commercial: User
) -> None:
    response = await client.patch(
        f"/users/{team_commercial.id}",
        json={"manager_id": None},
        headers=auth_headers(manager),
    )
    assert response.status_code == 403


async def test_listing_scoped_by_role(
    client: httpx.AsyncClient,
    direction: User,
    manager: User,
    team_commercial: User,
    commercial: User,
) -> None:
    # Commercial: only themselves
    as_commercial = await client.get("/users/", headers=auth_headers(commercial))
    assert [u["id"] for u in as_commercial.json()] == [str(commercial.id)]

    # Manager: their team plus themselves
    as_manager = await client.get("/users/", headers=auth_headers(manager))
    ids = {u["id"] for u in as_manager.json()}
    assert ids == {str(manager.id), str(team_commercial.id)}

    # Direction: the whole tenant
    as_direction = await client.get("/users/", headers=auth_headers(direction))
    ids = {u["id"] for u in as_direction.json()}
    assert ids == {str(direction.id), str(manager.id), str(team_commercial.id), str(commercial.id)}


async def test_change_password_then_login_with_new(
    client: httpx.AsyncClient, commercial: User
) -> None:
    response = await client.post(
        "/users/me/password",
        json={"old_password": TEST_PASSWORD, "new_password": "nouveaumotdepasse"},
        headers=auth_headers(commercial),
    )
    assert response.status_code == 204

    # Old password no longer works, new one does
    old = await client.post(
        "/auth/login", json={"email": commercial.email, "password": TEST_PASSWORD}
    )
    assert old.status_code == 401
    new = await client.post(
        "/auth/login", json={"email": commercial.email, "password": "nouveaumotdepasse"}
    )
    assert new.status_code == 200


async def test_change_password_wrong_old_rejected(
    client: httpx.AsyncClient, commercial: User
) -> None:
    response = await client.post(
        "/users/me/password",
        json={"old_password": "pas-le-bon", "new_password": "nouveaumotdepasse"},
        headers=auth_headers(commercial),
    )
    assert response.status_code == 401


async def test_change_password_requires_auth(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/users/me/password",
        json={"old_password": "x", "new_password": "nouveaumotdepasse"},
    )
    assert response.status_code in (401, 403)
