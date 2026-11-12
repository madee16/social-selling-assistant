"""Week 3 — Core CRUD route tests.

These tests exercise the management routes added during the Week 1/2 schema
window (merchants, stores, buyers, collections, attribute definitions,
governance/events, and AI sessions). They run against the local test Postgres
database defined in conftest.py (TEST_DATABASE_URL).

Each test registers its own unique account so the suite is independent of
the exact rows present in the shared test database.
"""
import uuid

import pytest

AUTH_HEADERS = {"Authorization": "Bearer {token}"}


def _unique_email(label: str) -> str:
    suffix = uuid.uuid4().hex[:8]
    return f"{label}-{suffix}@test.dev"


async def _register(client, label: str) -> dict:
    email = _unique_email(label)
    r = await client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "pass123",
            "company_name": f"Company {label}",
            "phone": "+21620000000",
        },
    )
    assert r.status_code == 200, f"register failed: {r.text}"
    return {"email": email, "token": r.json()["access_token"]}


def _headers(account: dict) -> dict:
    return {"Authorization": f"Bearer {account['token']}"}


async def _create_merchant(client, account: dict) -> dict:
    r = await client.post(
        "/api/merchants",
        json={"company_name": f"Test Merchant {account['email']}"},
        headers=_headers(account),
    )
    assert r.status_code == 201, f"create merchant failed: {r.text}"
    return r.json()


async def _create_store(client, account: dict, slug: str) -> dict:
    r = await client.post(
        "/api/stores",
        json={"name": slug.replace("-", " ").title(), "slug": slug},
        headers=_headers(account),
    )
    assert r.status_code == 201, f"create store failed: {r.text}"
    return r.json()


# ---------------------------------------------------------------------------
# Merchants
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_get_update_my_merchant(client):
    account = await _register(client, "merchant")
    h = _headers(account)

    created = await _create_merchant(client, account)
    assert created["company_name"].startswith("Test Merchant")
    assert created["verification_status"] == "pending"
    assert "id" in created

    me = (await client.get("/api/merchants/me", headers=h)).json()
    assert me["id"] == created["id"]

    updated = await client.put(
        "/api/merchants/me",
        json={"company_name": "Renamed Company", "verification_status": "verified"},
        headers=h,
    )
    assert updated.status_code == 200
    assert updated.json()["company_name"] == "Renamed Company"
    assert updated.json()["verification_status"] == "verified"


@pytest.mark.asyncio
async def test_merchant_create_duplicate_conflict(client):
    account = await _register(client, "merchantdup")
    h = _headers(account)
    await _create_merchant(client, account)
    r = await client.post("/api/merchants", json={"company_name": "Second"}, headers=h)
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_merchant_me_not_found_before_create(client):
    account = await _register(client, "merchantmissing")
    r = await client.get("/api/merchants/me", headers=_headers(account))
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_merchant_requires_auth(client):
    r = await client.post("/api/merchants", json={"company_name": "X"})
    assert r.status_code in (401, 403)


