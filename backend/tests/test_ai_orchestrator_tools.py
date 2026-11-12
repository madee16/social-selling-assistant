"""Unit and integration tests for Native AI Orchestrator Tool-Calling and RulesEngine Action Dispatching."""

import json
import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import select

from app.models.ai_message import AIMessage
from app.models.ai_session import AISession
from app.models.ai_tool_call import AIToolCall
from app.models.approval import Approval
from app.models.audit_log import AuditLog
from app.models.automation_rule import AutomationRule
from app.models.inventory import Inventory
from app.models.marketplace_listing import MarketplaceListing
from app.models.merchant import Merchant
from app.models.notification import Notification
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.store import Store
from app.models.user import User
from app.services import ai_service
from app.services.orchestrator import Orchestrator
from app.services.rules_engine import RulesEngine


# ---------------------------------------------------------------------------
# Test Orchestrator Tools
# ---------------------------------------------------------------------------


class TestOrchestratorTools:
    @pytest.mark.asyncio
    async def test_execute_tool_check_inventory_success(self, db_session):
        user = User(email=f"orch-{uuid.uuid4().hex[:6]}@test.dev", password_hash="pwd", company_name="Test Co")
        db_session.add(user)
        await db_session.flush()

        product = Product(
            user_id=user.id,
            name="Test Tunisian Olive Oil 1L",
            price=25.50,
            stock_quantity=40,
        )
        db_session.add(product)
        await db_session.flush()

        orchestrator = Orchestrator(db_session)
        session_id = uuid.uuid4()

        result = await orchestrator.execute_tool_call(
            session_id=session_id,
            tool_name="check_inventory",
            arguments={"product_id": str(product.id)},
            merchant_id=user.id,
        )

        assert result["success"] is True
        assert result["available"] is True
        assert result["quantity"] == 40
        assert result["product_name"] == "Test Tunisian Olive Oil 1L"
        assert result["price"] == 25.50

        # Verify AIToolCall logged and completed
        stmt = select(AIToolCall).where(AIToolCall.tool_name == "check_inventory")
        res = await db_session.execute(stmt)
        tool_call = res.scalar_one_or_none()
        assert tool_call is not None
        assert tool_call.status == "completed"
        assert tool_call.result["quantity"] == 40

    @pytest.mark.asyncio
    async def test_execute_tool_check_inventory_with_variant(self, db_session):
        user = User(email=f"orch-var-{uuid.uuid4().hex[:6]}@test.dev", password_hash="pwd", company_name="Test Co")
        db_session.add(user)
        await db_session.flush()

        product = Product(
            user_id=user.id,
            name="Linen Shirt",
            price=75.00,
            stock_quantity=50,
        )
        db_session.add(product)
        await db_session.flush()

        variant = ProductVariant(
            product_id=product.id,
            name="Blue XL",
            sku="SHIRT-BLU-XL",
            quantity=8,
        )
        db_session.add(variant)
        await db_session.flush()

        orchestrator = Orchestrator(db_session)
        result = await orchestrator.execute_tool_call(
            session_id=uuid.uuid4(),
            tool_name="check_inventory",
            arguments={"product_id": str(product.id), "variant": "Blue XL"},
            merchant_id=user.id,
        )

        assert result["success"] is True
        assert result["available"] is True
        assert result["quantity"] == 8
        assert result["variant"] == "Blue XL"
        assert result["sku"] == "SHIRT-BLU-XL"

    @pytest.mark.asyncio
    async def test_execute_tool_check_inventory_missing_product(self, db_session):
        orchestrator = Orchestrator(db_session)
        result = await orchestrator.execute_tool_call(
            session_id=uuid.uuid4(),
            tool_name="check_inventory",
            arguments={"product_id": "non-existent-id"},
            merchant_id=uuid.uuid4(),
        )

        assert result["success"] is False
        assert result["available"] is False
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_execute_tool_create_order_success(self, db_session):
        user = User(email=f"orch-ord-{uuid.uuid4().hex[:6]}@test.dev", password_hash="pwd", company_name="Test Co")
        db_session.add(user)
        await db_session.flush()

        product = Product(
            user_id=user.id,
            name="Artisan Honey 500g",
            price=15.00,
            stock_quantity=20,
        )
        db_session.add(product)
        await db_session.flush()

        orchestrator = Orchestrator(db_session)
        session_id = uuid.uuid4()

        result = await orchestrator.execute_tool_call(
            session_id=session_id,
            tool_name="create_order",
            arguments={
                "buyer_phone": "+21698111222",
                "customer_name": "Ali Ben Salah",
                "delivery_address": "Avenue Habib Bourguiba, Tunis",
                "payment_method": "COD",
                "items": [{"product_id": str(product.id), "quantity": 2}],
            },
            merchant_id=user.id,
        )

        assert result["success"] is True
        assert result["status"] == "pending"
        assert result["total_amount"] == 30.00
        assert result["items_count"] == 1
        assert "order_id" in result

        # Verify stock decremented
        await db_session.refresh(product)
        assert product.stock_quantity == 18

        # Verify Order & OrderItem in DB
        order = await db_session.get(Order, uuid.UUID(result["order_id"]))
        assert order is not None
        assert order.customer_name == "Ali Ben Salah"
        assert order.customer_phone == "+21698111222"
        assert order.total_amount == 30.00

    @pytest.mark.asyncio
    async def test_execute_tool_create_order_insufficient_stock(self, db_session):
        user = User(email=f"orch-nostock-{uuid.uuid4().hex[:6]}@test.dev", password_hash="pwd", company_name="Test Co")
        db_session.add(user)
        await db_session.flush()

        product = Product(
            user_id=user.id,
            name="Limited Edition Watch",
            price=250.00,
            stock_quantity=1,
        )
        db_session.add(product)
        await db_session.flush()

        orchestrator = Orchestrator(db_session)
        result = await orchestrator.execute_tool_call(
            session_id=uuid.uuid4(),
            tool_name="create_order",
            arguments={
                "buyer_phone": "+21698333444",
                "delivery_address": "Sousse",
                "items": [{"product_id": str(product.id), "quantity": 5}],
            },
            merchant_id=user.id,
        )

        assert result["success"] is False
        assert "insufficient stock" in result["error"].lower()

        # Stock remains untouched
        await db_session.refresh(product)
        assert product.stock_quantity == 1

    @pytest.mark.asyncio
    async def test_execute_tool_request_merchant_approval(self, db_session):
        user = User(email=f"orch-appr-{uuid.uuid4().hex[:6]}@test.dev", password_hash="pwd", company_name="Test Co")
        db_session.add(user)
        await db_session.flush()

        product = Product(
            user_id=user.id,
            name="Bulk Coffee Beans 10kg",
            price=120.00,
            stock_quantity=10,
        )
        db_session.add(product)
        await db_session.flush()

        orchestrator = Orchestrator(db_session)
        session_id = uuid.uuid4()

        result = await orchestrator.execute_tool_call(
            session_id=session_id,
            tool_name="request_merchant_approval",
            arguments={
                "reason": "Client buying 3 sacks, requested 15% discount",
                "proposed_discount_percent": 15.0,
                "product_id": str(product.id),
                "buyer_phone": "+21698555666",
            },
            merchant_id=user.id,
        )

        assert result["success"] is True
        assert result["status"] == "pending"
        assert result["proposed_discount_percent"] == 15.0
        assert "approval_id" in result

        # Verify Approval record in DB
        approval = await db_session.get(Approval, uuid.UUID(result["approval_id"]))
        assert approval is not None
        assert approval.approval_type == "discount"
        assert approval.status == "pending"
        assert approval.meta_data["buyer_phone"] == "+21698555666"
        assert approval.meta_data["proposed_discount_percent"] == 15.0

    @pytest.mark.asyncio
    async def test_execute_tool_unknown_tool(self, db_session):
        orchestrator = Orchestrator(db_session)
        result = await orchestrator.execute_tool_call(
            session_id=uuid.uuid4(),
            tool_name="unknown_non_existent_tool",
            arguments={},
            merchant_id=uuid.uuid4(),
        )
        assert result["success"] is False
        assert "unknown tool" in result["error"].lower()


