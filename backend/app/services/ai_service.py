import json
import logging
import re
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.product import Product
from app.prompts.system import get_system_prompt
from app.services import n8n_service

logger = logging.getLogger(__name__)

ORDER_PATTERN = re.compile(r"\[ORDER\](.*?)\[/ORDER\]", re.DOTALL)

REASONING_PATTERNS = [
    re.compile(r"<thinking>.*?</thinking>", re.DOTALL | re.IGNORECASE),
    re.compile(r"\[thinking\].*?\[/thinking\]", re.DOTALL | re.IGNORECASE),
    re.compile(r"<reasoning>.*?</reasoning>", re.DOTALL | re.IGNORECASE),
    re.compile(r"```think.*?```", re.DOTALL | re.IGNORECASE),
]


def _strip_reasoning(reply: str) -> str:
    """Remove any chain-of-thought / analysis blocks the LLM may leak."""
    if not reply:
        return reply
    cleaned = reply
    for pattern in REASONING_PATTERNS:
        cleaned = pattern.sub("", cleaned)
    cleaned = "\n".join(
        line for line in cleaned.splitlines()
        if not line.strip().startswith(("think:", "thought:", "analysis:", "let me think", "i need to"))
    )
    return cleaned.strip()


def _build_conversation_context(messages: list[Message]) -> str:
    parts = []
    for msg in messages:
        role = "client" if msg.role == "user" else "vendeur"
        parts.append(f"{role}: {msg.content}")
    return "\n".join(parts)


def _build_product_context(products: list[Product]) -> str:
    if not products:
        return "Aucun produit disponible pour le moment."
    lines = ["Produits disponibles :"]
    for p in products:
        lines.append(f"- {p.name} (ID: {p.id}) : {p.price:.2f} TND - {p.description or 'Pas de description'} [Stock: {p.stock_quantity}]")
    return "\n".join(lines)


def _detect_language(text: str) -> str:
    arabic_chars = sum(1 for c in text if "\u0600" <= c <= "\u06FF")
    total = len(text.strip())
    if total == 0:
        return "fr"
    if arabic_chars / total > 0.3:
        return "ar"
    return "fr"


def _call_llm(prompt: str) -> str:
    if not settings.nvidia_api_key:
        logger.warning("NVIDIA_API_KEY not configured, using fallback response")
        return (
            "Merci pour votre message ! Je suis votre assistant commercial. "
            "Pour l'instant, le service IA est en cours de configuration. "
            "Un conseiller vous répondra très bientôt."
        )

    try:
        from openai import OpenAI

        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=settings.nvidia_api_key,
        )
        response = client.chat.completions.create(
            model=settings.nvidia_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2048,
        )
        content = (response.choices[0].message.content or "").strip()

        if not content:
            # Reasoning-only or empty reply: ask the model to answer directly.
            logger.warning("Empty LLM reply for %s, retrying with direct-answer instruction", settings.nvidia_model)
            response = client.chat.completions.create(
                model=settings.nvidia_model,
                messages=[
                    {"role": "user", "content": prompt},
                    {
                        "role": "user",
                        "content": "Votre dernière réponse était vide ou contenait uniquement une analyse interne. "
                        "Répondez UNIQUEMENT par le message commercial directement destiné au client, sans réflexion ni commentaire.",
                    },
                ],
                temperature=0.7,
                max_tokens=2048,
            )
            content = (response.choices[0].message.content or "").strip()

        return content or (
            "Merci pour votre message ! Pouvez-vous reformuler votre demande pour que je vous aide ?"
        )
    except Exception as e:
        err_str = str(e)
        if "quota" in err_str.lower() or "rate limit" in err_str.lower() or "429" in err_str:
            logger.warning("NVIDIA quota/rate limit: %s", e)
            return (
                "Désolé, le quota de l'assistant IA est épuisé pour le moment. "
                "Veuillez réessayer plus tard."
            )
        if "invalid" in err_str.lower() and "key" in err_str.lower():
            logger.error("Invalid NVIDIA API key: %s", e)
            return (
                "Désolé, la clé API de l'assistant IA n'est pas valide. "
                "Veuillez vérifier votre clé API NVIDIA."
            )
        logger.exception("NVIDIA API error: %s", e)
        return (
            "Désolé, une erreur technique est survenue. "
            "Veuillez réessayer dans quelques instants."
        )


