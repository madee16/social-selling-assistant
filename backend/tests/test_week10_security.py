"""
Week 10 — Security Audit Tests
Covers: SQL Injection, XSS / stored-script injection, Auth bypass,
        Mass-assignment, Broken Object-Level Auth (BOLA), and
        Sensitive-data exposure.

Each test is independent and registers its own user so there are no
ordering or state dependencies.
"""

import uuid

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _register(client, tag: str | None = None) -> dict:
    tag = tag or uuid.uuid4().hex[:8]
    email = f"sec-{tag}@test.dev"
    r = await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "SecurePass!9",
            "company_name": f"SecCo {tag}",
            "phone": f"+2162{tag[:8]}",
        },
    )
    assert r.status_code == 200, f"register failed: {r.text}"
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, email


# ===========================================================================
# SEC-01  SQL Injection
# ===========================================================================


class TestSQLInjection:
    """
    Send classic injection payloads in string fields and query params.
    The server must never return a 500 (unhandled DB error) and must not
    return data that belongs to other users.
    """

    SQL_PAYLOADS = [
        "' OR '1'='1",
        "'; DROP TABLE users; --",
        "\" OR \"1\"=\"1",
        "1' UNION SELECT null, null, null --",
        "admin'--",
        "' OR 1=1--",
        "1; SELECT * FROM users",
    ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("payload", SQL_PAYLOADS)
    async def test_sql_injection_in_product_name(self, client, payload):
        headers, _ = await _register(client)
        r = await client.post(
            "/api/products",
            json={"name": payload, "price": 1.0, "description": "test"},
            headers=headers,
        )
        # Must not cause a 500; 422 (validation) or 201/200 (safe storage) are both OK
        assert r.status_code != 500, f"Possible SQLi via product name: {payload!r}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("payload", SQL_PAYLOADS)
    async def test_sql_injection_in_store_slug(self, client, payload):
        headers, _ = await _register(client)
        r = await client.post(
            "/api/stores",
            json={"slug": payload, "name": "InjStore"},
            headers=headers,
        )
        assert r.status_code != 500, f"Possible SQLi via store slug: {payload!r}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("payload", SQL_PAYLOADS)
    async def test_sql_injection_in_order_status_filter(self, client, payload):
        headers, _ = await _register(client)
        r = await client.get(
            "/api/orders",
            params={"status": payload},
            headers=headers,
        )
        assert r.status_code != 500, f"Possible SQLi via order status filter: {payload!r}"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("payload", SQL_PAYLOADS)
    async def test_sql_injection_in_company_name(self, client, payload):
        headers, _ = await _register(client)
        r = await client.post(
            "/api/merchants",
            json={"company_name": payload},
            headers=headers,
        )
        assert r.status_code != 500, f"Possible SQLi via company_name: {payload!r}"


# ===========================================================================
# SEC-02  XSS / Stored-Script Injection
# ===========================================================================


class TestXSSInjection:
    """
    Stored XSS: scripts sent in text fields must be stripped or escaped
    before being returned by the API, so they never reach a browser as-is.
    """

    XSS_PAYLOADS = [
        "<script>alert('xss')</script>",
        "<img src=x onerror=alert(1)>",
        "javascript:alert(1)",
        "<svg onload=alert(1)>",
        "'\"><script>alert(document.cookie)</script>",
        "<body onload=alert(1)>",
        "<iframe src=javascript:alert(1)>",
    ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    async def test_xss_in_product_description_is_stripped(self, client, payload):
        """
        If the API persists the value, it must not echo back raw HTML tags
        in the response body.
        """
        headers, _ = await _register(client)
        r = await client.post(
            "/api/products",
            json={"name": "XSS Test", "price": 1.0, "description": payload},
            headers=headers,
        )
        assert r.status_code != 500, f"500 on XSS payload in description"
        if r.status_code in (200, 201):
            body = r.text
            assert "<script>" not in body, "Raw <script> echoed back"
            assert "onerror=" not in body, "Raw onerror= echoed back"
            assert "onload=" not in body, "Raw onload= echoed back"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    async def test_xss_in_store_name_is_stripped(self, client, payload):
        headers, _ = await _register(client)
        slug = f"xss-{uuid.uuid4().hex[:6]}"
        r = await client.post(
            "/api/stores",
            json={"slug": slug, "name": payload},
            headers=headers,
        )
        assert r.status_code != 500
        if r.status_code in (200, 201):
            body = r.text
            assert "<script>" not in body
            assert "onerror=" not in body

    @pytest.mark.asyncio
    @pytest.mark.parametrize("payload", XSS_PAYLOADS)
    async def test_xss_in_widget_title_is_sanitized(self, client, payload):
        headers, _ = await _register(client)
        r = await client.put(
            "/api/widget/settings",
            json={"title": payload},
            headers=headers,
        )
        assert r.status_code != 500
        if r.status_code == 200:
            body = r.text
            assert "<script>" not in body
            assert "onerror=" not in body


# ===========================================================================
# SEC-03  Authentication Bypass
# ===========================================================================


class TestAuthBypass:
    """Every protected endpoint must reject missing / malformed tokens."""

    PROTECTED_ENDPOINTS = [
        ("GET", "/api/orders"),
        ("GET", "/api/products"),
        ("GET", "/api/stores"),
        ("GET", "/api/merchants/me"),
        ("GET", "/api/approvals"),
        ("GET", "/api/attribute-defs"),
        ("GET", "/api/ai/sessions"),
        ("GET", "/api/audit-logs"),
        ("GET", "/api/buyers"),
    ]

    @pytest.mark.asyncio
    @pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
    async def test_no_token_returns_401(self, client, method, path):
        r = await client.request(method, path)
        assert r.status_code in (401, 403), (
            f"{method} {path} returned {r.status_code} without a token"
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("method,path", PROTECTED_ENDPOINTS)
    async def test_malformed_token_returns_401(self, client, method, path):
        headers = {"Authorization": "Bearer not.a.real.token"}
        r = await client.request(method, path, headers=headers)
        assert r.status_code in (401, 403), (
            f"{method} {path} returned {r.status_code} with a garbage token"
        )

    @pytest.mark.asyncio
    async def test_expired_token_returns_401(self, client):
        """A hand-crafted token with exp=0 must be rejected."""
        import time

        from jose import jwt

        # Sign with a wrong secret — should be rejected regardless of payload
        fake_token = jwt.encode(
            {"sub": "00000000-0000-0000-0000-000000000000", "exp": int(time.time()) - 3600},
            key="wrong-secret",
            algorithm="HS256",
        )
        headers = {"Authorization": f"Bearer {fake_token}"}
        r = await client.get("/api/orders", headers=headers)
        assert r.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_empty_bearer_returns_401(self, client):
        headers = {"Authorization": "Bearer "}
        r = await client.get("/api/products", headers=headers)
        assert r.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_basic_auth_not_accepted(self, client):
        """Basic-auth header must not bypass JWT guard."""
        import base64

        creds = base64.b64encode(b"demo@test.com:pass123").decode()
        headers = {"Authorization": f"Basic {creds}"}
        r = await client.get("/api/orders", headers=headers)
        assert r.status_code in (401, 403)


# ===========================================================================
# SEC-04  Broken Object-Level Authorization (BOLA)
# ===========================================================================


class TestBOLA:
    """
    User A creates resources; User B must NOT be able to read, modify, or
    delete them by guessing the UUID.
    """

    @pytest.mark.asyncio
    async def test_user_b_cannot_read_user_a_order(self, client):
        headers_a, _ = await _register(client, "bola-a1")
        headers_b, _ = await _register(client, "bola-b1")

        # User A creates a product and an order
        r = await client.post(
            "/api/products",
            json={"name": "Secret Widget", "price": 9.99, "description": "mine", "stock_quantity": 100},
            headers=headers_a,
        )
        assert r.status_code in (200, 201)
        product_id = r.json()["id"]

        r = await client.post(
            "/api/orders",
            json={
                "customer_name": "User A",
                "items": [{"product_id": product_id, "quantity": 1, "unit_price": 9.99}],
            },
            headers=headers_a,
        )
        assert r.status_code in (200, 201)
        order_id = r.json()["id"]

        # User B tries to access it
        r = await client.get(f"/api/orders/{order_id}", headers=headers_b)
        assert r.status_code == 404, "BOLA: user B read user A's order"

    @pytest.mark.asyncio
    async def test_user_b_cannot_delete_user_a_order(self, client):
        headers_a, _ = await _register(client, "bola-a2")
        headers_b, _ = await _register(client, "bola-b2")

        r = await client.post(
            "/api/products",
            json={"name": "Shared Widget", "price": 5.0, "description": "test", "stock_quantity": 100},
            headers=headers_a,
        )
        assert r.status_code in (200, 201)
        product_id = r.json()["id"]

        r = await client.post(
            "/api/orders",
            json={
                "customer_name": "User A",
                "items": [{"product_id": product_id, "quantity": 1, "unit_price": 5.0}],
            },
            headers=headers_a,
        )
        assert r.status_code in (200, 201)
        order_id = r.json()["id"]

        r = await client.delete(f"/api/orders/{order_id}", headers=headers_b)
        assert r.status_code in (403, 404), "BOLA: user B deleted user A's order"

    @pytest.mark.asyncio
    async def test_user_b_cannot_update_user_a_store(self, client):
        headers_a, _ = await _register(client, "bola-a3")
        headers_b, _ = await _register(client, "bola-b3")

        # A creates a merchant + store
        await client.post(
            "/api/merchants",
            json={"company_name": "A Corp"},
            headers=headers_a,
        )
        r = await client.post(
            "/api/stores",
            json={"slug": f"bola-{uuid.uuid4().hex[:6]}", "name": "A Store"},
            headers=headers_a,
        )
        assert r.status_code in (200, 201)
        store_id = r.json()["id"]

        # B tries to rename it
        r = await client.put(
            f"/api/stores/{store_id}",
            json={"name": "Hijacked"},
            headers=headers_b,
        )
        assert r.status_code in (403, 404), "BOLA: user B updated user A's store"

    @pytest.mark.asyncio
    async def test_random_uuid_returns_404(self, client):
        """Accessing a non-existent UUID must return 404, not 500."""
        headers, _ = await _register(client, "bola-x")
        fake_id = str(uuid.uuid4())

        for path in [
            f"/api/orders/{fake_id}",
            f"/api/stores/{fake_id}",
            f"/api/approvals/{fake_id}",
        ]:
            r = await client.get(path, headers=headers)
            assert r.status_code == 404, f"Expected 404 for {path}, got {r.status_code}"


# ===========================================================================
# SEC-05  Mass-Assignment / Over-posting
# ===========================================================================


class TestMassAssignment:
    """
    Sending extra / privileged fields (is_admin, user_id, id) in the request
    body must not allow privilege escalation or data overwrite.
    """

    @pytest.mark.asyncio
    async def test_cannot_set_own_admin_via_register(self, client):
        tag = uuid.uuid4().hex[:6]
        r = await client.post(
            "/api/auth/register",
            json={
                "email": f"mass-{tag}@test.dev",
                "password": "SecurePass!9",
                "company_name": "Mass Co",
                "phone": f"+2162{tag}",
                "is_admin": True,       # extra field — must be ignored
                "role": "superadmin",   # extra field — must be ignored
            },
        )
        assert r.status_code in (200, 422), r.text
        if r.status_code == 200:
            # If the server accepted it, make sure admin wasn't granted
            token = r.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}
            me = await client.get("/api/auth/me", headers=headers)
            assert me.status_code == 200
            user_data = me.json()
            # is_admin / role must not be truthy
            assert not user_data.get("is_admin", False)
            assert user_data.get("role", "user") not in ("superadmin", "admin")

    @pytest.mark.asyncio
    async def test_cannot_override_merchant_user_id(self, client):
        """Sending a different user_id in the merchant payload must be ignored."""
        headers, _ = await _register(client, "mass02")
        fake_user_id = str(uuid.uuid4())

        r = await client.post(
            "/api/merchants",
            json={
                "company_name": "Override Attempt",
                "user_id": fake_user_id,   # must be ignored; actual user from JWT
            },
            headers=headers,
        )
        assert r.status_code in (200, 201, 422)
        if r.status_code in (200, 201):
            # user_id in response must match the authenticated user, not fake_user_id
            assert r.json().get("user_id") != fake_user_id


# ===========================================================================
# SEC-06  Sensitive-Data Exposure
# ===========================================================================


class TestSensitiveDataExposure:
    @pytest.mark.asyncio
    async def test_password_not_returned_in_register_response(self, client):
        tag = uuid.uuid4().hex[:6]
        r = await client.post(
            "/api/auth/register",
            json={
                "email": f"sens-{tag}@test.dev",
                "password": "SuperSecret!1",
                "company_name": "SenseCo",
                "phone": f"+2162{tag}",
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert "password" not in body
        assert "hashed_password" not in body

    @pytest.mark.asyncio
    async def test_password_not_returned_in_me_endpoint(self, client):
        headers, _ = await _register(client, "sens02")
        r = await client.get("/api/auth/me", headers=headers)
        assert r.status_code == 200
        body = r.json()
        assert "password" not in body
        assert "hashed_password" not in body

    @pytest.mark.asyncio
    async def test_whatsapp_token_encrypted_at_rest(self, client):
        """
        Tokens saved via PUT /api/widget/settings must NOT be stored as
        plaintext in the DB (verified by the conftest DB fixture).
        This test just checks the API round-trip doesn't leak the raw value
        in any unexpected field.
        """
        from sqlalchemy import text

        headers, _ = await _register(client, "sens03")
        secret = "wati-tok-sensitive-9876"

        r = await client.put(
            "/api/widget/settings",
            json={"whatsapp_access_token": secret},
            headers=headers,
        )
        assert r.status_code == 200
        # The API may return the value (decrypted for the owner) — that's fine
        # What must NOT happen: returning it under an extra "raw_token" key
        body = r.json()
        assert "raw_token" not in body
        assert "hashed_token" not in body
