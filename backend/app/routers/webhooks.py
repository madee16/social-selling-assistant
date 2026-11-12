import asyncio
import hashlib
import hmac
import json
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.widget_settings import WidgetSettings
from app.services import webhook_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])

_background_tasks: set[asyncio.Task] = set()


def _fire_and_forget(coro) -> None:
    task = asyncio.ensure_future(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)


async def _read_and_verify_meta_signature(request: Request) -> dict:
    """Read the raw body and verify Meta's X-Hub-Signature-256 HMAC.

    Verifies against whatsapp_app_secret if configured. When no app secret is
    set, the payload is logged as ignored for development only and forwarded;
    a missing signature with a configured secret is rejected outright.
    """
    raw = await request.body()
    header = request.headers.get("X-Hub-Signature-256", "")

    if not settings.whatsapp_app_secret:
        logger.warning(
            "whatsapp_app_secret not configured; webhook signature verification DISABLED"
        )
    else:
        prefix, _, provided = header.partition("=")
        expected = hmac.new(
            settings.whatsapp_app_secret.encode(), raw, hashlib.sha256
        ).hexdigest()
        if prefix != "sha256" or not hmac.compare_digest(provided, expected):
            logger.warning("Webhook signature verification failed")
            raise HTTPException(status_code=400, detail="Invalid signature")

    body = json.loads(raw)
    logger.info("WhatsApp webhook received")
    return body