async def _call_llm_with_tools(
    db: AsyncSession,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID,
    messages: list[dict[str, Any]],
    store_id: uuid.UUID | None = None,
) -> tuple[str, dict | None]:
    """Call NVIDIA NIM LLM with native tool-calling and multi-turn execution loop."""
    if not settings.nvidia_api_key:
        logger.warning("NVIDIA_API_KEY not configured, using fallback response")
        return (
            "Merci pour votre message ! Je suis votre assistant commercial. "
            "Pour l'instant, le service IA est en cours de configuration. "
            "Un conseiller vous répondra très bientôt.",
            None,
        )

    try:
        from openai import OpenAI
        from app.services.orchestrator import TOOLS_SCHEMA, Orchestrator

        client = OpenAI(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=settings.nvidia_api_key,
        )

        orchestrator = Orchestrator(db)
        created_order_data: dict[str, Any] | None = None
        current_messages = list(messages)

        # Loop up to 3 turns for iterative tool-calling
        for _ in range(3):
            response = client.chat.completions.create(
                model=settings.nvidia_model,
                messages=current_messages,
                tools=TOOLS_SCHEMA,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=2048,
            )
            choice = response.choices[0]
            response_msg = choice.message
            tool_calls = getattr(response_msg, "tool_calls", None)

            if not tool_calls:
                content = (response_msg.content or "").strip()
                if not content:
                    logger.warning("Empty LLM reply for %s, retrying with direct-answer instruction", settings.nvidia_model)
                    retry_messages = list(current_messages)
                    retry_messages.append({
                        "role": "user",
                        "content": "Votre dernière réponse était vide ou contenait uniquement une analyse interne. "
                        "Répondez UNIQUEMENT par le message commercial directement destiné au client, sans réflexion ni commentaire.",
                    })
                    retry_response = client.chat.completions.create(
                        model=settings.nvidia_model,
                        messages=retry_messages,
                        temperature=0.7,
                        max_tokens=2048,
                    )
                    content = (retry_response.choices[0].message.content or "").strip()
                return content or (
                    "Merci pour votre message ! Pouvez-vous reformuler votre demande pour que je vous aide ?"
                ), created_order_data

            # Append assistant message with tool calls
            tool_calls_dict = []
            for tc in tool_calls:
                call_dict = {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                tool_calls_dict.append(call_dict)

            current_messages.append({
                "role": "assistant",
                "content": response_msg.content or "",
                "tool_calls": tool_calls_dict,
            })

            # Execute tool calls
            for tc in tool_calls:
                t_name = tc.function.name
                t_args_str = tc.function.arguments
                try:
                    t_args = json.loads(t_args_str) if isinstance(t_args_str, str) else (t_args_str or {})
                except Exception:
                    t_args = {}

                tool_res = await orchestrator.execute_tool_call(
                    session_id=conversation_id,
                    tool_name=t_name,
                    arguments=t_args,
                    merchant_id=user_id,
                    store_id=store_id,
                )

                if t_name == "create_order" and tool_res.get("success"):
                    created_order_data = {
                        "id": tool_res.get("order_id"),
                        "total": tool_res.get("total_amount", 0.0),
                        "items": tool_res.get("items_count", 0),
                    }

                current_messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": t_name,
                    "content": json.dumps(tool_res, ensure_ascii=False),
                })

        # Final follow-up completion after multi-turn tool calling
        final_res = client.chat.completions.create(
            model=settings.nvidia_model,
            messages=current_messages,
            temperature=0.7,
            max_tokens=2048,
        )
        final_content = (final_res.choices[0].message.content or "").strip()
        return final_content, created_order_data

    except Exception as e:
        err_str = str(e)
        if "quota" in err_str.lower() or "rate limit" in err_str.lower() or "429" in err_str:
            logger.warning("NVIDIA quota/rate limit: %s", e)
            return (
                "Désolé, le quota de l'assistant IA est épuisé pour le moment. "
                "Veuillez réessayer plus tard.",
                None,
            )
        if "invalid" in err_str.lower() and "key" in err_str.lower():
            logger.error("Invalid NVIDIA API key: %s", e)
            return (
                "Désolé, la clé API de l'assistant IA n'est pas valide. "
                "Veuillez vérifier votre clé API NVIDIA.",
                None,
            )
        logger.exception("NVIDIA API error: %s", e)
        return (
            "Désolé, une erreur technique est survenue. "
            "Veuillez réessayer dans quelques instants.",
            None,
        )


