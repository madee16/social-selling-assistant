import logging
import uuid

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import async_session
from app.models.message import Message
from app.models.widget_settings import WidgetSettings
from app.services import ai_service, chat_service

logger = logging.getLogger(__name__)

WHATSAPP_API_BASE = settings.whatsapp_graph_api_base
MESSENGER_API_BASE = "https://graph.facebook.com/v21.0"


def log_whatsapp_configuration() -> None:
    """Log the WhatsApp integration state once at startup for clear visibility."""
    env_label = settings.whatsapp_env or settings.app_env or "unknown"
    if settings.whatsapp_enabled:
        credential_sources = []
        if settings.whatsapp_phone_number_id:
            credential_sources.append("phone_number_id from environment")
        if settings.whatsapp_access_token:
            credential_sources.append("access_token from environment")
        if not credential_sources:
            credential_sources.append(
                "no environment credentials set (per-tenant widget_settings only)"
            )
        logger.info(
            "WhatsApp/Meta integration: ENABLED (env=%s) - %s",
            env_label,
            ", ".join(credential_sources),
        )
    else:
        logger.warning(
            "WhatsApp/Meta integration: DISABLED (env=%s) - inbound webhooks are "
            "ignored and outbound sends are blocked. Set WHATSAPP_ENABLED=true "
            "only in the development/staging environment.",
            env_label,
        )


def is_whatsapp_enabled() -> bool:
    return settings.whatsapp_enabled


def resolve_whatsapp_credentials(
    ws: WidgetSettings | None,
) -> tuple[str | None, str | None]:
    """Resolve phone number id / access token: environment first, DB per-tenant fallback."""
    phone_number_id = settings.whatsapp_phone_number_id
    access_token = settings.whatsapp_access_token
    if ws:
        phone_number_id = phone_number_id or ws.whatsapp_phone_number_id
        access_token = access_token or ws.whatsapp_access_token
    return phone_number_id, access_token


async def process_whatsapp_payload_async(body: dict, user_id: uuid.UUID) -> None:
    """Process WhatsApp webhook asynchronously (background task)."""
    if not is_whatsapp_enabled():
        logger.warning("WhatsApp inbound processing skipped: integration disabled")
        return
    try:
        async with async_session() as db:
            result = await db.execute(
                select(WidgetSettings).where(WidgetSettings.user_id == user_id)
            )
            ws = result.scalar_one_or_none()
            if not ws:
                logger.warning("Async WhatsApp: settings not found for %s", user_id)
                return
            await process_whatsapp_payload(db, body, ws)
    except Exception:
        logger.exception("Async WhatsApp processing failed")


async def process_whatsapp_payload(
    db: AsyncSession, body: dict, ws: WidgetSettings
) -> None:
    if not is_whatsapp_enabled():
        logger.warning("WhatsApp payload skipped: integration disabled")
        return
    phone_number_id, access_token = resolve_whatsapp_credentials(ws)
    entry = body.get("entry", [])
    for ent in entry:
        changes = ent.get("changes", [])
        for change in changes:
            value = change.get("value", {})
            messages = value.get("messages", [])
            for msg in messages:
                if msg.get("type") != "text":
                    continue
                sender_phone = msg.get("from")
                text = msg.get("text", {}).get("body", "")
                wamid = msg.get("id")
                if not sender_phone or not text:
                    continue
                profile_name = (
                    value.get("contacts") or [{}]
                )[0].get("profile", {}).get("name", "")
                logger.info(
                    "WhatsApp inbound: from=%s to=%s bytes=%s wamid=%s",
                    sender_phone,
                    (value.get("metadata") or {}).get("phone_number_id"),
                    len(text.encode("utf-8")),
                    wamid,
                )

                conv = await chat_service.get_or_create_conversation(
                    db,
                    ws.user_id,
                    "whatsapp",
                    sender_phone,
                    customer_name=profile_name or sender_phone,
                    customer_phone=sender_phone,
                    language="fr",
                )
                conv_id = conv.id

                if wamid:
                    dup_result = await db.execute(
                        select(Message.id).where(
                            Message.conversation_id == conv_id,
                            Message.role == "user",
                            Message.extra_data["wamid"].astext == wamid,
                        )
                    )
                    if dup_result.scalar_one_or_none():
                        logger.info("Duplicate WhatsApp message ignored: %s", wamid)
                        continue

                await chat_service.save_message(
                    db,
                    conv_id,
                    "user",
                    text,
                    "fr",
                    extra_data={"wamid": wamid} if wamid else None,
                )

                try:
                    ai_result = await ai_service.get_ai_response(
                        db, ws.user_id, conv_id, text, "fr"
                    )
                except Exception as e:  # noqa: BLE001 - AI provider failures must not crash webhook
                    logger.error("AI error in whatsapp webhook: %s", e)
                    continue

                await chat_service.save_message(
                    db,
                    conv_id,
                    "assistant",
                    ai_result["reply"],
                    ai_result["language"],
                )

                await send_whatsapp_message(
                    to=sender_phone,
                    text=ai_result["reply"],
                    phone_number_id=phone_number_id,
                    access_token=access_token,
                )

                for product in ai_result.get("suggested_products", []):
                    image_url = product.get("image_url")
                    if not image_url:
                        continue
                    await send_whatsapp_image(
                        to=sender_phone,
                        image_url=image_url,
                        phone_number_id=phone_number_id,
                        access_token=access_token,
                    )


async def process_messenger_payload_async(body: dict, user_id: uuid.UUID) -> None:
    """Process Messenger webhook asynchronously (background task)."""
    try:
        async with async_session() as db:
            result = await db.execute(
                select(WidgetSettings).where(WidgetSettings.user_id == user_id)
            )
            ws = result.scalar_one_or_none()
            if not ws:
                logger.warning("Async Messenger: settings not found for %s", user_id)
                return
            await process_messenger_payload(db, body, ws)
    except Exception:
        logger.exception("Async Messenger processing failed")


