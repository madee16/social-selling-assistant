"""WhatsApp/Meta integration gating tests (no database required).

These tests verify the environment-based master switch: the webhook
verification endpoint, the webhook POST handling, and the outbound send
functions must only do real work when WHATSAPP_ENABLED is true.
"""

import asyncio
import uuid
from contextlib import asynccontextmanager

import httpx
import pytest

from app.config import settings
from app.database import get_db
from app.main import app
from app.services import webhook_service

_ORIGINAL = {
    "whatsapp_enabled": settings.whatsapp_enabled,
    "whatsapp_env": settings.whatsapp_env,
    "app_env": settings.app_env,
    "whatsapp_verify_token": settings.whatsapp_verify_token,
    "whatsapp_graph_api_base": settings.whatsapp_graph_api_base,
    "whatsapp_phone_number_id": settings.whatsapp_phone_number_id,
    "whatsapp_access_token": settings.whatsapp_access_token,
    "whatsapp_app_secret": settings.whatsapp_app_secret,
}


@pytest.fixture(scope="session", autouse=True)
def _restore_whatsapp_settings():
    yield
    for key, value in _ORIGINAL.items():
        setattr(settings, key, value)


def _set_whatsapp(**kwargs) -> None:
    for key, value in kwargs.items():
        setattr(settings, key, value)


@asynccontextmanager
async def _client():
    async def override_get_db():
        yield None

    app.dependency_overrides[get_db] = override_get_db
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


# ---- Webhook verification (Meta GET /whatsapp) ----


@pytest.mark.asyncio
async def test_verification_disabled_returns_403():
    _set_whatsapp(whatsapp_enabled=False, whatsapp_verify_token="tok-1")
    async with _client() as c:
        r = await c.get(
            "/api/webhooks/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "tok-1",
                "hub.challenge": "1234",
            },
        )
    assert r.status_code == 403
    assert "disabled" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_verification_enabled_missing_params_400():
    _set_whatsapp(whatsapp_enabled=True, whatsapp_verify_token="tok-1")
    async with _client() as c:
        r = await c.get("/api/webhooks/whatsapp")
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_verification_enabled_returns_challenge():
    _set_whatsapp(whatsapp_enabled=True, whatsapp_verify_token="dev-verify-token")
    async with _client() as c:
        r = await c.get(
            "/api/webhooks/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "dev-verify-token",
                "hub.challenge": "98765",
            },
        )
    assert r.status_code == 200
    assert r.json() == "98765"


@pytest.mark.asyncio
async def test_verification_enabled_wrong_token_403():
    _set_whatsapp(whatsapp_enabled=True, whatsapp_verify_token="dev-verify-token")
    async with _client() as c:
        r = await c.get(
            "/api/webhooks/whatsapp",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong-token",
                "hub.challenge": "98765",
            },
        )
    assert r.status_code == 403


# ---- Webhook POST handling ----


@pytest.mark.asyncio
async def test_post_disabled_returns_ignored_and_does_not_process(monkeypatch):
    calls = []

    async def fake_process(body, user_id):
        calls.append((body, user_id))

    monkeypatch.setattr(webhook_service, "process_whatsapp_payload_async", fake_process)
    _set_whatsapp(whatsapp_enabled=False)
    async with _client() as c:
        r = await c.post(
            "/api/webhooks/whatsapp",
            json={"entry": [{"changes": [{"value": {"messages": [{"from": "123"}]}}]}]},
        )
    assert r.status_code == 200
    assert r.json() == {"status": "ignored", "reason": "whatsapp_integration_disabled"}
    await asyncio.sleep(0)
    assert calls == []


@pytest.mark.asyncio
async def test_post_enabled_dispatches_processing(monkeypatch):
    processed = []
    user_id = uuid.uuid4()

    async def fake_get_settings(db, uid):
        return type("FakeWS", (), {"user_id": uid})

    async def fake_process(body, uid):
        processed.append(uid)

    monkeypatch.setattr(
        "app.routers.webhooks._get_widget_settings_by_user_id", fake_get_settings
    )
    monkeypatch.setattr(webhook_service, "process_whatsapp_payload_async", fake_process)
    _set_whatsapp(whatsapp_enabled=True)

    async with _client() as c:
        r = await c.post(
            f"/api/webhooks/whatsapp?user_id={user_id}",
            json={"entry": [{"changes": [{"value": {"messages": [{"from": "123"}]}}]}]},
        )
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    assert processed == [user_id]


# ---- Webhook POST signature verification ----


@pytest.mark.asyncio
async def test_post_enabled_with_secret_rejects_bad_signature(monkeypatch):
    _set_whatsapp(whatsapp_enabled=True, whatsapp_app_secret="app-secret")
    async with _client() as c:
        r = await c.post(
            "/api/webhooks/whatsapp?user_id=00000000-0000-0000-0000-000000000000",
            json={"entry": [{"changes": [{"value": {"messages": [{"from": "123"}]}}]}]},
        )
    assert r.status_code == 400
    assert r.json()["detail"] == "Invalid signature"


