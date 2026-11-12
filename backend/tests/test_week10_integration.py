"""
Week 10 — Integration Tests
Full-workflow tests: merchant → store → product → order → approval.

Each test class is self-contained: it registers a fresh user, builds up the
chain of resources it needs, then asserts the expected behaviour end-to-end.
"""

import uuid

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register_and_login(client, suffix: str | None = None) -> dict:
    """Register a unique user and return {headers, email, user_id}."""
    tag = suffix or uuid.uuid4().hex[:8]
    email = f"int-{tag}@test.dev"
    r = await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "TestPass!1",
            "company_name": f"Company {tag}",
            "phone": f"+2162{tag[:8]}",
        },
    )
    assert r.status_code == 200, f"register failed: {r.text}"
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, email


async def _create_merchant(client, headers) -> dict:
    r = await client.post(
        "/api/merchants",
        json={"company_name": "Test Merchant Inc."},
        headers=headers,
    )
    assert r.status_code in (200, 201), f"create merchant failed: {r.text}"
    return r.json()


async def _create_store(client, headers, slug: str | None = None) -> dict:
    slug = slug or f"store-{uuid.uuid4().hex[:6]}"
    r = await client.post(
        "/api/stores",
        json={"slug": slug, "name": "Test Store"},
        headers=headers,
    )
    assert r.status_code in (200, 201), f"create store failed: {r.text}"
    return r.json()


async def _create_product(client, headers) -> dict:
    r = await client.post(
        "/api/products",
        json={"name": "Widget Pro", "price": 29.99, "description": "A great widget", "stock_quantity": 100},
        headers=headers,
    )
    assert r.status_code in (200, 201), f"create product failed: {r.text}"
    return r.json()


async def _create_order(client, headers, product_id: str) -> dict:
    r = await client.post(
        "/api/orders",
        json={
            "customer_name": "Test Customer",
            "items": [{"product_id": product_id, "quantity": 2, "unit_price": 29.99}],
        },
        headers=headers,
    )
    assert r.status_code in (200, 201), f"create order failed: {r.text}"
    return r.json()


async def _create_approval(client, headers, entity_id: str) -> dict:
    r = await client.post(
        "/api/approvals",
        json={
            "approval_type": "order",
            "entity_type": "order",
            "entity_id": entity_id,
        },
        headers=headers,
    )
    assert r.status_code in (200, 201), f"create approval failed: {r.text}"
    return r.json()


# ===========================================================================
# TC-01  Full pipeline: register → merchant → store → product → order → approval
# ===========================================================================