async def _get_widget_settings_by_user_id(
    db: AsyncSession, user_id: uuid.UUID
) -> WidgetSettings | None:
    result = await db.execute(
        select(WidgetSettings).where(WidgetSettings.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def _resolve_whatsapp_owner(
    db: AsyncSession, body: dict
) -> tuple[uuid.UUID | None, WidgetSettings | None]:
    """Resolve the tenant user for a WhatsApp webhook with no user_id parameter.

    Meta callbacks do not reliably include query parameters, so we match the
    webhook's recipient phone number id (value.metadata.phone_number_id) against
    the per-tenant widget_settings. Falls back to the environment-level phone id.
    """
    try:
        phone_number_id = body["entry"][0]["changes"][0]["value"]["metadata"].get(
            "phone_number_id"
        )
    except (KeyError, IndexError, TypeError):
        phone_number_id = None

    if phone_number_id:
        result = await db.execute(
            select(WidgetSettings).where(
                WidgetSettings.whatsapp_phone_number_id == phone_number_id
            )
        )
        ws = result.scalar_one_or_none()
        if ws:
            logger.info("WhatsApp owner resolved from metadata phone id %s", str(ws.user_id)[:8])
            return ws.user_id, ws

    if phone_number_id and settings.whatsapp_phone_number_id == phone_number_id:
        result = await db.execute(
            select(WidgetSettings)
            .where(WidgetSettings.whatsapp_access_token.isnot(None))
            .order_by(WidgetSettings.created_at.asc())
            .limit(1)
        )
        ws = result.scalar_one_or_none()
        if ws:
            logger.info("WhatsApp owner resolved from env phone id %s", str(ws.user_id)[:8])
            return ws.user_id, ws

    logger.warning("WhatsApp owner not resolvable (phone_number_id=%s)", phone_number_id)
    return None, None


async def _resolve_messenger_owner(
    db: AsyncSession, body: dict
) -> tuple[uuid.UUID | None, WidgetSettings | None]:
    """Resolve the tenant user for a Messenger webhook with no user_id parameter.

    Meta callbacks provide the page id either in entry[0].id or in messaging[0].recipient.id.
    """
    page_id = None
    try:
        page_id = body.get("entry", [{}])[0].get("id")
    except (KeyError, IndexError, TypeError):
        pass

    if not page_id:
        try:
            page_id = (
                body.get("entry", [{}])[0]
                .get("messaging", [{}])[0]
                .get("recipient", {})
                .get("id")
            )
        except (KeyError, IndexError, TypeError):
            pass

    if page_id:
        result = await db.execute(
            select(WidgetSettings).where(
                WidgetSettings.messenger_page_id == str(page_id)
            )
        )
        ws = result.scalar_one_or_none()
        if ws:
            logger.info("Messenger owner resolved from page id %s", str(ws.user_id)[:8])
            return ws.user_id, ws

    result = await db.execute(
        select(WidgetSettings)
        .where(WidgetSettings.messenger_access_token.isnot(None))
        .order_by(WidgetSettings.created_at.asc())
        .limit(1)
    )
    ws = result.scalar_one_or_none()
    if ws:
        logger.info("Messenger owner resolved from single active config %s", str(ws.user_id)[:8])
        return ws.user_id, ws

    logger.warning("Messenger owner not resolvable (page_id=%s)", page_id)
    return None, None


@router.get("/whatsapp")
async def verify_whatsapp_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    user_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """WhatsApp Business API webhook verification."""
    if not settings.whatsapp_enabled:
        logger.warning(
            "WhatsApp webhook verification rejected: integration disabled in this environment"
        )
        raise HTTPException(
            status_code=403, detail="WhatsApp integration is disabled in this environment"
        )

    if not hub_mode or not hub_verify_token or not hub_challenge:
        raise HTTPException(status_code=400, detail="Missing verification params")

    if user_id:
        ws = await _get_widget_settings_by_user_id(db, user_id)
        expected_token = (
            ws.webhook_verify_token
            if ws and ws.webhook_verify_token
            else settings.whatsapp_verify_token
        )
    else:
        expected_token = settings.whatsapp_verify_token

    if hub_mode == "subscribe" and hub_verify_token == expected_token:
        logger.info("WhatsApp webhook verification succeeded")
        return hub_challenge
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/whatsapp")
async def receive_whatsapp_webhook(
    request: Request,
    user_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Receive WhatsApp Business API messages and reply via AI."""
    if not settings.whatsapp_enabled:
        logger.warning(
            "WhatsApp webhook POST ignored: integration disabled in this environment"
        )
        return {"status": "ignored", "reason": "whatsapp_integration_disabled"}

    body = await _read_and_verify_meta_signature(request)

    if user_id:
        ws = await _get_widget_settings_by_user_id(db, user_id)
        if not ws:
            logger.warning("Widget settings not found for user %s", user_id)
            return {"status": "ignored"}
    else:
        user_id, ws = await _resolve_whatsapp_owner(db, body)
        if not user_id or not ws:
            logger.warning("WhatsApp webhook dropped: no owner resolvable")
            return {"status": "ignored"}

    _fire_and_forget(webhook_service.process_whatsapp_payload_async(body, user_id))
    return {"status": "ok"}


@router.get("/messenger")
async def verify_messenger_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    user_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Facebook Messenger webhook verification."""
    if not hub_mode or not hub_verify_token or not hub_challenge:
        raise HTTPException(status_code=400, detail="Missing verification params")

    if user_id:
        ws = await _get_widget_settings_by_user_id(db, user_id)
        expected_token = (
            ws.webhook_verify_token
            if ws and ws.webhook_verify_token
            else settings.messenger_verify_token
        )
    else:
        expected_token = settings.messenger_verify_token

    if hub_mode == "subscribe" and hub_verify_token == expected_token:
        try:
            return int(hub_challenge)
        except (ValueError, TypeError):
            return hub_challenge
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/messenger")
async def receive_messenger_webhook(
    request: Request,
    user_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Receive Facebook Messenger messages and reply via AI."""
    body = await _read_and_verify_meta_signature(request)

    if user_id:
        ws = await _get_widget_settings_by_user_id(db, user_id)
        if not ws:
            logger.warning("Widget settings not found for user %s", user_id)
            return {"status": "ignored"}
    else:
        user_id, ws = await _resolve_messenger_owner(db, body)
        if not user_id or not ws:
            logger.warning("Messenger webhook dropped: no owner resolvable")
            return {"status": "ignored"}

    await webhook_service.process_messenger_payload(db, body, ws)
    return {"status": "ok"}