def _parse_order_block(reply: str) -> tuple[str, dict | None]:
    match = ORDER_PATTERN.search(reply)
    if not match:
        return reply, None

    clean_reply = ORDER_PATTERN.sub("", reply).strip()
    try:
        order_data = json.loads(match.group(1))
        return clean_reply, order_data
    except json.JSONDecodeError:
        logger.warning("Failed to parse ORDER block: %s", match.group(1))
        return clean_reply, None


async def _create_order_from_ai(
    db: AsyncSession, user_id: uuid.UUID, conversation_id: uuid.UUID, order_data: dict,
    default_phone: str | None = None,
) -> dict | None:
    from app.models.order import Order, OrderItem

    customer_name = order_data.get("customer_name", "Client")
    customer_phone = order_data.get("customer_phone") or default_phone
    customer_address = order_data.get("customer_address")

    items_data = order_data.get("items", [])
    if not items_data:
        logger.warning("Order has no items")
        return None

    result = await db.execute(
        select(Product).where(
            Product.user_id == user_id,
            Product.is_active,
        )
    )
    all_products = result.scalars().all()

    def _find_product(pname: str) -> Product | None:
        key = (pname or "").strip().lower()
        if not key:
            return None
        for p in all_products:
            if p.name.strip().lower() == key:
                return p
        for p in all_products:
            p_name = p.name.strip().lower()
            if key in p_name or p_name in key:
                return p
        return None

    order_items = []
    total = 0.0
    for item in items_data:
        pname = item.get("product_name", "")
        qty = item.get("quantity", 1)
        product = _find_product(pname)
        if not product:
            logger.warning("Product not found: %s", pname)
            continue
        if product.stock_quantity < qty:
            logger.warning("Insufficient stock for %s", pname)
            continue
        product.stock_quantity -= qty
        line_total = float(product.price) * qty
        order_items.append({
            "product_id": product.id,
            "quantity": qty,
            "unit_price": float(product.price),
            "subtotal": line_total,
        })
        total += line_total

    if not order_items:
        return None

    order = Order(
        user_id=user_id,
        conversation_id=conversation_id,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_address=customer_address,
        status="pending",
        total_amount=total,
    )
    db.add(order)
    await db.flush()

    for oi in order_items:
        db.add(OrderItem(order_id=order.id, **oi))

    await db.commit()
    await db.refresh(order)

    from app.services.notification_service import create_notification
    await create_notification(
        db, user_id, "new_order",
        f"New order from {customer_name}",
        f"Order total: {total:.2f} TND",
        "/orders",
    )

    return {"id": str(order.id), "total": total, "items": len(order_items)}


ORDER_CONFIRMATION_PATTERNS = [
    r"valide.*commande",
    r"confirme.*commande",
    r"commande.*(?:validée|confirmée|prise en compte)",
    r"total.*TND",
    r"récap.*commande",
    r"récapitulatif.*commande",
    r"commande.*(?:bien été enregistrée|est enregistrée)",
]


def _looks_like_order_confirmation(text: str) -> bool:
    text_lower = text.lower()
    for pattern in ORDER_CONFIRMATION_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


