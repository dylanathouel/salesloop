"""Test setup: dedicated Postgres database (schema applied via Alembic),
ASGI test client, tenant/user fixtures and a fake LLM provider.
"""

import os
import subprocess
import sys
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# --- Test environment, BEFORE any app import (settings read env at import) ---
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://salesloop:salesloop_dev_2026@localhost:5433/salesloop",
)
os.environ.setdefault("JWT_SECRET", "test-secret")
os.environ.setdefault("OPENROUTER_API_KEY", "test-key")
os.environ.setdefault("OPENROUTER_MODEL", "test-model")
# Rate limiting off by default; the dedicated test re-enables it explicitly
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")

_ADMIN_URL = os.environ["DATABASE_URL"]
_BASE, _DB_NAME = _ADMIN_URL.rsplit("/", 1)
TEST_DB_NAME = f"{_DB_NAME}_test"
TEST_DATABASE_URL = f"{_BASE}/{TEST_DB_NAME}"
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

BACKEND_DIR = Path(__file__).resolve().parent.parent

from app.core.security import create_access_token, hash_password  # noqa: E402
from app.database import async_session, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.enums import UserRole  # noqa: E402
from app.models.tenant import Tenant  # noqa: E402
from app.models.user import User  # noqa: E402
from app.services.llm.base import LLMMessage, LLMProvider, LLMResult  # noqa: E402
from app.services.llm.dependency import get_llm_provider  # noqa: E402

TEST_PASSWORD = "password123"
# Hash once: bcrypt is intentionally slow
TEST_PASSWORD_HASH = hash_password(TEST_PASSWORD)


@pytest.fixture(scope="session", autouse=True)
async def _database() -> AsyncGenerator[None, None]:
    """Recreate the test database and apply Alembic migrations on it."""
    admin_engine = create_async_engine(_ADMIN_URL, isolation_level="AUTOCOMMIT")
    async with admin_engine.connect() as conn:
        await conn.execute(text(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}" WITH (FORCE)'))
        await conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    await admin_engine.dispose()

    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        check=True,
        env={**os.environ, "DATABASE_URL": TEST_DATABASE_URL},
    )
    yield
    await engine.dispose()


@pytest.fixture(autouse=True)
async def _clean_tables(_database: None) -> AsyncGenerator[None, None]:
    yield
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "TRUNCATE TABLE report_conversation, message, conversation, report, "
                'directive, training_content, "user", tenant CASCADE'
            )
        )


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


@pytest.fixture
async def client() -> AsyncGenerator[httpx.AsyncClient, None]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


class FakeLLMProvider(LLMProvider):
    """Deterministic provider: returns queued results, then a default reply."""

    def __init__(self) -> None:
        self.queue: list[LLMResult] = []
        self.calls: list[dict[str, object]] = []

    def enqueue(self, content: str, prompt_tokens: int = 10, completion_tokens: int = 5) -> None:
        self.queue.append(
            LLMResult(
                content=content,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
            )
        )

    async def chat(
        self,
        system_prompt: str,
        messages: list[LLMMessage],
        max_tokens: int = 300,
    ) -> LLMResult:
        self.calls.append({"system_prompt": system_prompt, "messages": messages})
        if self.queue:
            return self.queue.pop(0)
        return LLMResult(content="Réponse de l'agent", prompt_tokens=10, completion_tokens=5)


@pytest.fixture
def fake_llm() -> AsyncGenerator[FakeLLMProvider, None]:
    fake = FakeLLMProvider()
    app.dependency_overrides[get_llm_provider] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_llm_provider, None)


async def _create_tenant(db: AsyncSession, name: str) -> Tenant:
    tenant = Tenant(name=name)
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant


async def _create_user(
    db: AsyncSession,
    tenant: Tenant,
    email: str,
    role: UserRole = UserRole.COMMERCIAL,
    manager_id: uuid.UUID | None = None,
) -> User:
    user = User(
        tenant_id=tenant.id,
        email=email,
        full_name="Test User",
        password_hash=TEST_PASSWORD_HASH,
        role=role,
        manager_id=manager_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def _unique_email(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}@test.fr"


@pytest.fixture
async def tenant(db: AsyncSession) -> Tenant:
    return await _create_tenant(db, "Tenant A")


@pytest.fixture
async def commercial(db: AsyncSession, tenant: Tenant) -> User:
    return await _create_user(db, tenant, _unique_email("commercial"))


@pytest.fixture
async def direction(db: AsyncSession, tenant: Tenant) -> User:
    return await _create_user(db, tenant, _unique_email("direction"), role=UserRole.DIRECTION)


@pytest.fixture
async def manager(db: AsyncSession, tenant: Tenant) -> User:
    return await _create_user(db, tenant, _unique_email("manager"), role=UserRole.MANAGER)


@pytest.fixture
async def team_commercial(db: AsyncSession, tenant: Tenant, manager: User) -> User:
    """A commercial attached to the `manager` fixture's team."""
    return await _create_user(db, tenant, _unique_email("equipier"), manager_id=manager.id)


@pytest.fixture
async def other_tenant_user(db: AsyncSession) -> User:
    other_tenant = await _create_tenant(db, "Tenant B")
    return await _create_user(db, other_tenant, _unique_email("intrus"))


def auth_headers(user: User) -> dict[str, str]:
    token = create_access_token(
        {"sub": str(user.id), "role": user.role.value, "tenant_id": str(user.tenant_id)}
    )
    return {"Authorization": f"Bearer {token}"}