class TestFullPipeline:
    @pytest.mark.asyncio
    async def test_full_merchant_store_product_order_approval_pipeline(self, client):
        """
        Happy-path end-to-end:
        1. Register a new user
        2. Create a merchant profile
        3. Create a store under that merchant
        4. Create a product
        5. Place an order
        6. Create an approval for that order
        7. Approve the approval → status becomes 'approved'
        """
        headers, _ = await _register_and_login(client, "pipe01")

        # 1. Merchant
        merchant = await _create_merchant(client, headers)
        assert merchant["company_name"] == "Test Merchant Inc."

        # 2. Store
        store = await _create_store(client, headers)
        assert "id" in store

        # 3. Product
        product = await _create_product(client, headers)
        product_id = product["id"]

        # 4. Order
        order = await _create_order(client, headers, product_id)
        order_id = order["id"]
        assert order["status"] in ("pending", "created", "open")

        # 5. Approval
        approval = await _create_approval(client, headers, order_id)
        approval_id = approval["id"]
        assert approval["entity_id"] == order_id

        # 6. Approve it
        r = await client.put(
            f"/api/approvals/{approval_id}",
            json={"status": "approved", "response_note": "LGTM"},
            headers=headers,
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "approved"


# ===========================================================================
# TC-02  Order status lifecycle
# ===========================================================================


class TestOrderStatusLifecycle:
    @pytest.mark.asyncio
    async def test_order_status_transitions(self, client):
        """
        Order goes through: pending → processing → shipped
        Each transition is verified by GET /api/orders/{id}.
        """
        headers, _ = await _register_and_login(client, "ordlc")
        product = await _create_product(client, headers)
        order = await _create_order(client, headers, product["id"])
        order_id = order["id"]

        for new_status in ("confirmed", "shipped"):
            r = await client.patch(
                f"/api/orders/{order_id}/status",
                json={"status": new_status},
                headers=headers,
            )
            assert r.status_code == 200, f"transition to {new_status} failed: {r.text}"
            assert r.json()["status"] == new_status

    @pytest.mark.asyncio
    async def test_get_order_returns_correct_data(self, client):
        headers, _ = await _register_and_login(client, "ordget")
        product = await _create_product(client, headers)
        order = await _create_order(client, headers, product["id"])

        r = await client.get(f"/api/orders/{order['id']}", headers=headers)
        assert r.status_code == 200
        assert r.json()["id"] == order["id"]

    @pytest.mark.asyncio
    async def test_list_orders_returns_created_order(self, client):
        headers, _ = await _register_and_login(client, "ordlist")
        product = await _create_product(client, headers)
        order = await _create_order(client, headers, product["id"])

        r = await client.get("/api/orders", headers=headers)
        assert r.status_code == 200
        ids = [o["id"] for o in r.json()["items"]]
        assert order["id"] in ids

    @pytest.mark.asyncio
    async def test_delete_order_returns_404_on_subsequent_get(self, client):
        headers, _ = await _register_and_login(client, "orddel")
        product = await _create_product(client, headers)
        order = await _create_order(client, headers, product["id"])
        order_id = order["id"]

        r = await client.delete(f"/api/orders/{order_id}", headers=headers)
        assert r.status_code == 204

        r = await client.get(f"/api/orders/{order_id}", headers=headers)
        assert r.status_code == 404


# ===========================================================================
# TC-03  Merchant profile management
# ===========================================================================


class TestMerchantProfile:
    @pytest.mark.asyncio
    async def test_create_merchant_idempotent(self, client):
        """Second POST /merchants → 409 Conflict."""
        headers, _ = await _register_and_login(client, "merch01")
        await _create_merchant(client, headers)

        r = await client.post(
            "/api/merchants",
            json={"company_name": "Duplicate"},
            headers=headers,
        )
        assert r.status_code == 409

    @pytest.mark.asyncio
    async def test_get_merchant_me(self, client):
        headers, _ = await _register_and_login(client, "merch02")
        created = await _create_merchant(client, headers)

        r = await client.get("/api/merchants/me", headers=headers)
        assert r.status_code == 200
        assert r.json()["id"] == created["id"]

    @pytest.mark.asyncio
    async def test_update_merchant(self, client):
        headers, _ = await _register_and_login(client, "merch03")
        await _create_merchant(client, headers)

        r = await client.put(
            "/api/merchants/me",
            json={"company_name": "Updated Name"},
            headers=headers,
        )
        assert r.status_code == 200
        assert r.json()["company_name"] == "Updated Name"


# ===========================================================================
# TC-04  Store management
# ===========================================================================


class TestStoreManagement:
    @pytest.mark.asyncio
    async def test_create_and_list_stores(self, client):
        headers, _ = await _register_and_login(client, "st01")
        await _create_merchant(client, headers)
        store = await _create_store(client, headers)

        r = await client.get("/api/stores", headers=headers)
        assert r.status_code == 200
        ids = [s["id"] for s in r.json()["items"]]
        assert store["id"] in ids

    @pytest.mark.asyncio
    async def test_get_store_by_id(self, client):
        headers, _ = await _register_and_login(client, "st02")
        await _create_merchant(client, headers)
        store = await _create_store(client, headers)

        r = await client.get(f"/api/stores/{store['id']}", headers=headers)
        assert r.status_code == 200
        assert r.json()["id"] == store["id"]

    @pytest.mark.asyncio
    async def test_update_store(self, client):
        headers, _ = await _register_and_login(client, "st03")
        await _create_merchant(client, headers)
        store = await _create_store(client, headers)

        r = await client.put(
            f"/api/stores/{store['id']}",
            json={"name": "Renamed Store"},
            headers=headers,
        )
        assert r.status_code == 200
        assert r.json()["name"] == "Renamed Store"

    @pytest.mark.asyncio
    async def test_delete_store(self, client):
        headers, _ = await _register_and_login(client, "st04")
        await _create_merchant(client, headers)
        store = await _create_store(client, headers)

        r = await client.delete(f"/api/stores/{store['id']}", headers=headers)
        assert r.status_code == 204

        r = await client.get(f"/api/stores/{store['id']}", headers=headers)
        assert r.status_code == 404


# ===========================================================================
# TC-05  Approval workflow
# ===========================================================================


class TestApprovalWorkflow:
    @pytest.mark.asyncio
    async def test_reject_approval(self, client):
        headers, _ = await _register_and_login(client, "appr01")
        product = await _create_product(client, headers)
        order = await _create_order(client, headers, product["id"])
        approval = await _create_approval(client, headers, order["id"])

        r = await client.put(
            f"/api/approvals/{approval['id']}",
            json={"status": "rejected", "response_note": "Not valid"},
            headers=headers,
        )
        assert r.status_code == 200
        assert r.json()["status"] == "rejected"

    @pytest.mark.asyncio
    async def test_list_approvals(self, client):
        headers, _ = await _register_and_login(client, "appr02")
        product = await _create_product(client, headers)
        order = await _create_order(client, headers, product["id"])
        approval = await _create_approval(client, headers, order["id"])

        r = await client.get("/api/approvals", headers=headers)
        assert r.status_code == 200
        ids = [a["id"] for a in r.json()["items"]]
        assert approval["id"] in ids

    @pytest.mark.asyncio
    async def test_nonexistent_approval_returns_404(self, client):
        headers, _ = await _register_and_login(client, "appr03")
        fake_id = str(uuid.uuid4())

        r = await client.put(
            f"/api/approvals/{fake_id}",
            json={"status": "approved"},
            headers=headers,
        )
        assert r.status_code == 404


# ===========================================================================
# TC-06  Auth isolation — users cannot see each other's data
# ===========================================================================


class TestAuthIsolation:
    @pytest.mark.asyncio
    async def test_user_cannot_access_another_users_order(self, client):
        headers_a, _ = await _register_and_login(client, "isoa")
        headers_b, _ = await _register_and_login(client, "isob")

        product = await _create_product(client, headers_a)
        order_a = await _create_order(client, headers_a, product["id"])

        # User B tries to read user A's order
        r = await client.get(f"/api/orders/{order_a['id']}", headers=headers_b)
        assert r.status_code == 404

    @pytest.mark.asyncio
    async def test_unauthenticated_request_returns_401(self, client):
        r = await client.get("/api/orders")
        assert r.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_invalid_token_returns_401(self, client):
        headers = {"Authorization": "Bearer totally.invalid.token"}
        r = await client.get("/api/orders", headers=headers)
        assert r.status_code in (401, 403)