# ---------------------------------------------------------------------------
# Test RulesEngine Low-Stock Auto-Pause & Governance
# ---------------------------------------------------------------------------


class TestRulesEngineActions:
    @pytest.mark.asyncio
    async def test_low_stock_auto_pauses_marketplace_listings(self, db_session):
        user = User(email=f"rules-low-{uuid.uuid4().hex[:6]}@test.dev", password_hash="pwd", company_name="Test Co")
        db_session.add(user)
        await db_session.flush()

        merchant = Merchant(user_id=user.id, company_name="Test Co")
        db_session.add(merchant)
        await db_session.flush()

        store = Store(name="Main Store", slug=f"store-{uuid.uuid4().hex[:6]}", merchant_id=merchant.id)
        db_session.add(store)
        await db_session.flush()

        product = Product(user_id=user.id, name="Low Stock Ceramic Vase", price=45.0, stock_quantity=4)
        db_session.add(product)
        await db_session.flush()

        listing1 = MarketplaceListing(
            product_id=product.id,
            store_id=store.id,
            marketplace="facebook_shops",
            listing_status="active",
        )
        listing2 = MarketplaceListing(
            product_id=product.id,
            store_id=store.id,
            marketplace="instagram",
            listing_status="published",
        )
        db_session.add_all([listing1, listing2])
        await db_session.flush()

        rules_engine = RulesEngine(db_session)
        result = await rules_engine.trigger_low_stock_actions(
            product_id=product.id,
            store_id=store.id,
            merchant_user_id=user.id,
            quantity=4,
            threshold=5,
        )

        assert result["paused_listings"] == 2
        assert result["notification_created"] is True

        # Verify listings are paused
        await db_session.refresh(listing1)
        await db_session.refresh(listing2)
        assert listing1.listing_status == "paused"
        assert listing1.status == "paused"
        assert listing2.listing_status == "paused"
        assert listing2.status == "paused"

        # Verify low_stock notification created
        notif_stmt = select(Notification).where(
            Notification.user_id == user.id,
            Notification.type == "low_stock",
        )
        notif_res = await db_session.execute(notif_stmt)
        notif = notif_res.scalar_one_or_none()
        assert notif is not None
        assert "Low Stock Ceramic Vase" in notif.title

    @pytest.mark.asyncio
    async def test_execute_automation_dispatches_actions(self, db_session):
        user = User(email=f"auto-rule-{uuid.uuid4().hex[:6]}@test.dev", password_hash="pwd", company_name="Test Co")
        db_session.add(user)
        await db_session.flush()

        merchant = Merchant(user_id=user.id, company_name="Test Co")
        db_session.add(merchant)
        await db_session.flush()

        store = Store(name="Store Auto", slug=f"store-{uuid.uuid4().hex[:6]}", merchant_id=merchant.id)
        db_session.add(store)
        await db_session.flush()

        product = Product(user_id=user.id, name="Auto Paused Item", price=20.0, stock_quantity=2)
        db_session.add(product)
        await db_session.flush()

        listing = MarketplaceListing(
            product_id=product.id,
            store_id=store.id,
            marketplace="facebook",
            listing_status="active",
        )
        db_session.add(listing)
        await db_session.flush()

        rule = AutomationRule(
            merchant_id=merchant.id,
            name="Auto Pause on Low Stock",
            event_type="inventory.low_stock",
            actions={
                "pause_listings": True,
                "notify_merchant": True,
                "notification": {
                    "title": "Rule Alert: Stock Depleted",
                    "message": "Listings automatically paused by rule.",
                },
                "log_audit": True,
            },
        )
        db_session.add(rule)
        await db_session.flush()

        rules_engine = RulesEngine(db_session)
        exec_res = await rules_engine.execute_automation(
            rule=rule,
            event_payload={"product_id": str(product.id), "user_id": str(user.id)},
        )

        assert exec_res["executed"] is True
        assert rule.execution_count == 1
        assert len(exec_res["dispatched"]) >= 2

        await db_session.refresh(listing)
        assert listing.listing_status == "paused"

        # Verify notification created
        notif_stmt = select(Notification).where(
            Notification.user_id == user.id,
            Notification.title == "Rule Alert: Stock Depleted",
        )
        notif_res = await db_session.execute(notif_stmt)
        assert notif_res.scalar_one_or_none() is not None

        # Verify audit log created
        audit_stmt = select(AuditLog).where(
            AuditLog.action == "automation.inventory.low_stock"
        )
        audit_res = await db_session.execute(audit_stmt)
        assert audit_res.scalar_one_or_none() is not None


