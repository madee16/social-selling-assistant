"""Tests for AI Auto-SEO Generation, Rubric Calculation, Dynamic Sitemap XML, and SSR Social Share Pages."""

import json
import uuid
import xml.etree.ElementTree as ET

import pytest
from sqlalchemy import select

from app.models.category import Category
from app.models.merchant import Merchant
from app.models.product import Product
from app.models.product_score import ProductScore
from app.models.seller_trust_score import SellerTrustScore
from app.models.seo_data import SeoData
from app.models.seo_score import SeoScore
from app.models.store import Store


async def _register_and_get_auth(client, tag: str):
    reg = await client.post(
        "/api/auth/register",
        json={
            "email": f"seo-{tag}@test.dev",
            "password": "Password123!",
            "company_name": f"SEO Co {tag}",
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
class TestSeoAiAndSsr:
    async def test_seo_generate_product_metadata_and_score(self, client, db_session):
        tag = uuid.uuid4().hex[:6]
        headers, user_id = await _register_and_get_auth(client, tag)

        merchant = Merchant(
            user_id=user_id,
            company_name=f"Boutique Artisanale {tag}",
            verification_status="verified",
        )
        db_session.add(merchant)
        await db_session.flush()

        store = Store(
            merchant_id=merchant.id,
            slug=f"store-seo-{tag}",
            name=f"Boutique Artisanale {tag}",
        )
        db_session.add(store)
        await db_session.flush()

        cat = Category(
            user_id=user_id,
            store_id=store.id,
            name="Artisanat Tunisien",
        )
        db_session.add(cat)
        await db_session.flush()

        product = Product(
            user_id=user_id,
            store_id=store.id,
            category_id=cat.id,
            name="Kaftan Traditionnel Tunisien Brodé Main",
            description="Superbe kaftan tunisien brodé à la main par des maîtres artisans avec fil de soie.",
            price=220.00,
            stock_quantity=12,
            image_url="https://images.unsplash.com/photo-1515372039744-b8f02a3ae446?w=800",
            is_active=True,
        )
        db_session.add(product)
        await db_session.commit()

        # 2. Call AI SEO generation endpoint
        res = await client.post(
            f"/api/seo/product/{product.id}/generate",
            headers=headers,
        )
        assert res.status_code == 200, res.text
        data = res.json()

        assert "seo_data" in data
        assert "seo_score" in data
        seo_data = data["seo_data"]
        seo_score = data["seo_score"]

        # Validate SeoData fields
        assert seo_data["entity_type"] == "product"
        assert seo_data["entity_id"] == str(product.id)
        assert 50 <= len(seo_data["title"]) <= 60
        assert 120 <= len(seo_data["description"]) <= 155
        assert isinstance(seo_data["keywords"], list)
        assert 6 <= len(seo_data["keywords"]) <= 10
        assert any("تونس" in kw or "\u0600" <= kw[0] <= "\u06FF" for kw in seo_data["keywords"])
        assert seo_data["slug"] is not None
        assert seo_data["is_indexable"] is True
        assert seo_data["canonical_url"].startswith("/share/product/")

        # Validate SeoScore rubric
        assert seo_score["overall_score"] is not None
        assert seo_score["overall_score"] >= 80.0
        assert seo_score["meta_score"] is not None
        assert seo_score["meta_score"] >= 80.0
        assert seo_score["keyword_score"] is not None
        assert seo_score["keyword_score"] >= 80.0
        assert seo_score["structure_score"] is not None
        assert seo_score["structure_score"] >= 80.0
        assert "breakdown" in seo_score["detail"]

        # Verify ProductScore synchronization in DB
        ps_res = await db_session.execute(
            select(ProductScore).where(
                ProductScore.product_id == product.id,
                ProductScore.score_type == "seo",
            )
        )
        prod_score = ps_res.scalar_one_or_none()
        assert prod_score is not None
        assert prod_score.score == seo_score["overall_score"]

    async def test_seo_generate_idempotency_upsert(self, client, db_session):
        tag = uuid.uuid4().hex[:6]
        headers, user_id = await _register_and_get_auth(client, tag)

        product = Product(
            user_id=user_id,
            name=f"Tapis Berbère Artisanal {tag}",
            description="Tapis tissé à la main en pure laine naturelle de montagne.",
            price=350.00,
            stock_quantity=3,
            is_active=True,
        )
        db_session.add(product)
        await db_session.commit()

        # First call
        res1 = await client.post(f"/api/seo/product/{product.id}/generate", headers=headers)
        assert res1.status_code == 200
        seo1_id = res1.json()["seo_data"]["id"]

        # Second call
        res2 = await client.post(f"/api/seo/product/{product.id}/generate", headers=headers)
        assert res2.status_code == 200
        seo2_id = res2.json()["seo_data"]["id"]

        # Idempotent: same SeoData ID is updated, not duplicated
        assert seo1_id == seo2_id

        count_res = await db_session.execute(
            select(SeoData).where(
                SeoData.entity_type == "product",
                SeoData.entity_id == product.id,
            )
        )
        assert len(count_res.scalars().all()) == 1

    async def test_seo_generate_invalid_inputs(self, client, db_session):
        tag = uuid.uuid4().hex[:6]
        headers, _ = await _register_and_get_auth(client, tag)
        fake_uuid = uuid.uuid4()

        # Nonexistent product -> 404
        r404 = await client.post(f"/api/seo/product/{fake_uuid}/generate", headers=headers)
        assert r404.status_code == 404
        assert "not found" in r404.json()["detail"].lower()

        # Unsupported entity type -> 400
        r400 = await client.post(f"/api/seo/collection/{fake_uuid}/generate", headers=headers)
        assert r400.status_code == 400
        assert "unsupported" in r400.json()["detail"].lower()

        # Invalid UUID -> 400
        r_bad_uuid = await client.post("/api/seo/product/not-a-valid-uuid-123/generate", headers=headers)
        assert r_bad_uuid.status_code == 400

    async def test_sitemap_xml_endpoints(self, client, db_session):
        tag = uuid.uuid4().hex[:6]
        headers, user_id = await _register_and_get_auth(client, tag)

        p1 = Product(
            user_id=user_id,
            name=f"Poterie de Nabeul {tag}",
            description="Plat traditionnel en terre cuite émaillée de haute qualité.",
            price=45.00,
            stock_quantity=20,
            is_active=True,
        )
        db_session.add(p1)
        await db_session.commit()

        # Generate indexable SEO
        gen_res = await client.post(f"/api/seo/product/{p1.id}/generate", headers=headers)
        assert gen_res.status_code == 200
        slug1 = gen_res.json()["seo_data"]["slug"]

        # Add a non-indexable record directly
        non_indexable = SeoData(
            entity_type="product",
            entity_id=uuid.uuid4(),
            title="Private Draft Product",
            slug=f"draft-{tag}",
            is_indexable=False,
        )
        db_session.add(non_indexable)
        await db_session.commit()

        # Test both /sitemap.xml and /api/seo/sitemap.xml
        for url in ("/sitemap.xml", "/api/seo/sitemap.xml"):
            res = await client.get(url)
            assert res.status_code == 200
            assert "application/xml" in res.headers["content-type"]
            xml_text = res.text

            # Parse XML
            root = ET.fromstring(xml_text)
            assert "urlset" in root.tag

            # Verify indexable entry is present
            assert f"/share/product/{slug1}" in xml_text
            # Verify non-indexable draft is NOT in sitemap
            assert f"draft-{tag}" not in xml_text

    async def test_ssr_share_product_page_opengraph_and_schema(self, client, db_session):
        tag = uuid.uuid4().hex[:6]
        headers, user_id = await _register_and_get_auth(client, tag)

        # Attach merchant and seller trust score
        merchant = Merchant(
            user_id=user_id,
            company_name=f"Artisans Réunis {tag}",
            verification_status="verified",
        )
        db_session.add(merchant)
        await db_session.flush()

        trust = SellerTrustScore(
            seller_id=merchant.id,
            score=94.5,
            level="gold",
        )
        db_session.add(trust)
        await db_session.flush()

        product = Product(
            user_id=user_id,
            name=f"Service à Thé en Cuivre Ciselé {tag}",
            description="Ensemble théière et 6 verres traditionnels ciselés main en cuivre pur.",
            price=165.00,
            stock_quantity=7,
            image_url="https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=800",
            is_active=True,
        )
        db_session.add(product)
        await db_session.commit()

        # Generate SEO metadata
        gen_res = await client.post(f"/api/seo/product/{product.id}/generate", headers=headers)
        assert gen_res.status_code == 200
        slug = gen_res.json()["seo_data"]["slug"]

        # Test SSR HTML endpoints (both /share/product/{slug} and /api/seo/share/product/{slug})
        for share_url in (f"/share/product/{slug}", f"/api/seo/share/product/{slug}"):
            res = await client.get(share_url)
            assert res.status_code == 200
            assert "text/html" in res.headers["content-type"]
            html_text = res.text

            # 1. OpenGraph meta tags check
            assert '<meta property="og:title"' in html_text
            assert '<meta property="og:description"' in html_text
            assert '<meta property="og:type" content="product">' in html_text
            assert '<meta property="og:image"' in html_text
            assert '<link rel="canonical"' in html_text

            # 2. Schema.org JSON-LD check
            assert '<script type="application/ld+json">' in html_text
            json_start = html_text.find('<script type="application/ld+json">') + len('<script type="application/ld+json">')
            json_end = html_text.find('</script>', json_start)
            json_str = html_text[json_start:json_end].strip()
            schema_data = json.loads(json_str)

            assert schema_data["@type"] == "Product"
            assert schema_data["name"] == product.name
            assert schema_data["offers"]["priceCurrency"] == "TND"
            assert float(schema_data["offers"]["price"]) == 165.00
            assert schema_data["offers"]["availability"] == "https://schema.org/InStock"
            assert schema_data["sku"] == str(product.id)

            # 3. HTML UI elements
            assert "165.00" in html_text
            assert "TND" in html_text
            assert "En Stock" in html_text
            assert "★ Gold" in html_text or "Gold" in html_text
            assert 'src="/widget.js"' in html_text
            assert "Commander avec l&#39;Assistant IA" in html_text or "Commander avec l'Assistant IA" in html_text

    async def test_ssr_share_product_out_of_stock(self, client, db_session):
        tag = uuid.uuid4().hex[:6]
        headers, user_id = await _register_and_get_auth(client, tag)

        product = Product(
            user_id=user_id,
            name=f"Fouta Tunisienne Rayée {tag}",
            description="Fouta traditionnelle en coton peigné.",
            price=35.00,
            stock_quantity=0,  # Out of stock
            is_active=True,
        )
        db_session.add(product)
        await db_session.commit()

        gen_res = await client.post(f"/api/seo/product/{product.id}/generate", headers=headers)
        assert gen_res.status_code == 200
        slug = gen_res.json()["seo_data"]["slug"]

        res = await client.get(f"/share/product/{slug}")
        assert res.status_code == 200
        html_text = res.text

        # Availability in Schema.org must be OutOfStock
        assert "https://schema.org/OutOfStock" in html_text
        assert "Rupture de Stock" in html_text

    async def test_ssr_share_nonexistent_returns_404(self, client):
        res = await client.get("/share/product/this-product-does-not-exist-at-all-999")
        assert res.status_code == 404
        assert "text/html" in res.headers["content-type"]
        assert "non trouvé" in res.text.lower()

    async def test_seo_generate_store_metadata_and_ssr_share(self, client, db_session):
        tag = uuid.uuid4().hex[:6]
        headers, user_id = await _register_and_get_auth(client, tag)

        # Store merchant_id references merchants.id, not users.id
        merchant = Merchant(
            user_id=user_id,
            company_name=f"Médina Co {tag}",
            verification_status="verified",
        )
        db_session.add(merchant)
        await db_session.flush()

        store = Store(
            merchant_id=merchant.id,
            slug=f"boutique-medina-{tag}",
            name=f"Médina Épicerie Fine {tag}",
            domain=f"medina-{tag}.tn",
        )
        db_session.add(store)
        await db_session.commit()

        # Generate Store SEO
        gen_res = await client.post(f"/api/seo/store/{store.id}/generate", headers=headers)
        assert gen_res.status_code == 200
        data = gen_res.json()
        assert data["seo_data"]["entity_type"] == "store"
        assert data["seo_data"]["entity_id"] == str(store.id)
        assert data["seo_score"]["overall_score"] is not None

        # SSR Store Share Page
        res = await client.get(f"/share/store/{store.slug}")
        assert res.status_code == 200
        assert store.name in res.text
        assert 'src="/widget.js"' in res.text
