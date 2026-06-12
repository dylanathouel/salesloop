import httpx
from app.models.tenant import Tenant
from app.models.user import User

from tests.conftest import TEST_PASSWORD, auth_headers


async def test_login_ok(client: httpx.AsyncClient, commercial: User) -> None:
    response = await client.post(
        "/auth/login",
        json={
            "email": commercial.email,
            "password": TEST_PASSWORD,
            "tenant_id": str(commercial.tenant_id),
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "commercial"

    me = await client.get("/users/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
    assert me.json()["email"] == commercial.email


async def test_login_wrong_password(client: httpx.AsyncClient, commercial: User) -> None:
    response = await client.post(
        "/auth/login",
        json={
            "email": commercial.email,
            "password": "mauvais-mot-de-passe",
            "tenant_id": str(commercial.tenant_id),
        },
    )
    assert response.status_code == 401


async def test_register_then_duplicate_email(client: httpx.AsyncClient, tenant: Tenant) -> None:
    payload = {
        "email": "nouveau@test.fr",
        "password": "secret123",
        "full_name": "Nouveau User",
        "tenant_id": str(tenant.id),
    }
    first = await client.post("/auth/register", json=payload)
    assert first.status_code == 201

    duplicate = await client.post("/auth/register", json=payload)
    assert duplicate.status_code == 409


async def test_me_requires_token(client: httpx.AsyncClient) -> None:
    response = await client.get("/users/me")
    assert response.status_code in (401, 403)


async def test_users_scoped_to_tenant(
    client: httpx.AsyncClient, commercial: User, other_tenant_user: User
) -> None:
    response = await client.get("/users/", headers=auth_headers(commercial))
    assert response.status_code == 200
    emails = [u["email"] for u in response.json()]
    assert commercial.email in emails
    assert other_tenant_user.email not in emails