async def _extract_order_from_conversation(
    db: AsyncSession, user_id: uuid.UUID, conversation_id: uuid.UUID, product_context: str,
    current_reply: str | None = None,
) -> dict | None:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    msgs = result.scalars().all()

    conversation_text = _build_conversation_context(msgs)
    if current_reply:
        conversation_text += f"\nvendeur: {current_reply}"
    extract_prompt = f"""Tu es un assistant qui extrait les commandes depuis une conversation commerciale.

CONTEXTE PRODUITS :
{product_context}

CONVERSATION :
{conversation_text}

Lis la conversation ci-dessus. Si le vendeur a confirmé ou validé une commande, réponds UNIQUEMENT avec un bloc [ORDER] au format JSON contenant les détails de la commande. Sinon, réponds "AUCUNE COMMANDE".

Format attendu :
[ORDER]{{"customer_name": "Nom du client", "customer_phone": "22222222", "customer_address": "Adresse", "items": [{{"product_name": "Nom exact du produit", "quantity": 1}}]}}[/ORDER]"""

    reply = _call_llm(extract_prompt)
    logger.info("Extraction fallback: LLM replied (first 200 chars): %s", reply[:200])
    match = ORDER_PATTERN.search(reply)
    if not match:
        logger.warning("Extraction fallback: no ORDER block found")
        return None

    json_str = match.group(1)
    logger.info("Extraction fallback: found JSON: %s", json_str[:300])
    try:
        order_data = json.loads(json_str)
        logger.info("Extraction fallback: parsed order for %s", order_data.get("customer_name"))
        return order_data
    except json.JSONDecodeError as e:
        logger.warning("Extraction fallback: JSON parse error: %s", e)
        return None


def _detect_mentioned_products(reply: str, products: list[Product]) -> list[dict]:
    reply_lower = reply.lower()
    mentioned = []
    for p in products:
        if p.name.lower() in reply_lower:
            mentioned.append({
                "id": str(p.id),
                "name": p.name,
                "price": float(p.price),
                "image_url": p.image_url,
            })
    return mentioned


async def get_ai_response(
    db: AsyncSession,
    user_id: uuid.UUID,
    conversation_id: uuid.UUID,
    user_message: str,
    preferred_language: str | None = "fr",
) -> dict:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    )
    messages = result.scalars().all()

    product_result = await db.execute(
        select(Product).where(Product.user_id == user_id, Product.is_active)
    )
    products = product_result.scalars().all()

    # Retrieve conversation metadata
    conv_result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = conv_result.scalar_one_or_none()
    store_id = conv.store_id if conv else None
    conv_phone = conv.customer_phone if conv else None

    conversation_history = _build_conversation_context(messages)
    product_context = _build_product_context(products)
    system_prompt = get_system_prompt()

    # Build messages list for OpenAI tool-calling API
    llm_messages: list[dict[str, Any]] = [
        {
            "role": "system",
            "content": f"{system_prompt}\n\nLangue préférée du client : {preferred_language}\n\nCONTEXTE PRODUITS :\n{product_context}",
        }
    ]
    for msg in messages:
        role = "user" if msg.role == "user" else "assistant"
        llm_messages.append({"role": role, "content": msg.content})
    llm_messages.append({"role": "user", "content": user_message})

    # Try external n8n workflow if configured
    n8n_result = await n8n_service.generate_with_n8n(
        user_message=user_message,
        conversation_history=conversation_history,
        product_context=product_context,
        preferred_language=preferred_language,
        system_prompt=system_prompt,
    )

    created_order = None
    if n8n_result:
        logger.info("Reply generated via n8n workflow (language=%s)", n8n_result["language"])
        reply = _strip_reasoning(n8n_result["reply"])
        detected_lang = n8n_result["language"]
    else:
        # Native AI LLM call with tool-calling
        raw_reply, native_order = await _call_llm_with_tools(
            db=db,
            user_id=user_id,
            conversation_id=conversation_id,
            messages=llm_messages,
            store_id=store_id,
        )
        reply = _strip_reasoning(raw_reply)
        detected_lang = _detect_language(reply)
        created_order = native_order

    # Parse [ORDER] block (backward compatibility fallback)
    clean_reply, order_data = _parse_order_block(reply)

    if not created_order and order_data:
        created_order = await _create_order_from_ai(
            db, user_id, conversation_id, order_data, default_phone=conv_phone
        )

    # Fallback: if reply confirms an order but has no ORDER block or native order, try extracting
    if not created_order and _looks_like_order_confirmation(clean_reply):
        logger.info("No ORDER block found but reply looks like order confirmation, extracting...")
        extracted_order = await _extract_order_from_conversation(
            db, user_id, conversation_id, product_context, current_reply=clean_reply
        )
        if extracted_order:
            created_order = await _create_order_from_ai(
                db, user_id, conversation_id, extracted_order, default_phone=conv_phone
            )

    detected_lang = _detect_language(clean_reply)
    if n8n_result:
        detected_lang = n8n_result["language"]

    mentioned_products = _detect_mentioned_products(clean_reply, products)

    return {
        "reply": clean_reply,
        "language": detected_lang,
        "order": created_order,
        "suggested_products": mentioned_products,
    }


