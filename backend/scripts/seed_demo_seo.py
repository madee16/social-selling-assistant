"""
Demo SEO Data Seed Script
=========================
Inserts realistic demo SEO entries, scores, seller-trust records, and
product-score records linked directly to the store's real catalog products
via the live REST API so the SEO & Growth page works end-to-end out of the box.

Usage:
    python scripts/seed_demo_seo.py [--base-url http://localhost:8000] [--email demo@test.com] [--password pass123] [--clean]

The script is idempotent: it checks existing slugs before inserting.
Use --clean to remove pre-existing SEO entries before seeding.
"""

import argparse
import sys
import uuid
from typing import Any

import httpx

# ---------------------------------------------------------------------------
# Trust & Score fixtures
# ---------------------------------------------------------------------------

TRUST_RECORDS = [
    {
        "score": 88,
        "level": "gold",
        "components": {
            "delivery_rate": 94,
            "return_rate": 3,
            "review_score": 4.6,
            "dispute_rate": 1.2,
            "response_time_hours": 2,
        },
    },
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def login(base_url: str, email: str, password: str) -> str:
    r = httpx.post(f"{base_url}/api/auth/login", json={"email": email, "password": password}, timeout=10)
    r.raise_for_status()
    token = r.json().get("access_token")
    if not token:
        raise ValueError(f"No token in login response: {r.text}")
    print(f"✓ Logged in as {email}")
    return token


def clean_existing_seo(base_url: str, headers: dict[str, str]) -> None:
    """Delete existing SEO records to ensure a fresh, clean slate."""
    r = httpx.get(f"{base_url}/api/seo", headers=headers, params={"page_size": 100}, timeout=10)
    if r.status_code == 200:
        items = r.json().get("items", [])
        if items:
            print(f"\n🧹 Cleaning up {len(items)} existing SEO entries…")
            for item in items:
                try:
                    httpx.delete(f"{base_url}/api/seo/{item['id']}", headers=headers, timeout=10)
                except Exception as exc:
                    print(f"  Warning deleting SEO record {item['id']}: {exc}")
            print("✓ Old SEO records cleaned")


def get_or_create_store(base_url: str, headers: dict[str, str]) -> dict[str, Any] | None:
    """Fetch the active store, or create a demo store if none exists."""
    r = httpx.get(f"{base_url}/api/stores", headers=headers, params={"page_size": 1}, timeout=10)
    if r.status_code == 200:
        items = r.json().get("items", [])
        if items:
            return items[0]

    # Create a fallback store
    r2 = httpx.post(
        f"{base_url}/api/stores",
        headers=headers,
        json={"name": "Artisanat & Déco Tunisie", "domain": "artisanat-deco.tn"},
        timeout=10,
    )
    if r2.status_code in (200, 201):
        store = r2.json()
        print(f"  Created demo store: {store.get('name')} ({store.get('id')})")
        return store
    return None


def get_or_create_products(base_url: str, headers: dict[str, str], store_id: str | None) -> list[dict[str, Any]]:
    """Retrieve catalog products, creating realistic demo ones if none exist."""
    r = httpx.get(f"{base_url}/api/products", headers=headers, params={"page_size": 20}, timeout=10)
    if r.status_code == 200:
        items = r.json().get("items", [])
        if items:
            return items

    # Create demo products
    fixtures = [
        {"name": "Potiche en Céramique de Nabeul", "price": 45.0, "description": "Poterie artisanale peinte à la main."},
        {"name": "Tapis Berbère Margoum 100% Laine", "price": 180.0, "description": "Tapis traditionnel tissé main à Kairouan."},
        {"name": "Service à Café en Cuivre Martelé", "price": 95.0, "description": "Plateau artisanal avec tasses gravées."},
    ]
    created = []
    for f in fixtures:
        payload = {**f, "stock_quantity": 10, "is_active": True}
        if store_id:
            payload["store_id"] = store_id
        r2 = httpx.post(f"{base_url}/api/products", headers=headers, json=payload, timeout=10)
        if r2.status_code in (200, 201):
            created.append(r2.json())
    print(f"  Created {len(created)} catalog products for seeding")
    return created


def existing_seo_slugs(base_url: str, headers: dict[str, str]) -> set[str]:
    r = httpx.get(f"{base_url}/api/seo", headers=headers, params={"page_size": 100}, timeout=10)
    if r.status_code != 200:
        return set()
    return {item.get("slug") for item in r.json().get("items", []) if item.get("slug")}


def seed_seo(
    base_url: str,
    headers: dict[str, str],
    store: dict[str, Any] | None,
    products: list[dict[str, Any]],
) -> None:
    existing = existing_seo_slugs(base_url, headers)
    print("\n📄 Seeding SEO data linked to real store & products…")

    entries_to_seed: list[dict[str, Any]] = []

    # 1. Store SEO entry (linked to actual store)
    if store and store.get("id"):
        s_id = store["id"]
        s_name = store.get("name") or "Boutique Officielle"
        s_slug = store.get("slug") or s_name.lower().replace(" ", "-")
        entries_to_seed.append({
            "entity_type": "store",
            "entity_id": s_id,
            "title": f"{s_name} — Vente en Ligne | Boutique Officielle Tunisie",
            "description": f"Découvrez les collections chez {s_name}. Haute qualité artisanale, livraison express et paiement à la livraison en Tunisie.",
            "keywords": [s_name.lower(), "boutique tunisie", "achat en ligne", "livraison tunisie", "commerce tunisie"],
            "slug": f"{s_slug}-boutique",
            "canonical_url": f"https://socialselling.tn/share/store/{s_slug}",
            "is_indexable": True,
            "score": {"overall_score": 90, "keyword_score": 93, "meta_score": 87, "structure_score": 90},
        })

    # 2. Product SEO entries (strictly 1:1 mapping with real distinct catalog products)
    for p in products[:4]:
        p_id = p.get("id")
        p_name = p.get("name") or "Produit"
        p_price = p.get("price") or 50.0
        p_slug = p_name.lower().replace(" ", "-").replace("—", "-")
        p_slug = "".join(c for c in p_slug if c.isalnum() or c == "-").strip("-")
        entries_to_seed.append({
            "entity_type": "product",
            "entity_id": p_id,
            "title": f"{p_name[:40]} — Prix {int(p_price)} TND Tunisie",
            "description": f"Commandez {p_name} au meilleur prix en Tunisie. Livraison express à domicile et paiement à la livraison sécurisé.",
            "keywords": [p_name.lower(), "tunisie", "artisanat tunisie", f"{int(p_price)} tnd", "achat en ligne"],
            "slug": f"{p_slug}-tunisie",
            "canonical_url": f"https://socialselling.tn/share/product/{p_slug}",
            "is_indexable": True,
            "score": {"overall_score": 88, "keyword_score": 91, "meta_score": 84, "structure_score": 88},
        })

    # 3. Category / Showcase entry
    cat_id = products[0].get("category_id") if products and products[0].get("category_id") else str(uuid.uuid4())
    entries_to_seed.append({
        "entity_type": "category",
        "entity_id": str(cat_id),
        "title": "Catalogue & Sélections Tendance | Vente en Tunisie",
        "description": "Explorez toutes nos nouveautés et promotions exclusives du moment en Tunisie. Stock garanti et service client réactif.",
        "keywords": ["catalogue", "promotions tunisie", "nouveautes", "achat express"],
        "slug": "catalogue-selections-tendance",
        "canonical_url": "https://socialselling.tn/share/category/catalogue",
        "is_indexable": True,
        "score": {"overall_score": 72, "keyword_score": 75, "meta_score": 68, "structure_score": 74},
    })

    for entry in entries_to_seed:
        slug = entry["slug"]
        if slug in existing:
            print(f"  skip  {slug} (already exists)")
            continue

        score_payload = entry.pop("score")
        payload = dict(entry)

        r = httpx.post(f"{base_url}/api/seo", headers=headers, json=payload, timeout=10)
        if r.status_code not in (200, 201):
            print(f"  ✗ SEO create failed for {slug}: {r.status_code} {r.text[:120]}")
            continue

        seo_id = r.json()["id"]
        print(f"  ✓ Created SEO entry: [{payload['entity_type']}] {slug} ({seo_id[:8]}…)")

        # Attach rubric score
        rs = httpx.post(
            f"{base_url}/api/seo/{seo_id}/scores",
            headers=headers,
            json=score_payload,
            timeout=10,
        )
        if rs.status_code in (200, 201):
            print(f"      ✓ Score attached: overall={score_payload['overall_score']}")
        else:
            print(f"      ✗ Score failed: {rs.status_code} {rs.text[:80]}")


def seed_trust(base_url: str, headers: dict[str, str]) -> None:
    print("\n🛡  Seeding Seller Trust records…")
    r = httpx.get(f"{base_url}/api/seller-trust", headers=headers, params={"page_size": 5}, timeout=10)
    if r.status_code == 200 and r.json().get("total", 0) > 0:
        print("  skip  trust records (already exist)")
        return

    for rec in TRUST_RECORDS:
        r2 = httpx.post(f"{base_url}/api/seller-trust", headers=headers, json=rec, timeout=10)
        if r2.status_code in (200, 201):
            print(f"  ✓ Trust record: level={rec['level']} score={rec['score']}")
        else:
            print(f"  ✗ Trust failed: {r2.status_code} {r2.text[:120]}")


def seed_product_scores(base_url: str, headers: dict[str, str], product_id: str, store_id: str | None) -> None:
    if not store_id:
        print("\n⚠  No store found — skipping product scores (store_id required)")
        return

    print(f"\n📊 Seeding Product Scores for product {product_id[:8]}…")
    r = httpx.get(f"{base_url}/api/products/{product_id}/scores", headers=headers, params={"page_size": 5}, timeout=10)
    if r.status_code == 200 and r.json().get("total", 0) > 0:
        print("  skip  product scores (already exist)")
        return

    score_fixtures = [
        {"score_type": "ai", "score": 91, "detail": {"reasoning": "Excellent title, rich description, optimised keywords."}},
        {"score_type": "quality", "score": 85, "detail": {"image_count": 6, "has_video": True, "description_length": 320}},
        {"score_type": "relevance", "score": 78, "detail": {"category_match": 0.92, "keyword_density": 0.04}},
    ]

    for s in score_fixtures:
        payload = {**s, "store_id": store_id}
        r2 = httpx.post(f"{base_url}/api/products/{product_id}/scores", headers=headers, json=payload, timeout=10)
        if r2.status_code in (200, 201):
            print(f"  ✓ Score [{s['score_type']}]: {s['score']}/100")
        else:
            print(f"  ✗ Failed [{s['score_type']}]: {r2.status_code} {r2.text[:80]}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed demo SEO & Growth data linked to real catalog items")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--email", default="demo@test.com", help="User email")
    parser.add_argument("--password", default="pass123", help="User password")
    parser.add_argument("--clean", action="store_true", help="Clean up existing SEO entries before seeding")
    args = parser.parse_args()

    try:
        token = login(args.base_url, args.email, args.password)
    except Exception as exc:
        print(f"✗ Login failed: {exc}", file=sys.stderr)
        sys.exit(1)

    headers = {"Authorization": f"Bearer {token}"}

    if args.clean:
        clean_existing_seo(args.base_url, headers)

    store = get_or_create_store(args.base_url, headers)
    store_id = store["id"] if store else None

    products = get_or_create_products(args.base_url, headers, store_id)
    first_product_id = products[0]["id"] if products else str(uuid.uuid4())

    seed_seo(args.base_url, headers, store, products)
    seed_trust(args.base_url, headers)
    if store_id and products:
        seed_product_scores(args.base_url, headers, first_product_id, store_id)

    print("\n✅ Demo SEO data seeded successfully!")
    print("   → All entities are linked directly to your real store and catalog products.")
    print("   → Open http://localhost:5173/seo to test '✨ Auto-Optimize'")


if __name__ == "__main__":
    main()