# ---------------------------------------------------------------------------
# Stores
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_store_full_crud_lifecycle(client):
    account = await _register(client, "store")
    h = _headers(account)
    slug = f"store-{uuid.uuid4().hex[:8]}"

    await _create_merchant(client, account)
    store = await _create_store(client, account, slug)
    assert store["slug"] == slug
    assert store["status"] == "active"

    listed = (await client.get("/api/stores", headers=h)).json()
    assert any(s["id"] == store["id"] for s in listed["items"])

    got = await client.get(f"/api/stores/{store['id']}", headers=h)
    assert got.status_code == 200
    assert got.json()["slug"] == slug

    updated = await client.put(
        f"/api/stores/{store['id']}", json={"name": "Renamed Store"}, headers=h
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Renamed Store"

    members = (await client.get(f"/api/stores/{store['id']}/members", headers=h)).json()
    assert members["total"] == 0

    deleted = await client.delete(f"/api/stores/{store['id']}", headers=h)
    assert deleted.status_code == 204

    gone = await client.get(f"/api/stores/{store['id']}", headers=h)
    assert gone.status_code == 404


@pytest.mark.asyncio
async def test_store_create_requires_merchant(client):
    account = await _register(client, "storenomerchant")
    slug = f"store-{uuid.uuid4().hex[:8]}"
    r = await client.post(
        "/api/stores", json={"name": "No Merchant Store", "slug": slug}, headers=_headers(account)
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_store_invalid_slug_rejected(client):
    account = await _register(client, "storebadslug")
    await _create_merchant(client, account)
    r = await client.post(
        "/api/stores",
        json={"name": "Bad Slug", "slug": "Not A Valid Slug!"},
        headers=_headers(account),
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_store_get_missing_404(client):
    account = await _register(client, "storemissing")
    r = await client.get("/api/stores/00000000-0000-0000-0000-000000000000", headers=_headers(account))
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Buyers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_buyer_full_crud_lifecycle(client):
    account = await _register(client, "buyer")
    h = _headers(account)

    created = await client.post(
        "/api/buyers",
        json={"email": _unique_email("buy"), "name": "Sam Buyer", "phone": "+21621000000"},
        headers=h,
    )
    assert created.status_code == 201
    buyer = created.json()
    assert buyer["name"] == "Sam Buyer"

    listed = (await client.get("/api/buyers", headers=h)).json()
    assert any(b["id"] == buyer["id"] for b in listed["items"])

    searched = await client.get("/api/buyers", params={"search": "Sam"}, headers=h)
    assert searched.status_code == 200
    assert any(b["id"] == buyer["id"] for b in searched.json()["items"])

    got = await client.get(f"/api/buyers/{buyer['id']}", headers=h)
    assert got.status_code == 200

    updated = await client.put(
        f"/api/buyers/{buyer['id']}",
        json={"name": "Sam Updated", "preferences": {"lang": "fr"}},
        headers=h,
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Sam Updated"
    assert updated.json()["preferences"] == {"lang": "fr"}

    deleted = await client.delete(f"/api/buyers/{buyer['id']}", headers=h)
    assert deleted.status_code == 204

    gone = await client.get(f"/api/buyers/{buyer['id']}", headers=h)
    assert gone.status_code == 404


@pytest.mark.asyncio
async def test_buyer_get_missing_404(client):
    account = await _register(client, "buyermissing")
    r = await client.get("/api/buyers/00000000-0000-0000-0000-000000000000", headers=_headers(account))
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Collections
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_collection_full_crud(client):
    account = await _register(client, "collection")
    h = _headers(account)
    await _create_merchant(client, account)
    slug = f"sale-{uuid.uuid4().hex[:8]}"

    created = await client.post(
        "/api/collections",
        json={"name": "Summer Sale", "slug": slug, "description": "Summer items", "sort_order": 1},
        headers=h,
    )
    assert created.status_code == 201
    coll = created.json()
    assert coll["slug"] == slug
    assert coll["sort_order"] == 1

    listed = (await client.get("/api/collections", headers=h)).json()
    assert any(c["id"] == coll["id"] for c in listed["items"])

    got = await client.get(f"/api/collections/{coll['id']}", headers=h)
    assert got.status_code == 200

    updated = await client.put(
        f"/api/collections/{coll['id']}", json={"is_visible": False}, headers=h
    )
    assert updated.status_code == 200
    assert updated.json()["is_visible"] is False

    deleted = await client.delete(f"/api/collections/{coll['id']}", headers=h)
    assert deleted.status_code == 204

    gone = await client.get(f"/api/collections/{coll['id']}", headers=h)
    assert gone.status_code == 404


@pytest.mark.asyncio
async def test_collection_create_requires_merchant(client):
    account = await _register(client, "collectionnomerchant")
    slug = f"sale-{uuid.uuid4().hex[:8]}"
    r = await client.post(
        "/api/collections", json={"name": "No Merchant", "slug": slug}, headers=_headers(account)
    )
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_collection_invalid_slug_rejected(client):
    account = await _register(client, "collectionbadslug")
    await _create_merchant(client, account)
    r = await client.post(
        "/api/collections",
        json={"name": "Bad Slug", "slug": "Bad Slug!"},
        headers=_headers(account),
    )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Attribute definitions (catalog)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_attribute_def_crud_and_validation(client):
    account = await _register(client, "attr")
    h = _headers(account)
    await _create_merchant(client, account)

    created = await client.post(
        "/api/attribute-defs",
        json={
            "name": "Color",
            "attribute_type": "select",
            "values": ["red", "blue"],
            "is_filterable": True,
        },
        headers=h,
    )
    assert created.status_code == 201
    attr = created.json()
    assert attr["name"] == "Color"
    assert attr["values"] == ["red", "blue"]
    assert attr["is_filterable"] is True

    listed = (await client.get("/api/attribute-defs", headers=h)).json()
    assert any(a["id"] == attr["id"] for a in listed["items"])

    updated = await client.put(
        f"/api/attribute-defs/{attr['id']}", json={"values": ["red", "blue", "green"]}, headers=h
    )
    assert updated.status_code == 200
    assert updated.json()["values"] == ["red", "blue", "green"]

    invalid = await client.post(
        "/api/attribute-defs", json={"name": "Bad", "attribute_type": "not_a_type"}, headers=h
    )
    assert invalid.status_code == 422

    deleted = await client.delete(f"/api/attribute-defs/{attr['id']}", headers=h)
    assert deleted.status_code == 204

    listed_after = (await client.get("/api/attribute-defs", headers=h)).json()
    assert not any(a["id"] == attr["id"] for a in listed_after["items"])


@pytest.mark.asyncio
async def test_attribute_def_requires_merchant(client):
    account = await _register(client, "attrnomerchant")
    r = await client.post(
        "/api/attribute-defs", json={"name": "Color"}, headers=_headers(account)
    )
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Governance: approvals, automation rules, events, audit logs
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_approval_create_list_update(client):
    account = await _register(client, "approval")
    h = _headers(account)

    created = await client.post(
        "/api/approvals",
        json={
            "approval_type": "product",
            "entity_type": "product",
            "entity_id": "prod-1",
            "title": "Approve laptop",
        },
        headers=h,
    )
    assert created.status_code == 201
    approval = created.json()
    assert approval["status"] == "pending"

    listed = (await client.get("/api/approvals", headers=h)).json()
    assert any(a["id"] == approval["id"] for a in listed["items"])

    updated = await client.put(
        f"/api/approvals/{approval['id']}",
        json={"status": "approved", "rejection_reason": None},
        headers=h,
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "approved"

    filtered = (await client.get("/api/approvals", params={"status": "approved"}, headers=h)).json()
    assert any(a["id"] == approval["id"] for a in filtered["items"])


@pytest.mark.asyncio
async def test_automation_rule_crud_requires_merchant(client):
    account = await _register(client, "rule")
    h = _headers(account)

    no_merchant = await client.post(
        "/api/automation-rules",
        json={"name": "Rule", "event_type": "order_created"},
        headers=h,
    )
    assert no_merchant.status_code == 404

    await _create_merchant(client, account)
    created = await client.post(
        "/api/automation-rules",
        json={
            "name": "Low stock alert",
            "event_type": "inventory_low",
            "priority": 3,
            "is_active": True,
        },
        headers=h,
    )
    assert created.status_code == 201
    rule = created.json()

    listed = (await client.get("/api/automation-rules", headers=h)).json()
    assert any(r["id"] == rule["id"] for r in listed["items"])

    active = (await client.get("/api/automation-rules", params={"active_only": "true"}, headers=h)).json()
    assert any(r["id"] == rule["id"] for r in active["items"])

    updated = await client.put(
        f"/api/automation-rules/{rule['id']}", json={"is_active": False}, headers=h
    )
    assert updated.status_code == 200
    assert updated.json()["is_active"] is False

    deleted = await client.delete(f"/api/automation-rules/{rule['id']}", headers=h)
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_event_crud(client):
    account = await _register(client, "event")
    h = _headers(account)

    created = await client.post(
        "/api/events",
        json={
            "event_type": "campaign",
            "entity_type": "product",
            "entity_id": "p-1",
            "payload": {"discount": 10},
        },
        headers=h,
    )
    assert created.status_code == 201
    event = created.json()

    listed = (await client.get("/api/events", headers=h)).json()
    assert any(e["id"] == event["id"] for e in listed["items"])

    typed = (await client.get("/api/events", params={"event_type": "campaign"}, headers=h)).json()
    assert any(e["id"] == event["id"] for e in typed["items"])

    got = await client.get(f"/api/events/{event['id']}", headers=h)
    assert got.status_code == 200

    updated = await client.put(
        f"/api/events/{event['id']}", json={"event_type": "sale"}, headers=h
    )
    assert updated.status_code == 200
    assert updated.json()["event_type"] == "sale"

    deleted = await client.delete(f"/api/events/{event['id']}", headers=h)
    assert deleted.status_code == 204

    gone = await client.get(f"/api/events/{event['id']}", headers=h)
    assert gone.status_code == 404


@pytest.mark.asyncio
async def test_event_collections_and_product_gaps(client):
    account = await _register(client, "eventflow")
    h = _headers(account)

    event = (await client.post(
        "/api/events", json={"event_type": "sale"}, headers=h
    )).json()

    product = (await client.post(
        "/api/products",
        json={"name": "Gap Product", "price": 12.5},
        headers=h,
    )).json()
    assert "id" in product

    collection = (await client.post(
        f"/api/events/{event['id']}/collections",
        json={"collection_type": "curated", "collection_id": "col-1"},
        headers=h,
    )).json()
    assert collection["event_id"] == event["id"]

    listed_collections = (await client.get(f"/api/events/{event['id']}/collections", headers=h)).json()
    assert any(c["id"] == collection["id"] for c in listed_collections["items"])

    gap = (await client.post(
        f"/api/event-collections/{collection['id']}/gaps",
        json={"product_id": product["id"], "gap_type": "missing_image"},
        headers=h,
    )).json()
    assert gap["event_collection_id"] == collection["id"]

    gaps = (await client.get(f"/api/event-collections/{collection['id']}/gaps", headers=h)).json()
    assert gaps["total"] >= 1


@pytest.mark.asyncio
async def test_audit_log_create_list(client):
    account = await _register(client, "audit")
    h = _headers(account)

    created = await client.post(
        "/api/audit-logs",
        json={"action": "product.create", "entity_type": "product", "entity_id": "p-1", "details": {"ok": True}},
        headers=h,
    )
    assert created.status_code == 201

    listed = (await client.get("/api/audit-logs", headers=h)).json()
    assert any(log["action"] == "product.create" for log in listed["items"])


@pytest.mark.asyncio
async def test_consent_record_create_update(client):
    account = await _register(client, "consent")
    h = _headers(account)

    buyer = (await client.post(
        "/api/buyers",
        json={"email": _unique_email("consentbuy"), "name": "Consent Buyer"},
        headers=h,
    )).json()

    created = await client.post(
        "/api/consent-records",
        json={
            "buyer_id": buyer["id"],
            "consent_type": "marketing_email",
            "granted": True,
        },
        headers=h,
    )
    assert created.status_code == 201
    record = created.json()

    updated = await client.put(
        f"/api/consent-records/{record['id']}", json={"granted": False}, headers=h
    )
    assert updated.status_code == 200
    assert updated.json()["granted"] is False


# ---------------------------------------------------------------------------
# AI sessions / messages / tool calls
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ai_session_message_tool_call_flow(client):
    account = await _register(client, "ai")
    h = _headers(account)
    await _create_merchant(client, account)
    store = await _create_store(client, account, f"ai-store-{uuid.uuid4().hex[:8]}")

    created = await client.post(
        "/api/ai/sessions",
        json={"store_id": store["id"], "intent": "product_inquiry", "status": "active"},
        headers=h,
    )
    assert created.status_code == 201
    session = created.json()
    assert session["total_messages"] == 0

    listed = (await client.get("/api/ai/sessions", headers=h)).json()
    assert any(s["id"] == session["id"] for s in listed["items"])

    got = await client.get(f"/api/ai/sessions/{session['id']}", headers=h)
    assert got.status_code == 200

    msg = await client.post(
        f"/api/ai/sessions/{session['id']}/messages",
        json={"role": "user", "content": "how much is the laptop?", "confidence": 0.9},
        headers=h,
    )
    assert msg.status_code == 201
    message = msg.json()
    assert message["content"] == "how much is the laptop?"

    refreshed = (await client.get(f"/api/ai/sessions/{session['id']}", headers=h)).json()
    assert refreshed["total_messages"] == 1

    messages = (await client.get(f"/api/ai/sessions/{session['id']}/messages", headers=h)).json()
    assert any(m["id"] == message["id"] for m in messages["items"])

    tool = await client.post(
        f"/api/ai/sessions/{session['id']}/tool-calls",
        json={"tool_name": "search_products", "arguments": {"q": "laptop"}},
        headers=h,
    )
    assert tool.status_code == 201
    call = tool.json()
    assert call["tool_name"] == "search_products"

    calls = (await client.get(f"/api/ai/sessions/{session['id']}/tool-calls", headers=h)).json()
    assert any(c["id"] == call["id"] for c in calls["items"])

    updated = await client.put(
        f"/api/ai/sessions/{session['id']}", json={"status": "closed"}, headers=h
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "closed"

    deleted = await client.delete(f"/api/ai/sessions/{session['id']}", headers=h)
    assert deleted.status_code == 204

    gone = await client.get(f"/api/ai/sessions/{session['id']}", headers=h)
    assert gone.status_code == 404


@pytest.mark.asyncio
async def test_ai_session_not_found_for_other_user(client):
    account_a = await _register(client, "aistore_a")
    account_b = await _register(client, "aistore_b")
    await _create_merchant(client, account_a)
    store_a = await _create_store(client, account_a, f"ai-a-{uuid.uuid4().hex[:8]}")

    session = (await client.post(
        "/api/ai/sessions",
        json={"store_id": store_a["id"]},
        headers=_headers(account_a),
    )).json()

    # User B cannot create sessions visible in user A's store or read them
    r = await client.get(f"/api/ai/sessions/{session['id']}", headers=_headers(account_b))
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_ai_tool_call_requires_message_first(client):
    account = await _register(client, "aitool")
    h = _headers(account)
    await _create_merchant(client, account)
    store = await _create_store(client, account, f"ai-tool-{uuid.uuid4().hex[:8]}")

    session = (await client.post(
        "/api/ai/sessions", json={"store_id": store["id"]}, headers=h
    )).json()

    r = await client.post(
        f"/api/ai/sessions/{session['id']}/tool-calls",
        json={"tool_name": "x", "arguments": {}},
        headers=h,
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_inventory_variant_price_crud(client):
    account = await _register(client, "catalog")
    h = _headers(account)
    await _create_merchant(client, account)
    store = await _create_store(client, account, f"catalog-{uuid.uuid4().hex[:8]}")
    product = (await client.post(
        "/api/products", json={"name": "Catalog Widget", "price": 10.0}, headers=h
    )).json()
    pid = product["id"]

    inv = (await client.post(
        f"/api/products/{pid}/inventory",
        json={"store_id": store["id"], "quantity": 20, "reserved_quantity": 2, "low_stock_threshold": 5},
        headers=h,
    )).json()
    assert inv["quantity"] == 20 and inv["reserved_quantity"] == 2
    up_inv = await client.put(f"/api/inventory/{inv['id']}", json={"quantity": 15}, headers=h)
    assert up_inv.status_code == 200 and up_inv.json()["quantity"] == 15
    inv_list = (await client.get(f"/api/products/{pid}/inventory", headers=h)).json()
    assert any(r["id"] == inv["id"] for r in inv_list["items"])

    var = (await client.post(
        f"/api/products/{pid}/variants",
        json={"name": "Blue L", "sku": "blue-l", "quantity": 5},
        headers=h,
    )).json()
    assert var["name"] == "Blue L"
    up_var = await client.put(f"/api/variants/{var['id']}", json={"quantity": 7}, headers=h)
    assert up_var.status_code == 200 and up_var.json()["quantity"] == 7
    var_list = (await client.get(f"/api/products/{pid}/variants", headers=h)).json()
    assert any(v["id"] == var["id"] for v in var_list["items"])

    price = (await client.post(
        f"/api/products/{pid}/prices",
        json={"store_id": store["id"], "amount": 19.99, "currency": "TND"},
        headers=h,
    )).json()
    assert price["amount"] == 19.99
    up_price = await client.put(f"/api/prices/{price['id']}", json={"sale_price": 14.99}, headers=h)
    assert up_price.status_code == 200 and up_price.json()["sale_price"] == 14.99
    price_list = (await client.get(f"/api/products/{pid}/prices", headers=h)).json()
    assert any(p["id"] == price["id"] for p in price_list["items"])

    assert (await client.delete(f"/api/inventory/{inv['id']}", headers=h)).status_code == 204
    assert (await client.delete(f"/api/variants/{var['id']}", headers=h)).status_code == 204
    assert (await client.delete(f"/api/prices/{price['id']}", headers=h)).status_code == 204