# ---------------------------------------------------------------------------
# Test Governance Approval Dispatch via Router
# ---------------------------------------------------------------------------


class TestGovernanceApprovalDispatch:
    @pytest.mark.asyncio
    async def test_approval_approved_dispatches_buyer_message_and_audit(self, client):
        tag = uuid.uuid4().hex[:6]
        reg = await client.post(
            "/api/auth/register",
            json={
                "email": f"gov-{tag}@test.dev",
                "password": "Password123!",
                "company_name": f"Gov Co {tag}",
            },
        )
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Create merchant and store
        merch_res = await client.post(
            "/api/merchants",
            json={"company_name": f"Gov Co {tag}"},
            headers=headers,
        )
        assert merch_res.status_code in (200, 201)

        store_res = await client.post(
            "/api/stores",
            json={"name": "Gov Store", "slug": f"store-{tag}"},
            headers=headers,
        )
        assert store_res.status_code in (200, 201)
        store_id = store_res.json()["id"]

        # 2. Create AI session
        sess_res = await client.post(
            "/api/ai/sessions",
            json={"store_id": store_id, "intent": "discount_negotiation"},
            headers=headers,
        )
        assert sess_res.status_code == 201
        session_id = sess_res.json()["id"]

        # 2. Create pending approval with session_id in meta_data
        appr_res = await client.post(
            "/api/approvals",
            json={
                "approval_type": "discount",
                "entity_type": "product",
                "entity_id": "test-prod-123",
                "title": "Discount 10% request",
                "meta_data": {
                    "session_id": session_id,
                    "buyer_phone": "+21699887766",
                    "proposed_discount_percent": 10.0,
                    "product_name": "Leather Handbag",
                },
            },
            headers=headers,
        )
        assert appr_res.status_code == 201
        approval_id = appr_res.json()["id"]

        # 3. Merchant approves the request
        update_res = await client.put(
            f"/api/approvals/{approval_id}",
            json={"status": "approved"},
            headers=headers,
        )
        assert update_res.status_code == 200
        assert update_res.json()["status"] == "approved"

        # 4. Verify automated AIMessage created in buyer session
        msgs_res = await client.get(
            f"/api/ai/sessions/{session_id}/messages",
            headers=headers,
        )
        assert msgs_res.status_code == 200
        items = msgs_res.json()["items"]
        assert len(items) >= 1
        last_msg = items[-1]
        assert last_msg["role"] == "assistant"
        assert "accepté" in last_msg["content"].lower() or "validé" in last_msg["content"].lower()
        assert "Leather Handbag" in last_msg["content"]

        # 5. Verify audit log entry
        audit_res = await client.get("/api/audit-logs", headers=headers)
        assert audit_res.status_code == 200
        logs = audit_res.json()["items"]
        assert any(l["action"] == "approval.approved" for l in logs)

    @pytest.mark.asyncio
    async def test_approval_rejected_dispatches_buyer_message_and_audit(self, client):
        tag = uuid.uuid4().hex[:6]
        reg = await client.post(
            "/api/auth/register",
            json={
                "email": f"gov-rej-{tag}@test.dev",
                "password": "Password123!",
                "company_name": f"Gov Rej Co {tag}",
            },
        )
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Create merchant and store
        merch_res = await client.post(
            "/api/merchants",
            json={"company_name": f"Gov Rej Co {tag}"},
            headers=headers,
        )
        assert merch_res.status_code in (200, 201)

        store_res = await client.post(
            "/api/stores",
            json={"name": "Gov Rej Store", "slug": f"store-{tag}"},
            headers=headers,
        )
        assert store_res.status_code in (200, 201)
        store_id = store_res.json()["id"]

        # 2. Create AI session
        sess_res = await client.post(
            "/api/ai/sessions",
            json={"store_id": store_id, "intent": "discount_negotiation"},
            headers=headers,
        )
        assert sess_res.status_code == 201
        session_id = sess_res.json()["id"]

        appr_res = await client.post(
            "/api/approvals",
            json={
                "approval_type": "discount",
                "entity_type": "product",
                "entity_id": "test-prod-456",
                "title": "Discount 25% request",
                "meta_data": {
                    "session_id": session_id,
                    "buyer_phone": "+21699112233",
                    "proposed_discount_percent": 25.0,
                    "product_name": "Handmade Carpet",
                },
            },
            headers=headers,
        )
        approval_id = appr_res.json()["id"]

        update_res = await client.put(
            f"/api/approvals/{approval_id}",
            json={"status": "rejected", "rejection_reason": "Marge insuffisante"},
            headers=headers,
        )
        assert update_res.status_code == 200
        assert update_res.json()["status"] == "rejected"

        msgs_res = await client.get(
            f"/api/ai/sessions/{session_id}/messages",
            headers=headers,
        )
        assert msgs_res.status_code == 200
        items = msgs_res.json()["items"]
        assert len(items) >= 1
        last_msg = items[-1]
        assert "Marge insuffisante" in last_msg["content"]

        audit_res = await client.get("/api/audit-logs", headers=headers)
        assert audit_res.status_code == 200
        logs = audit_res.json()["items"]
        assert any(l["action"] == "approval.rejected" for l in logs)


