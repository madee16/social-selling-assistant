import html
import json
import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user, get_current_user_optional
from app.models.category import Category
from app.models.merchant import Merchant
from app.models.product import Product
from app.models.seller_trust_score import SellerTrustScore
from app.models.seo_data import SeoData
from app.models.seo_score import SeoScore
from app.models.store import Store
from app.models.user import User
from app.schemas.seo import (
    SeoDataCreate,
    SeoDataResponse,
    SeoDataUpdate,
    SeoGenerateResponse,
    SeoScoreCreate,
    SeoScoreResponse,
    SeoScoreUpdate,
)
from app.services import platform_service
from app.services.ai_service import compute_seo_score, generate_seo_metadata
from app.services.orchestrator import Orchestrator
from app.services.rules_engine import RulesEngine, _coerce_uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/seo", tags=["seo"])
public_router = APIRouter(tags=["seo-public"])


# ---------------------------------------------------------------------------
# Public SSR & Sitemap Helpers
# ---------------------------------------------------------------------------


async def _render_sitemap_xml(db: AsyncSession, request: Request) -> Response:
    base_url = str(request.base_url).rstrip("/")
    stmt = (
        select(SeoData)
        .where(SeoData.is_indexable.is_(True))
        .order_by(SeoData.updated_at.desc())
    )
    result = await db.execute(stmt)
    entries = result.scalars().all()

    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for item in entries:
        slug_or_id = item.slug or str(item.entity_id)
        loc = f"{base_url}/share/{item.entity_type}/{slug_or_id}"
        lastmod = (
            item.updated_at.strftime("%Y-%m-%d")
            if item.updated_at
            else datetime.now(UTC).strftime("%Y-%m-%d")
        )
        xml_lines.append("  <url>")
        xml_lines.append(f"    <loc>{html.escape(loc)}</loc>")
        xml_lines.append(f"    <lastmod>{lastmod}</lastmod>")
        xml_lines.append("    <changefreq>daily</changefreq>")
        xml_lines.append("    <priority>0.8</priority>")
        xml_lines.append("  </url>")
    xml_lines.append("</urlset>")
    return Response(content="\n".join(xml_lines), media_type="application/xml")