@pytest.mark.asyncio
async def test_post_enabled_with_secret_rejects_missing_signature(monkeypatch):
    _set_whatsapp(whatsapp_enabled=True, whatsapp_app_secret="app-secret")
    async with _client() as c:
        r = await c.post(
            "/api/webhooks/whatsapp?user_id=00000000-0000-0000-0000-000000000000",
            content=b'{"entry": []}',
        )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_post_enabled_with_secret_accepts_valid_signature(monkeypatch):
    import hashlib
    import hmac

    processed = []
    user_id = uuid.uuid4()

    async def fake_get_settings(db, uid):
        return type("FakeWS", (), {"user_id": uid})

    async def fake_process(body, uid):
        processed.append(uid)

    monkeypatch.setattr(
        "app.routers.webhooks._get_widget_settings_by_user_id", fake_get_settings
    )
    monkeypatch.setattr(webhook_service, "process_whatsapp_payload_async", fake_process)

    payload = '{"entry": [{"changes": [{"value": {"messages": [{"from": "123"}]}}]}]}'
    sig = hmac.new(b"app-secret", payload.encode(), hashlib.sha256).hexdigest()
    _set_whatsapp(whatsapp_enabled=True, whatsapp_app_secret="app-secret")

    async with _client() as c:
        r = await c.post(
            f"/api/webhooks/whatsapp?user_id={user_id}",
            content=payload,
            headers={"X-Hub-Signature-256": f"sha256={sig}"},
        )
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
    await asyncio.sleep(0)
    await asyncio.sleep(0)
    assert processed == [user_id]


# ---- Outbound sending ----


@pytest.mark.asyncio
async def test_send_message_blocked_when_disabled(monkeypatch):
    monkeypatch.setattr(
        webhook_service.httpx.AsyncClient,
        "post",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not call HTTP")),
    )
    _set_whatsapp(whatsapp_enabled=False)
    ok = await webhook_service.send_whatsapp_message(
        to="212600000000",
        text="hello",
        phone_number_id="000",
        access_token="tok",
    )
    assert ok is False


@pytest.mark.asyncio
async def test_send_image_blocked_when_disabled(monkeypatch):
    monkeypatch.setattr(
        webhook_service.httpx.AsyncClient,
        "post",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not call HTTP")),
    )
    _set_whatsapp(whatsapp_enabled=False)
    ok = await webhook_service.send_whatsapp_image(
        to="212600000000",
        image_url="https://example.com/p.jpg",
        phone_number_id="000",
        access_token="tok",
    )
    assert ok is False


@pytest.mark.asyncio
async def test_send_message_enabled_uses_environment_credentials(monkeypatch):
    env_pnid = "ENV_PHONE_NUMBER_ID"
    env_token = "ENV_ACCESS_TOKEN"
    _set_whatsapp(
        whatsapp_enabled=True,
        whatsapp_phone_number_id=env_pnid,
        whatsapp_access_token=env_token,
        whatsapp_graph_api_base="https://graph.facebook.com/v21.0",
    )

    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

    calls = []

    async def fake_post(self, url, json=None, headers=None, **kwargs):
        calls.append((url, json, headers))
        return FakeResponse()

    monkeypatch.setattr(webhook_service.httpx.AsyncClient, "post", fake_post)

    ok = await webhook_service.send_whatsapp_message(
        to="212600000000", text="hello", phone_number_id=None, access_token=None
    )
    assert ok is True
    assert len(calls) == 1
    url, payload, headers = calls[0]
    assert url == "https://graph.facebook.com/v21.0/ENV_PHONE_NUMBER_ID/messages"
    assert headers["Authorization"] == "Bearer ENV_ACCESS_TOKEN"
    assert payload["messaging_product"] == "whatsapp"
    assert payload["to"] == "212600000000"
    assert payload["text"] == {"body": "hello"}


@pytest.mark.asyncio
async def test_send_message_enabled_but_no_credentials_returns_false(monkeypatch):
    monkeypatch.setattr(
        webhook_service.httpx.AsyncClient,
        "post",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not call HTTP")),
    )
    _set_whatsapp(
        whatsapp_enabled=True,
        whatsapp_phone_number_id=None,
        whatsapp_access_token=None,
    )
    ok = await webhook_service.send_whatsapp_message(
        to="212600000000", text="hello", phone_number_id=None, access_token=None
    )
    assert ok is False


@pytest.mark.asyncio
async def test_process_whatsapp_payload_async_skips_when_disabled():
    _set_whatsapp(whatsapp_enabled=False)
    await webhook_service.process_whatsapp_payload_async({"entry": []}, uuid.uuid4())