async def process_messenger_payload(
    db: AsyncSession, body: dict, ws: WidgetSettings
) -> None:
    entry = body.get("entry", [])
    for ent in entry:
        messaging_list = ent.get("messaging", [])
        for event in messaging_list:
            sender_id = event.get("sender", {}).get("id")
            message = event.get("message", {})
            text = message.get("text", "")
            mid = message.get("mid")
            if not sender_id or not text:
                continue

            logger.info(
                "Messenger inbound: from=%s bytes=%s mid=%s",
                sender_id,
                len(text.encode("utf-8")),
                mid,
            )

            conv = await chat_service.get_or_create_conversation(
                db,
                ws.user_id,
                "messenger",
                sender_id,
                customer_name=f"Messenger User {sender_id[-4:]}" if len(sender_id) >= 4 else sender_id,
                language="fr",
            )
            conv_id = conv.id

            if mid:
                dup_result = await db.execute(
                    select(Message.id).where(
                        Message.conversation_id == conv_id,
                        Message.role == "user",
                        Message.extra_data["mid"].astext == mid,
                    )
                )
                if dup_result.scalar_one_or_none():
                    logger.info("Duplicate Messenger message ignored: %s", mid)
                    continue

            await chat_service.save_message(
                db,
                conv_id,
                "user",
                text,
                "fr",
                extra_data={"mid": mid} if mid else None,
            )

            try:
                ai_result = await ai_service.get_ai_response(
                    db, ws.user_id, conv_id, text, "fr"
                )
            except Exception as e:  # noqa: BLE001 - AI provider failures must not crash messenger webhook
                logger.error("AI error in messenger webhook: %s", e)
                continue

            await chat_service.save_message(
                db,
                conv_id,
                "assistant",
                ai_result["reply"],
                ai_result["language"],
            )

            await send_messenger_message(
                recipient_id=sender_id,
                text=ai_result["reply"],
                access_token=ws.messenger_access_token,
            )

            for product in ai_result.get("suggested_products", []):
                image_url = product.get("image_url")
                if not image_url:
                    continue
                await send_messenger_image(
                    recipient_id=sender_id,
                    image_url=image_url,
                    access_token=ws.messenger_access_token,
                )


async def send_whatsapp_message(
    to: str, text: str, phone_number_id: str | None, access_token: str | None
) -> bool:
    if not is_whatsapp_enabled():
        logger.warning("WhatsApp send blocked: integration disabled")
        return False
    phone_number_id = phone_number_id or settings.whatsapp_phone_number_id
    access_token = access_token or settings.whatsapp_access_token
    if not phone_number_id or not access_token:
        logger.warning("WhatsApp credentials not configured")
        return False
    if not text or not text.strip():
        logger.warning("WhatsApp send skipped: empty reply text for %s", to)
        return False
    url = f"{WHATSAPP_API_BASE}/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            logger.info("WhatsApp message sent to %s: %s", to, resp.status_code)
            return True
    except httpx.HTTPError as e:
        logger.error("Failed to send WhatsApp message: %s", e)
        return False


async def send_whatsapp_image(
    to: str, image_url: str, phone_number_id: str | None, access_token: str | None
) -> bool:
    if not is_whatsapp_enabled():
        logger.warning("WhatsApp image send blocked: integration disabled")
        return False
    phone_number_id = phone_number_id or settings.whatsapp_phone_number_id
    access_token = access_token or settings.whatsapp_access_token
    if not phone_number_id or not access_token or not image_url:
        logger.warning("WhatsApp image credentials/url missing")
        return False
    url = f"{WHATSAPP_API_BASE}/{phone_number_id}/messages"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "image",
        "image": {"link": image_url},
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            logger.info("WhatsApp image sent to %s: %s", to, resp.status_code)
            return True
    except httpx.HTTPError as e:
        logger.error("Failed to send WhatsApp image: %s", e)
        return False


async def send_messenger_message(
    recipient_id: str, text: str, access_token: str | None
) -> bool:
    if not access_token:
        logger.info(
            "[MOCK/DEV] Messenger send skipped (credentials not configured): recipient=%s, text=%s",
            recipient_id,
            text[:60] if text else "",
        )
        return False
    if not text or not text.strip():
        logger.warning("Messenger send skipped: empty reply text for %s", recipient_id)
        return False
    url = f"{MESSENGER_API_BASE}/me/messages"
    params = {"access_token": access_token}
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text},
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, params=params, json=payload)
            resp.raise_for_status()
            logger.info(
                "Messenger message sent to %s: %s", recipient_id, resp.status_code
            )
            return True
    except httpx.HTTPError as e:
        logger.error("Failed to send Messenger message: %s", e)
        return False


async def send_messenger_image(
    recipient_id: str, image_url: str, access_token: str | None
) -> bool:
    if not access_token:
        logger.info(
            "[MOCK/DEV] Messenger image send skipped (credentials not configured): recipient=%s, url=%s",
            recipient_id,
            image_url,
        )
        return False
    if not image_url:
        return False
    url = f"{MESSENGER_API_BASE}/me/messages"
    params = {"access_token": access_token}
    payload = {
        "recipient": {"id": recipient_id},
        "message": {
            "attachment": {
                "type": "image",
                "payload": {"url": image_url, "is_reusable": True},
            }
        },
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, params=params, json=payload)
            resp.raise_for_status()
            logger.info("Messenger image sent to %s: %s", recipient_id, resp.status_code)
            return True
    except httpx.HTTPError as e:
        logger.error("Failed to send Messenger image: %s", e)
        return False

