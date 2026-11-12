import os
from collections.abc import AsyncGenerator

import httpx
import pytest
from pytest_asyncio import fixture as async_fixture
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.database import Base, get_db
from app.main import app


def _resolve_db_host() -> str:
    """Resolve the Postgres host for tests; defaults to the Docker container on localhost."""
    return os.environ.get("TEST_DB_HOST", "localhost")


TEST_DATABASE_URL = f"postgresql+asyncpg://postgres:postgrespwd@{_resolve_db_host()}:5432/social_test"

engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
TestingSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def _disable_rate_limits():
    from app.limiter import limiter

    limiter.enabled = False
    yield
    limiter.enabled = True


@async_fixture(scope="function")
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@async_fixture(scope="function")
async def db_session(setup_database) -> AsyncGenerator[AsyncSession]:
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@async_fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
        yield c
    app.dependency_overrides.pop(get_db)


@async_fixture(scope="function")
async def auth_token(client) -> AsyncGenerator[str]:
    r = await client.post("/api/auth/login", json={"email": "demo@test.com", "password": "pass123"})
    token = r.json()["access_token"]
    yield token


@pytest.mark.asyncio
async def test_health_check(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_categories(client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    r = await client.get("/api/categories", headers=headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_products(client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    r = await client.get("/api/products", headers=headers)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_merchants(client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    r = await client.post("/api/merchants", json={"company_name": "Test Merchant"}, headers=headers)
    assert r.status_code in (200, 201)


@pytest.mark.asyncio
async def test_stores(client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    r = await client.post("/api/stores", json={"slug": "test-store", "name": "Test Store"}, headers=headers)
    assert r.status_code in (200, 201)


@pytest.mark.asyncio
async def test_buyers(client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    r = await client.post("/api/buyers", json={"email": "buyer@test.com", "name": "Test Buyer"}, headers=headers)
    assert r.status_code in (200, 201)


@pytest.mark.asyncio
async def test_orchestrator(client, db_session, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    r = await client.post("/api/ai/sessions", headers=headers)
    assert r.status_code in (200, 201)


@pytest.mark.asyncio
async def test_approvals(client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    r = await client.post("/api/approvals", json={"approval_type": "product", "entity_type": "product", "entity_id": "test-123"}, headers=headers)
    assert r.status_code in (200, 201)


@pytest.mark.asyncio
async def test_automation_rules(client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    r = await client.post("/api/automation-rules", json={"name": "Test Rule", "event_type": "order_created"}, headers=headers)
    assert r.status_code in (200, 201)


@pytest.mark.asyncio
async def test_inventory(client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    r = await client.get("/api/inventory", headers=headers)
    assert r.status_code in (200, 201)


@pytest.mark.asyncio
async def test_product_scores(client, auth_token):
    headers = {"Authorization": f"Bearer {auth_token}"}
    r = await client.get("/api/product-scores", headers=headers)
    assert r.status_code in (200, 201)