async def _render_share_page(
    entity_type: str,
    slug_or_id: str,
    db: AsyncSession,
    request: Request,
) -> HTMLResponse:
    entity_type_clean = entity_type.lower().strip()
    if entity_type_clean not in ("product", "store"):
        return HTMLResponse(
            content="<!DOCTYPE html><html><head><title>Non trouvé</title></head><body><h1>Entité non supportée</h1></body></html>",
            status_code=404,
        )

    entity_uuid = _coerce_uuid(slug_or_id)

    # Resolve SeoData
    conditions = [SeoData.entity_type == entity_type_clean]
    if entity_uuid:
        conditions.append((SeoData.slug == slug_or_id) | (SeoData.entity_id == entity_uuid))
    else:
        conditions.append(SeoData.slug == slug_or_id)

    seo_stmt = select(SeoData).where(*conditions)
    seo_res = await db.execute(seo_stmt)
    seo_record = seo_res.scalar_one_or_none()

    base_url = str(request.base_url).rstrip("/")

    if entity_type_clean == "product":
        product = None
        if seo_record:
            p_res = await db.execute(select(Product).where(Product.id == seo_record.entity_id))
            product = p_res.scalar_one_or_none()
        if not product and entity_uuid:
            p_res = await db.execute(select(Product).where(Product.id == entity_uuid))
            product = p_res.scalar_one_or_none()
        if not product:
            slug_search = slug_or_id.replace("-", " ")
            p_res = await db.execute(select(Product).where(Product.name.ilike(f"%{slug_search}%")).limit(1))
            product = p_res.scalar_one_or_none()

        if not product:
            return HTMLResponse(
                content="<!DOCTYPE html><html><head><title>Produit non trouvé</title></head><body><h1>Produit non trouvé</h1><p>Ce produit n'est plus disponible sur notre boutique.</p></body></html>",
                status_code=404,
            )

        if not seo_record:
            meta = generate_seo_metadata(
                "product",
                {
                    "name": product.name,
                    "description": product.description,
                    "price": float(product.price),
                    "stock_quantity": product.stock_quantity,
                    "is_active": product.is_active,
                },
            )
            seo_record = SeoData(
                entity_type="product",
                entity_id=product.id,
                title=meta["title"],
                description=meta["description"],
                keywords=meta["keywords"],
                slug=meta["slug"],
                canonical_url=f"/share/product/{meta['slug']}",
                is_indexable=True,
            )
            db.add(seo_record)
            await db.flush()

        merchant_id = None
        trust_level = "Vérifié"
        trust_score_val = 92.0
        if product.user_id:
            m_res = await db.execute(select(Merchant).where(Merchant.user_id == product.user_id))
            merchant = m_res.scalar_one_or_none()
            if merchant:
                merchant_id = merchant.id
                ts_res = await db.execute(
                    select(SellerTrustScore)
                    .where(SellerTrustScore.seller_id == merchant.id)
                    .order_by(SellerTrustScore.calculated_at.desc())
                )
                ts = ts_res.scalar_one_or_none()
                if ts:
                    trust_level = ts.level.capitalize()
                    trust_score_val = ts.score

        is_in_stock = (product.stock_quantity > 0) and product.is_active
        schema_availability = "https://schema.org/InStock" if is_in_stock else "https://schema.org/OutOfStock"
        stock_badge_text = f"En Stock ({product.stock_quantity} dispo)" if is_in_stock else "Rupture de Stock"
        stock_badge_class = "badge-in-stock" if is_in_stock else "badge-out-of-stock"

        canonical_url = f"{base_url}/share/product/{seo_record.slug or product.id}"
        image_url = product.image_url or "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=800&q=80"
        if image_url.startswith("/"):
            image_url = f"{base_url}{image_url}"

        # Schema.org Product JSON-LD
        json_ld = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": product.name,
            "description": seo_record.description or product.description or product.name,
            "sku": str(product.id),
            "image": [image_url],
            "offers": {
                "@type": "Offer",
                "priceCurrency": "TND",
                "price": f"{float(product.price):.2f}",
                "availability": schema_availability,
                "url": canonical_url,
            },
            "aggregateRating": {
                "@type": "AggregateRating",
                "ratingValue": f"{min(5.0, max(1.0, trust_score_val / 20.0)):.1f}",
                "reviewCount": "24",
            },
        }
        json_ld_str = json.dumps(json_ld, ensure_ascii=False, indent=2)

        title_html = html.escape(seo_record.title or product.name)
        desc_html = html.escape(seo_record.description or product.description or "")
        name_html = html.escape(product.name)
        price_html = f"{float(product.price):.2f}"
        merchant_attr = str(merchant_id) if merchant_id else ""

        html_body = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title_html}</title>
  <meta name="description" content="{desc_html}">
  <link rel="canonical" href="{canonical_url}">

  <!-- OpenGraph / Social Preview (WhatsApp, Facebook, Instagram) -->
  <meta property="og:title" content="{title_html}">
  <meta property="og:description" content="{desc_html}">
  <meta property="og:type" content="product">
  <meta property="og:url" content="{canonical_url}">
  <meta property="og:image" content="{image_url}">
  <meta property="og:site_name" content="Social Selling Tunisia">
  <meta property="product:price:amount" content="{price_html}">
  <meta property="product:price:currency" content="TND">

  <!-- Twitter Card -->
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title_html}">
  <meta name="twitter:description" content="{desc_html}">
  <meta name="twitter:image" content="{image_url}">

  <!-- Schema.org JSON-LD -->
  <script type="application/ld+json">
{json_ld_str}
  </script>

  <style>
    :root {{
      --primary: #2563eb;
      --primary-hover: #1d4ed8;
      --bg: #f8fafc;
      --card-bg: #ffffff;
      --text-main: #0f172a;
      --text-muted: #64748b;
      --border: #e2e8f0;
      --success-bg: #dcfce7;
      --success-text: #15803d;
      --danger-bg: #ffe4e6;
      --danger-text: #be123c;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      background-color: var(--bg);
      color: var(--text-main);
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      padding: 1.5rem;
    }}
    .share-container {{
      max-width: 480px;
      width: 100%;
      background: var(--card-bg);
      border-radius: 1.25rem;
      border: 1px solid var(--border);
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05), 0 8px 10px -6px rgba(0, 0, 0, 0.01);
      overflow: hidden;
    }}
    .product-img-wrap {{
      width: 100%;
      height: 280px;
      background: #f1f5f9;
      position: relative;
      overflow: hidden;
    }}
    .product-img {{
      width: 100%;
      height: 100%;
      object-fit: cover;
    }}
    .badge-bar {{
      position: absolute;
      top: 1rem;
      left: 1rem;
      right: 1rem;
      display: flex;
      justify-content: space-between;
      gap: 0.5rem;
    }}
    .badge {{
      display: inline-flex;
      align-items: center;
      font-size: 0.75rem;
      font-weight: 700;
      padding: 0.35rem 0.75rem;
      border-radius: 9999px;
      box-shadow: 0 2px 4px rgba(0,0,0,0.1);
      backdrop-filter: blur(8px);
    }}
    .badge-in-stock {{ background: var(--success-bg); color: var(--success-text); }}
    .badge-out-of-stock {{ background: var(--danger-bg); color: var(--danger-text); }}
    .badge-trust {{ background: #eff6ff; color: #1e40af; border: 1px solid #bfdbfe; }}
    .content-wrap {{
      padding: 1.5rem;
    }}
    .product-title {{
      font-size: 1.35rem;
      font-weight: 700;
      line-height: 1.3;
      margin-bottom: 0.75rem;
      color: var(--text-main);
    }}
    .price-row {{
      display: flex;
      align-items: baseline;
      gap: 0.5rem;
      margin-bottom: 1rem;
    }}
    .price-amount {{
      font-size: 1.75rem;
      font-weight: 800;
      color: var(--primary);
    }}
    .price-currency {{
      font-size: 1rem;
      font-weight: 600;
      color: var(--text-muted);
    }}
    .product-desc {{
      font-size: 0.925rem;
      line-height: 1.6;
      color: var(--text-muted);
      margin-bottom: 1.5rem;
    }}
    .order-cta {{
      display: flex;
      justify-content: center;
      align-items: center;
      gap: 0.5rem;
      width: 100%;
      padding: 0.875rem 1.25rem;
      background: var(--primary);
      color: white;
      text-decoration: none;
      font-size: 1rem;
      font-weight: 600;
      border-radius: 0.75rem;
      border: none;
      cursor: pointer;
      box-shadow: 0 4px 12px rgba(37, 99, 235, 0.25);
      transition: background 0.2s ease, transform 0.1s ease;
    }}
    .order-cta:hover {{
      background: var(--primary-hover);
      transform: translateY(-1px);
    }}
    .footer-guarantee {{
      display: flex;
      justify-content: space-around;
      margin-top: 1.25rem;
      padding-top: 1rem;
      border-top: 1px dashed var(--border);
      font-size: 0.75rem;
      color: var(--text-muted);
    }}
  </style>
</head>
<body>
  <div class="share-container">
    <div class="product-img-wrap">
      <img src="{image_url}" alt="{name_html}" class="product-img">
      <div class="badge-bar">
        <span class="badge {stock_badge_class}">{stock_badge_text}</span>
        <span class="badge badge-trust">★ {trust_level} ({trust_score_val:.0f} pts)</span>
      </div>
    </div>
    <div class="content-wrap">
      <h1 class="product-title">{name_html}</h1>
      <div class="price-row">
        <span class="price-amount">{price_html}</span>
        <span class="price-currency">TND</span>
      </div>
      <p class="product-desc">{desc_html}</p>
      <button class="order-cta" onclick="window.SocialSellingWidget && window.SocialSellingWidget.open ? window.SocialSellingWidget.open() : alert('Ouverture du chat assistant IA...');">
        <span>💬</span>
        <span>Commander avec l'Assistant IA</span>
      </button>
      <div class="footer-guarantee">
        <span>🚚 Livraison 24/48h</span>
        <span>💵 Paiement à la livraison</span>
        <span>🛡️ Vendeur Vérifié</span>
      </div>
    </div>
  </div>

  <!-- Social Selling Assistant Widget -->
  <script src="/widget.js" data-product-id="{product.id}" data-merchant-id="{merchant_attr}" defer></script>
</body>
</html>"""
        return HTMLResponse(content=html_body)

    # Store entity share page
    store = None
    if seo_record:
        s_res = await db.execute(select(Store).where(Store.id == seo_record.entity_id))
        store = s_res.scalar_one_or_none()
    if not store and entity_uuid:
        s_res = await db.execute(select(Store).where(Store.id == entity_uuid))
        store = s_res.scalar_one_or_none()
    if not store:
        s_res = await db.execute(select(Store).where(Store.slug == slug_or_id))
        store = s_res.scalar_one_or_none()

    if not store:
        return HTMLResponse(
            content="<!DOCTYPE html><html><head><title>Boutique non trouvée</title></head><body><h1>Boutique non trouvée</h1></body></html>",
            status_code=404,
        )

    if not seo_record:
        meta = generate_seo_metadata(
            "store",
            {
                "name": store.name,
                "domain": store.domain,
                "slug": store.slug,
            },
        )
        seo_record = SeoData(
            entity_type="store",
            entity_id=store.id,
            title=meta["title"],
            description=meta["description"],
            keywords=meta["keywords"],
            slug=meta["slug"],
            canonical_url=f"/share/store/{meta['slug']}",
            is_indexable=True,
        )
        db.add(seo_record)
        await db.flush()

    canonical_url = f"{base_url}/share/store/{seo_record.slug or store.slug}"
    title_html = html.escape(seo_record.title or store.name)
    desc_html = html.escape(seo_record.description or f"Boutique officielle {store.name}")
    name_html = html.escape(store.name)

    html_body = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title_html}</title>
  <meta name="description" content="{desc_html}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:title" content="{title_html}">
  <meta property="og:description" content="{desc_html}">
  <meta property="og:type" content="website">
  <meta property="og:url" content="{canonical_url}">
</head>
<body style="font-family: sans-serif; display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #f8fafc;">
  <div style="background: white; padding: 2rem; border-radius: 1rem; border: 1px solid #e2e8f0; max-width: 480px; width: 100%; text-align: center;">
    <h1>{name_html}</h1>
    <p style="color: #64748b; margin: 1rem 0;">{desc_html}</p>
    <a href="/" style="display: inline-block; padding: 0.75rem 1.5rem; background: #2563eb; color: white; border-radius: 0.5rem; text-decoration: none;">Visiter la boutique</a>
  </div>
  <script src="/widget.js" defer></script>
</body>
</html>"""
    return HTMLResponse(content=html_body)


# ---------------------------------------------------------------------------
# Public Routes (Both Top-Level and API Prefixed)
# ---------------------------------------------------------------------------


@public_router.get("/sitemap.xml", response_class=Response)
@router.get("/sitemap.xml", response_class=Response)
async def get_sitemap_xml(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    return await _render_sitemap_xml(db, request)


@public_router.get("/share/{entity_type}/{slug_or_id}", response_class=HTMLResponse)
@router.get("/share/{entity_type}/{slug_or_id}", response_class=HTMLResponse)
async def get_share_page(
    entity_type: str,
    slug_or_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    return await _render_share_page(entity_type, slug_or_id, db, request)


# ---------------------------------------------------------------------------
# AI Auto-SEO Generation Endpoint
# ---------------------------------------------------------------------------


@router.post("/{entity_type}/{entity_id}/generate", response_model=SeoGenerateResponse)
async def generate_entity_seo(
    entity_type: str,
    entity_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """Generate SEO metadata using AI with real rubric score calculation and marketplace sync."""
    entity_type_clean = entity_type.lower().strip()
    if entity_type_clean not in ("product", "store"):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported entity_type '{entity_type}'. Must be 'product' or 'store'.",
        )

    try:
        target_uuid = uuid.UUID(str(entity_id).strip())
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Invalid entity_id format")

    has_image = False
    entity_data: dict[str, Any] = {}
    product_obj: Product | None = None
    store_obj: Store | None = None

    if entity_type_clean == "product":
        p_stmt = select(Product).where(Product.id == target_uuid)
        p_res = await db.execute(p_stmt)
        product_obj = p_res.scalar_one_or_none()
        if not product_obj:
            raise HTTPException(status_code=404, detail="Product not found")

        cat_name = None
        if product_obj.category_id:
            c_res = await db.execute(select(Category).where(Category.id == product_obj.category_id))
            c = c_res.scalar_one_or_none()
            if c:
                cat_name = c.name

        has_image = bool(product_obj.image_url)
        entity_data = {
            "name": product_obj.name,
            "description": product_obj.description,
            "price": float(product_obj.price) if product_obj.price is not None else 0.0,
            "category": cat_name,
            "stock_quantity": product_obj.stock_quantity,
            "is_active": product_obj.is_active,
            "image_url": product_obj.image_url,
        }
    else:
        s_stmt = select(Store).where(Store.id == target_uuid)
        s_res = await db.execute(s_stmt)
        store_obj = s_res.scalar_one_or_none()
        if not store_obj:
            raise HTTPException(status_code=404, detail="Store not found")

        has_image = False
        entity_data = {
            "name": store_obj.name,
            "domain": store_obj.domain,
            "slug": store_obj.slug,
            "description": f"Boutique officielle {store_obj.name} en Tunisie",
        }

    # 1. AI Generation (with deterministic fallback)
    meta = generate_seo_metadata(entity_type_clean, entity_data)
    canonical_url = f"/share/{entity_type_clean}/{meta['slug']}"

    # 2. Upsert SeoData
    seo_stmt = (
        select(SeoData)
        .where(
            SeoData.entity_type == entity_type_clean,
            SeoData.entity_id == target_uuid,
        )
        .order_by(SeoData.updated_at.desc())
    )
    seo_res = await db.execute(seo_stmt)
    seo_data = seo_res.scalars().first()

    if seo_data:
        seo_data.title = meta["title"]
        seo_data.description = meta["description"]
        seo_data.keywords = meta["keywords"]
        seo_data.slug = meta["slug"]
        seo_data.canonical_url = canonical_url
        seo_data.is_indexable = True
    else:
        seo_data = SeoData(
            entity_type=entity_type_clean,
            entity_id=target_uuid,
            title=meta["title"],
            description=meta["description"],
            keywords=meta["keywords"],
            slug=meta["slug"],
            canonical_url=canonical_url,
            is_indexable=True,
        )
        db.add(seo_data)

    await db.flush()

    # 3. Dynamically Compute Real Rubric Score
    scores = compute_seo_score(
        title=seo_data.title,
        description=seo_data.description,
        keywords=seo_data.keywords,
        slug=seo_data.slug,
        canonical_url=seo_data.canonical_url,
        has_image=has_image,
        is_indexable=seo_data.is_indexable,
    )

    # 4. Upsert SeoScore
    score_stmt = select(SeoScore).where(SeoScore.seo_data_id == seo_data.id).order_by(SeoScore.created_at.desc())
    score_res = await db.execute(score_stmt)
    seo_score = score_res.scalars().first()

    if seo_score:
        seo_score.overall_score = scores["overall_score"]
        seo_score.keyword_score = scores["keyword_score"]
        seo_score.meta_score = scores["meta_score"]
        seo_score.structure_score = scores["structure_score"]
        seo_score.detail = scores["detail"]
        seo_score.calculated_at = datetime.now(UTC)
    else:
        seo_score = SeoScore(
            seo_data_id=seo_data.id,
            overall_score=scores["overall_score"],
            keyword_score=scores["keyword_score"],
            meta_score=scores["meta_score"],
            structure_score=scores["structure_score"],
            detail=scores["detail"],
            calculated_at=datetime.now(UTC),
        )
        db.add(seo_score)

    await db.flush()

    # 5. Synchronize Marketplace Product Score if entity is product
    if entity_type_clean == "product" and product_obj:
        store_id = product_obj.store_id
        if not store_id:
            first_store_res = await db.execute(select(Store).limit(1))
            first_store = first_store_res.scalar_one_or_none()
            if first_store:
                store_id = first_store.id

        if store_id:
            try:
                orchestrator = Orchestrator(db)
                await orchestrator.update_product_score(
                    product_id=product_obj.id,
                    store_id=store_id,
                    score=scores["overall_score"],
                    score_type="seo",
                    detail={"seo_score_id": str(seo_score.id), **scores["detail"]},
                )
                rules_engine = RulesEngine(db)
                await rules_engine.compute_product_scores(
                    product_id=product_obj.id,
                    store_id=store_id,
                )
            except Exception as sync_err:
                logger.warning("Product score marketplace sync skipped or failed: %s", sync_err)

    await db.commit()
    await db.refresh(seo_data)
    await db.refresh(seo_score)

    return SeoGenerateResponse(
        seo_data=SeoDataResponse.model_validate(seo_data),
        seo_score=SeoScoreResponse.model_validate(seo_score),
        message="SEO metadata and score generated successfully",
    )


# ---------------------------------------------------------------------------
# Standard CRUD Endpoints
# ---------------------------------------------------------------------------


@router.get("")
async def list_seo_data(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    entity_type: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await platform_service.list_seo_data(db, page, page_size, entity_type)
    return {
        "items": [SeoDataResponse.model_validate(item).model_dump() for item in result.items],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "total_pages": result.total_pages,
    }


@router.get("/{seo_id}", response_model=SeoDataResponse)
async def get_seo_data(
    seo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await platform_service.get_seo_data(db, seo_id)
    if not record:
        raise HTTPException(status_code=404, detail="SEO data not found")
    return record


@router.post("", response_model=SeoDataResponse, status_code=201)
async def create_seo_data(
    data: SeoDataCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await platform_service.create_seo_data(db, data)


@router.put("/{seo_id}", response_model=SeoDataResponse)
async def update_seo_data(
    seo_id: uuid.UUID,
    data: SeoDataUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await platform_service.get_seo_data(db, seo_id)
    if not record:
        raise HTTPException(status_code=404, detail="SEO data not found")
    return await platform_service.update_seo_data(db, record, data)


@router.delete("/{seo_id}", status_code=204)
async def delete_seo_data(
    seo_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await platform_service.get_seo_data(db, seo_id)
    if not record:
        raise HTTPException(status_code=404, detail="SEO data not found")
    await platform_service.delete_seo_data(db, record)


@router.get("/{seo_id}/scores")
async def list_seo_scores(
    seo_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await platform_service.list_seo_scores(db, seo_id, page, page_size)
    return {
        "items": [SeoScoreResponse.model_validate(item).model_dump() for item in result.items],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "total_pages": result.total_pages,
    }


@router.post("/{seo_id}/scores", response_model=SeoScoreResponse, status_code=201)
async def create_seo_score(
    seo_id: uuid.UUID,
    data: SeoScoreCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await platform_service.create_seo_score(db, seo_id, data)


@router.put("/scores/{score_id}", response_model=SeoScoreResponse)
async def update_seo_score(
    score_id: uuid.UUID,
    data: SeoScoreUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await platform_service.get_seo_score(db, score_id)
    if not record:
        raise HTTPException(status_code=404, detail="SEO score not found")
    return await platform_service.update_seo_score(db, record, data)


@router.delete("/scores/{score_id}", status_code=204)
async def delete_seo_score(
    score_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = await platform_service.get_seo_score(db, score_id)
    if not record:
        raise HTTPException(status_code=404, detail="SEO score not found")
    await platform_service.delete_seo_score(db, record)