# ---------------------------------------------------------------------------
# Test AI Service Tool-Calling Loop and Backward Compatibility
# ---------------------------------------------------------------------------


class TestAIServiceToolCalling:
    @pytest.mark.asyncio
    async def test_ai_service_native_tool_calling_loop(self, db_session):
        user = User(email=f"ai-tool-{uuid.uuid4().hex[:6]}@test.dev", password_hash="pwd", company_name="Test Co")
        db_session.add(user)
        await db_session.flush()

        product = Product(
            user_id=user.id,
            name="Organic Almonds 500g",
            price=22.0,
            stock_quantity=15,
        )
        db_session.add(product)
        await db_session.flush()

        conv_id = uuid.uuid4()

        # Mock OpenAI chat completion responses
        mock_tool_call = MagicMock()
        mock_tool_call.id = "call_abc123"
        mock_tool_call.function.name = "check_inventory"
        mock_tool_call.function.arguments = json.dumps({"product_id": str(product.id)})

        mock_first_response = MagicMock()
        mock_first_response.choices = [
            MagicMock(
                message=MagicMock(
                    content=None,
                    tool_calls=[mock_tool_call],
                )
            )
        ]

        mock_second_response = MagicMock()
        mock_second_response.choices = [
            MagicMock(
                message=MagicMock(
                    content="Oui, les amandes bio 500g sont bien en stock (15 unités disponibles à 22.00 TND). Souhaitez-vous passer commande ?",
                    tool_calls=None,
                )
            )
        ]

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [
            mock_first_response,
            mock_second_response,
        ]

        with patch("app.config.settings.nvidia_api_key", "test-key-mock"), \
             patch("openai.OpenAI", return_value=mock_client):

            messages = [
                {"role": "user", "content": "Avez-vous des amandes bio en stock ?"}
            ]

            reply, order = await ai_service._call_llm_with_tools(
                db=db_session,
                user_id=user.id,
                conversation_id=conv_id,
                messages=messages,
            )

            assert "15 unités disponibles" in reply
            assert order is None

            # Verify the tool was called and recorded
            tc_stmt = select(AIToolCall).where(AIToolCall.tool_name == "check_inventory")
            tc_res = await db_session.execute(tc_stmt)
            tool_call_rec = tc_res.scalar_one_or_none()
            assert tool_call_rec is not None
            assert tool_call_rec.result["available"] is True
            assert tool_call_rec.result["quantity"] == 15

    def test_parse_order_block_fallback(self):
        text = 'Merci ! [ORDER]{"customer_name": "Nadia", "customer_phone": "22111333", "customer_address": "Tunis", "items": [{"product_name": "Huile", "quantity": 1}]}[/ORDER] Votre commande arrive bientôt !'
        clean, order_data = ai_service._parse_order_block(text)
        assert clean == "Merci !  Votre commande arrive bientôt !"
        assert order_data is not None
        assert order_data["customer_name"] == "Nadia"
        assert order_data["items"][0]["quantity"] == 1
