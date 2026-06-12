import httpx
from app.models.user import User

from tests.conftest import TEST_PASSWORD, auth_headers

SIGNUP_PAYLOAD = {
    "company_name": "Pharma-Corp",
    "email": "fondateur@pharma.fr",
    "password": "motdepasse8",
    "full_name": "Fondateur Pharma",
}


async def test_company_signup_creates_tenant_and_direction(client: httpx.AsyncClient) -> None:
    response = await client.post("/auth/register", json=SIGNUP_PAYLOAD)
    assert response.status_code == 201
    body = response.json()
    assert body["role"] == "direction"

    me = await client.get("/users/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == SIGNUP_PAYLOAD["email"]


async def test_signup_duplicate_email_rejected(client: httpx.AsyncClient) -> None:
    first = await client.post("/auth/register", json=SIGNUP_PAYLOAD)
    assert first.status_code == 201

    duplicate = await client.post(
        "/auth/register", json={**SIGNUP_PAYLOAD, "company_name": "Autre Corp"}
    )
    assert duplicate.status_code == 409


async def test_login_with_email_only(client: httpx.AsyncClient, commercial: User) -> None:
    response = await client.post(
        "/auth/login", json={"email": commercial.email, "password": TEST_PASSWORD}
    )
    assert response.status_code == 200
    assert response.json()["role"] == "commercial"


async def test_login_wrong_password(client: httpx.AsyncClient, commercial: User) -> None:
    response = await client.post(
        "/auth/login", json={"email": commercial.email, "password": "mauvais-mot-de-passe"}
    )
    assert response.status_code == 401


async def test_login_inactive_account(
    client: httpx.AsyncClient, commercial: User, direction: User
) -> None:
    patch = await client.patch(
        f"/users/{commercial.id}", json={"is_active": False}, headers=auth_headers(direction)
    )
    assert patch.status_code == 200

    response = await client.post(
        "/auth/login", json={"email": commercial.email, "password": TEST_PASSWORD}
    )
    assert response.status_code == 403


async def test_me_requires_token(client: httpx.AsyncClient) -> None:
    response = await client.get("/users/me")
    assert response.status_code in (401, 403)