# ---------------------------------------------------------------------------
# AI Auto-SEO Generation & Deterministic Scoring Rubric
# ---------------------------------------------------------------------------


def _clean_slug(text: str) -> str:
    """Produce a clean, URL-safe lowercase slug."""
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s).strip("-")
    return s or "item"


def _format_seo_title(name: str, price: float | None = None) -> str:
    """Ensure title is between 50 and 60 characters for optimal CTR and SEO rubric."""
    name_clean = name.strip()
    price_part = f" ({price:.2f} TND)" if price is not None else ""
    title = f"{name_clean}{price_part} | Livraison Tunisie"
    if 50 <= len(title) <= 60:
        return title
    if len(title) < 50:
        title = f"{name_clean}{price_part} - Achat En Ligne Tunisie"
    if len(title) < 50:
        title = f"Achetez {name_clean}{price_part} - Livraison Express Tunisie"
    if len(title) > 60:
        title = f"{name_clean}{price_part} | Achat Tunisie"
    if len(title) > 60:
        title = title[:57].rstrip() + "..."
    if len(title) < 50:
        title = (title + " - Top Qualite")[:60]
    return title


def _format_seo_description(
    name: str, price: float | None = None, category: str | None = None
) -> str:
    """Ensure description is between 120 and 155 characters with clear CTA."""
    cat_str = f" en {category}" if category else ""
    price_str = f" à seulement {price:.2f} TND" if price is not None else ""
    desc = (
        f"Achetez {name}{cat_str}{price_str} en Tunisie. "
        f"Qualité certifiée, stock garanti et livraison express 24/48h partout en Tunisie. "
        f"Commandez dès maintenant !"
    )
    if 120 <= len(desc) <= 155:
        return desc
    if len(desc) > 155:
        desc = (
            f"Achetez {name}{price_str} en Tunisie. "
            f"Qualité garantie, stock disponible et livraison rapide 24/48h à domicile. Commandez dès maintenant !"
        )
    if len(desc) > 155:
        desc = desc[:152].rstrip() + "..."
    if len(desc) < 120:
        desc = (
            f"Découvrez {name}{cat_str}{price_str} sur notre boutique en Tunisie. "
            f"Profitez du meilleur prix garanti et livraison 24/48h. "
            f"Commandez en ligne !"
        )
        if len(desc) > 155:
            desc = desc[:152].rstrip() + "..."
    return desc


def _generate_seo_keywords(name: str, category: str | None = None) -> list[str]:
    """Generate 6-10 high-intent keywords across French, Arabic, and Tunisian Darija."""
    clean_name = name.lower().strip()
    kws = [
        clean_name,
        f"{clean_name} tunisie",
        f"prix {clean_name} tnd",
        "livraison tunisie",
        "achat en ligne tunisie",
        "commander en ligne",
        "توصيل تونس",
        "سوم باهي تونس",
    ]
    if category:
        kws.append(f"{category.lower().strip()} tunisie")
    if len(kws) < 10:
        kws.append("paiement à la livraison tunisie")
    return kws[:10]


