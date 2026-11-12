import subprocess
import sys
import time

import httpx
import pytest


@pytest.fixture(scope="module")
def server():
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8002"],
        stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
    )
    time.sleep(4)
    yield
    proc.terminate()
    proc.wait()


@pytest.mark.asyncio
async def test_categories_and_products(server):
    base = "http://localhost:8002"
    async with httpx.AsyncClient(base_url=base, timeout=15) as c:
        r = await c.post("/api/auth/login", json={"email": "demo@test.com", "password": "pass123"})
        token = r.json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}

        r = await c.get("/api/categories", headers=h)
        assert r.status_code == 200
        initial_category_total = r.json()["total"]

        r = await c.get("/api/products", headers=h)
        assert r.status_code == 200
        initial_product_total = r.json()["total"]

        r = await c.post("/api/categories", json={"name": "Electronics"}, headers=h)
        assert r.status_code == 201
        cat_id = r.json()["id"]

        r = await c.get("/api/categories", headers=h)
        assert r.status_code == 200
        assert r.json()["total"] == initial_category_total + 1

        r = await c.post("/api/products", json={
            "name": "Laptop", "price": 999.99, "category_id": cat_id, "stock_quantity": 5
        }, headers=h)
        assert r.status_code == 201
        prod_id = r.json()["id"]

        r = await c.get("/api/products", headers=h)
        assert r.json()["total"] == initial_product_total + 1

        r = await c.get("/api/products?search=laptop", headers=h)
        assert any(product["id"] == prod_id for product in r.json()["items"])

        r = await c.put(f"/api/products/{prod_id}", json={"price": 899.99}, headers=h)
        assert r.json()["price"] == 899.99

        r = await c.delete(f"/api/products/{prod_id}", headers=h)
        assert r.status_code == 204

        r = await c.delete(f"/api/categories/{cat_id}", headers=h)
        assert r.status_code == 204

        print("\nAll Week 2 backend tests passed!")
