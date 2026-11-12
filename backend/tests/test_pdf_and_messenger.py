"""Tests for PDF Invoice / Bon de Livraison Generator, Messenger AI Parity, and n8n Circuit Breaker."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.config import settings
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.store import Store
from app.models.widget_settings import WidgetSettings
from app.services import n8n_service, order_service, webhook_service


async def _register_and_get_auth(client, tag: str):
    reg = await client.post(
        "/api/auth/register",
        json={
            "email": f"merchant-{tag}@test.dev",
            "password": "Password123!",
            "company_name": f"Boutique {tag}",
        },
    )
    assert reg.status_code in (200, 201), reg.text
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    me_res = await client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200, me_res.text
    user_id = uuid.UUID(me_res.json()["id"])
    return headers, user_id


@pytest.mark.asyncio
class TestPdfInvoiceGenerator:
    async def test_pdf_invoice_download_success(self, client, db_session):
        tag = uuid.uuid4().hex[:6]
        headers, user_id = await _register_and_get_auth(client, tag)

        product = Product(
            user_id=user_id,
            name="Caftan Tunisien en Soie",
            price=220.00,
            stock_quantity=10,
            is_active=True,
        )
        db_session.add(product)
        await db_session.flush()

        order = Order(
            user_id=user_id,
            customer_name="Amina Mansour",
            customer_phone="+216 98 765 432",
            customer_address="Avenue Habib Bourguiba, Tunis",
            status="confirmed",
            total_amount=220.00,
        )
        db_session.add(order)
        await db_session.flush()

        order_item = OrderItem(
            order_id=order.id,
            product_id=product.id,
            quantity=1,
            unit_price=220.00,
            subtotal=220.00,
        )
        db_session.add(order_item)
        await db_session.commit()

        # Request PDF download
        res = await client.get(f"/api/orders/{order.id}/invoice.pdf", headers=headers)
        assert res.status_code == 200, res.text
        assert res.headers["content-type"] == "application/pdf"
        assert f"bon-de-livraison-{order.id}.pdf" in res.headers.get("content-disposition", "")
        # Valid PDF header
        assert res.content.startswith(b"%PDF-")
        assert len(res.content) > 1000

    async def test_pdf_invoice_cross_tenant_access_forbidden(self, client, db_session):
        # Merchant A
        tag_a = uuid.uuid4().hex[:6]
        headers_a, user_id_a = await _register_and_get_auth(client, tag_a)

        order_a = Order(
            user_id=user_id_a,
            customer_name="Client A",
            customer_phone="+216 20 111 222",
            customer_address="Sousse",
            status="pending",
            total_amount=95.00,
        )
        db_session.add(order_a)
        await db_session.commit()

        # Merchant B
        tag_b = uuid.uuid4().hex[:6]
        headers_b, _ = await _register_and_get_auth(client, tag_b)

        # Merchant B attempts to download Merchant A's order PDF
        res = await client.get(f"/api/orders/{order_a.id}/invoice.pdf", headers=headers_b)
        assert res.status_code in (403, 404)

        # Unauthenticated request
        unauth_res = await client.get(f"/api/orders/{order_a.id}/invoice.pdf")
        assert unauth_res.status_code in (401, 403)

    async def test_generate_pdf_service_function_direct(self):
        order = Order(
            id=uuid.uuid4(),
            customer_name="Karim Jaziri",
            customer_phone="+216 55 444 333",
            customer_address="Route de Téniour, Sfax",
            status="delivered",
            total_amount=150.00,
        )
        pdf_bytes = order_service.generate_order_invoice_pdf(order)
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes.startswith(b"%PDF-")


@pytest.mark.asyncio
class TestMessengerWebhookAndAIParity:
    async def test_verify_messenger_webhook(self, client):
        token = settings.messenger_verify_token
        # Valid subscribe
        res = await client.get(
            "/api/webhooks/messenger",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": token,
                "hub.challenge": "123456789",
            },
        )
        assert res.status_code == 200
        assert res.text in ("123456789", "123456789\n")

        # Invalid token
        res_fail = await client.get(
            "/api/webhooks/messenger",
            params={
                "hub.mode": "subscribe",
                "hub.verify_token": "wrong-token-invalid",
                "hub.challenge": "123456789",
            },
        )
        assert res_fail.status_code == 403

    async def test_process_messenger_payload_ai_parity(self, client, db_session):
        tag = uuid.uuid4().hex[:6]
        _, user_id = await _register_and_get_auth(client, tag)

        ws = WidgetSettings(
            user_id=user_id,
            enabled=True,
            messenger_page_id=f"page-{tag}",
            messenger_access_token=None,  # test mock fallback
        )
        db_session.add(ws)
        await db_session.commit()

        mid_test = f"mid.test.{uuid.uuid4().hex[:8]}"
        sender_id = f"sender-{tag}"
        payload = {
            "object": "page",
            "entry": [
                {
                    "id": f"page-{tag}",
                    "messaging": [
                        {
                            "sender": {"id": sender_id},
                            "recipient": {"id": f"page-{tag}"},
                            "message": {
                                "mid": mid_test,
                                "text": "Bonjour, quel est le prix du caftan et la livraison ?",
                            },
                        }
                    ],
                }
            ],
        }

        # Process through webhook service
        await webhook_service.process_messenger_payload(db_session, payload, ws)

        # Verify conversation was created
        conv_res = await db_session.execute(
            select(Conversation).where(
                Conversation.user_id == user_id,
                Conversation.platform == "messenger",
                Conversation.platform_conversation_id == sender_id,
            )
        )
        conv = conv_res.scalar_one_or_none()
        assert conv is not None

        # Verify user and assistant messages exist
        msg_res = await db_session.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.asc())
        )
        messages = msg_res.scalars().all()
        assert len(messages) >= 2
        user_msg = messages[0]
        asst_msg = messages[1]
        assert user_msg.role == "user"
        assert user_msg.extra_data.get("mid") == mid_test
        assert asst_msg.role == "assistant"
        assert asst_msg.content

        # Test deduplication: resending the same mid does not add duplicate messages
        prev_count = len(messages)
        await webhook_service.process_messenger_payload(db_session, payload, ws)
        msg_res_after = await db_session.execute(
            select(Message).where(Message.conversation_id == conv.id)
        )
        assert len(msg_res_after.scalars().all()) == prev_count

    async def test_process_messenger_with_images_and_mock_fallback(self, client, db_session):
        tag = uuid.uuid4().hex[:6]
        _, user_id = await _register_and_get_auth(client, tag)

        ws = WidgetSettings(
            user_id=user_id,
            enabled=True,
            messenger_page_id=f"page-{tag}",
            messenger_access_token=None,
        )
        db_session.add(ws)
        await db_session.commit()

        mock_ai_resp = {
            "reply": "Voici notre produit vedette en soie.",
            "language": "fr",
            "suggested_products": [
                {"id": 1, "name": "Caftan Soie", "image_url": "https://example.com/caftan.jpg"}
            ],
        }

        with patch("app.services.ai_service.get_ai_response", return_value=mock_ai_resp), \
             patch("app.services.webhook_service.send_messenger_image", new_callable=AsyncMock) as mock_send_img:

            payload = {
                "object": "page",
                "entry": [
                    {
                        "id": f"page-{tag}",
                        "messaging": [
                            {
                                "sender": {"id": f"buyer-{tag}"},
                                "recipient": {"id": f"page-{tag}"},
                                "message": {
                                    "mid": f"mid.img.{tag}",
                                    "text": "Avez-vous des photos ?",
                                },
                            }
                        ],
                    }
                ],
            }

            await webhook_service.process_messenger_payload(db_session, payload, ws)
            mock_send_img.assert_awaited_once_with(
                recipient_id=f"buyer-{tag}",
                image_url="https://example.com/caftan.jpg",
                access_token=None,
            )

    async def test_send_messenger_mock_fallback(self):
        # When access_token is None, both functions return False with mock logging and do not raise
        res_msg = await webhook_service.send_messenger_message("user123", "Hello", None)
        assert res_msg is False
        res_img = await webhook_service.send_messenger_image("user123", "https://img.jpg", None)
        assert res_img is False


@pytest.mark.asyncio
class TestN8nFastCircuitBreaker:
    async def test_n8n_circuit_breaker_trips_on_failures(self):
        n8n_service.reset_circuit_breaker()
        assert not n8n_service.is_circuit_open()

        # Simulate failures
        n8n_service.record_n8n_failure()
        assert not n8n_service.is_circuit_open()

        # Second failure trips threshold (FAILURE_THRESHOLD = 2)
        n8n_service.record_n8n_failure()
        assert n8n_service.is_circuit_open()

        state = n8n_service.get_circuit_state()
        assert state["is_open"] is True
        assert state["consecutive_failures"] >= 2

        # While open, generate_with_n8n returns None immediately without calling network
        with patch.object(settings, "n8n_webhook_url", "http://unreachable-test-host:5678"):
            res = await n8n_service.generate_with_n8n(
                user_message="test",
                conversation_history="",
                product_context="",
            )
            assert res is None

        # Reset works cleanly
        n8n_service.reset_circuit_breaker()
        assert not n8n_service.is_circuit_open()

    async def test_n8n_recovers_on_success(self):
        n8n_service.reset_circuit_breaker()
        n8n_service.record_n8n_failure()
        assert n8n_service.get_circuit_state()["consecutive_failures"] == 1

        n8n_service.record_n8n_success()
        assert n8n_service.get_circuit_state()["consecutive_failures"] == 0
        assert not n8n_service.is_circuit_open()