def generate_seo_metadata(entity_type: str, entity_data: dict[str, Any]) -> dict[str, Any]:
    """Generate optimized SEO metadata tailored for Tunisian/MENA social commerce.

    Uses configured LLM with fallback deterministic generation for offline/test environments.
    """
    name = str(entity_data.get("name") or "Produit").strip()
    price = entity_data.get("price")
    try:
        price_val = float(price) if price is not None else None
    except (ValueError, TypeError):
        price_val = None
    category = entity_data.get("category")
    desc = entity_data.get("description")
    stock_qty = entity_data.get("stock_quantity", 1)
    stock_status = "En stock" if (stock_qty is None or stock_qty > 0) else "Rupture de stock"

    prompt = (
        f"Tu es un expert SEO et Social Commerce spécialisé dans le marché tunisien et MENA (Facebook, Instagram, WhatsApp, TikTok).\n"
        f"Génère les métadonnées SEO et de partage social pour le {entity_type} suivant :\n"
        f"- Nom : {name}\n"
        f"- Description : {desc or 'N/A'}\n"
        f"- Prix : {price_val:.2f} TND\n" if price_val is not None else "- Prix : Non spécifié\n"
        f"- Catégorie : {category or 'Général'}\n"
        f"- Disponibilité : {stock_status}\n\n"
        f"Consignes strictes :\n"
        f"1. 'title' : Entre 50 et 60 caractères exactement. Accrocheur, avec le nom et la mention Tunisie.\n"
        f"2. 'description' : Entre 120 et 155 caractères exactement. Persuasif, mettant en avant la qualité et la livraison express avec appel à l'action.\n"
        f"3. 'keywords' : Une liste de 6 à 10 mots-clés à haute intention d'achat, mélangeant Français, Arabe tunisien / Derja ('توصيل تونس', 'سوم باهي', 'livraison tunisie', etc.).\n"
        f"4. 'slug' : Un slug URL propre, sécurisé et en minuscules sans accents.\n\n"
        f"Réponds STRICTEMENT avec un objet JSON valide :\n"
        f'{{"title": "...", "description": "...", "keywords": ["...", "..."], "slug": "..."}}'
    )

    result = None
    # If API key configured, attempt LLM call
    if settings.nvidia_api_key:
        try:
            raw = _call_llm(prompt)
            json_match = re.search(r"\{.*\}", raw, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group(0))
                if isinstance(parsed, dict) and "title" in parsed and "description" in parsed:
                    result = parsed
        except Exception as e:
            logger.warning("LLM SEO generation failed or unparseable: %s", e)

    # Fallback deterministic generator
    if not result:
        fb_title = _format_seo_title(name, price_val)
        fb_desc = _format_seo_description(name, price_val, category)
        fb_kws = _generate_seo_keywords(name, category)
        fb_slug = _clean_slug(f"{name}-{int(price_val)}tnd" if price_val else name)
        result = {
            "title": fb_title,
            "description": fb_desc,
            "keywords": fb_kws,
            "slug": fb_slug,
        }
    else:
        # Sanitize LLM result to ensure rubric compliance
        title = str(result.get("title") or "").strip()
        if len(title) < 40 or len(title) > 70:
            title = _format_seo_title(name, price_val)
        desc_text = str(result.get("description") or "").strip()
        if len(desc_text) < 100 or len(desc_text) > 170:
            desc_text = _format_seo_description(name, price_val, category)
        kws = result.get("keywords")
        if not isinstance(kws, list) or len(kws) < 4:
            kws = _generate_seo_keywords(name, category)
        slug = str(result.get("slug") or "")
        slug = _clean_slug(slug or name)
        result = {
            "title": title,
            "description": desc_text,
            "keywords": [str(k).strip() for k in kws if str(k).strip()][:10],
            "slug": slug,
        }

    return result


def compute_seo_score(
    title: str | None,
    description: str | None,
    keywords: list[str] | None,
    slug: str | None,
    canonical_url: str | None = None,
    has_image: bool = False,
    is_indexable: bool = True,
) -> dict[str, Any]:
    """Calculate granular SEO scores (0-100) using real rubric rules."""
    title_str = (title or "").strip()
    desc_str = (description or "").strip()
    kw_list = [k.strip() for k in (keywords or []) if k and k.strip()]
    slug_str = (slug or "").strip()

    # 1. Meta Score (Title 50 pts, Description 50 pts)
    t_len = len(title_str)
    if 50 <= t_len <= 60:
        title_score = 50.0
    elif 40 <= t_len <= 70:
        title_score = 35.0
    elif (20 <= t_len < 40) or (70 < t_len <= 90):
        title_score = 20.0
    elif t_len > 0:
        title_score = 10.0
    else:
        title_score = 0.0

    d_len = len(desc_str)
    if 120 <= d_len <= 155:
        desc_score = 50.0
    elif 100 <= d_len <= 170:
        desc_score = 35.0
    elif (60 <= d_len < 100) or (170 < d_len <= 200):
        desc_score = 20.0
    elif d_len > 0:
        desc_score = 10.0
    else:
        desc_score = 0.0

    meta_score = round(title_score + desc_score, 1)

    # 2. Keyword Score (Count 50 pts, Intent/Localization 50 pts)
    kw_count = len(kw_list)
    if 6 <= kw_count <= 10:
        kw_count_score = 50.0
    elif kw_count > 10:
        kw_count_score = 40.0
    elif 3 <= kw_count < 6:
        kw_count_score = 30.0
    elif kw_count > 0:
        kw_count_score = 15.0
    else:
        kw_count_score = 0.0

    # High-intent & Arabic check
    combined_kws = " ".join(kw_list).lower()
    has_arabic = bool(re.search(r"[\u0600-\u06FF]", combined_kws))
    intent_terms = ["tunisie", "livraison", "prix", "tnd", "achat", "تونس", "توصيل", "commander", "bahi", "dinar"]
    intent_matches = sum(1 for term in intent_terms if term in combined_kws)

    intent_score = 0.0
    if has_arabic:
        intent_score += 25.0
    if intent_matches >= 2:
        intent_score += 25.0
    elif intent_matches == 1:
        intent_score += 15.0

    keyword_score = round(min(100.0, kw_count_score + intent_score), 1)

    # 3. Structure Score (Slug 30 pts, Image 30 pts, Indexable 20 pts, Canonical 20 pts)
    if slug_str and re.match(r"^[a-z0-9\-]+$", slug_str):
        slug_score = 30.0
    elif slug_str:
        slug_score = 15.0
    else:
        slug_score = 0.0

    image_score = 30.0 if has_image else 0.0
    indexable_score = 20.0 if is_indexable else 0.0
    canonical_score = 20.0 if canonical_url else 0.0

    structure_score = round(slug_score + image_score + indexable_score + canonical_score, 1)

    # 4. Overall Weighted Score (Meta 40%, Keyword 35%, Structure 25%)
    overall_score = round(
        0.40 * meta_score + 0.35 * keyword_score + 0.25 * structure_score, 1
    )

    detail = {
        "title_length": t_len,
        "description_length": d_len,
        "keyword_count": kw_count,
        "has_arabic": has_arabic,
        "intent_matches": intent_matches,
        "has_slug": bool(slug_str),
        "has_image": bool(has_image),
        "is_indexable": bool(is_indexable),
        "canonical_url": canonical_url,
        "breakdown": {
            "meta_score": meta_score,
            "keyword_score": keyword_score,
            "structure_score": structure_score,
        },
    }

    return {
        "overall_score": overall_score,
        "keyword_score": keyword_score,
        "meta_score": meta_score,
        "structure_score": structure_score,
        "detail": detail,
    }

