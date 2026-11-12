import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.widget import PublicChatRequest, PublicChatResponse
from app.services import ai_service, chat_service, widget_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/public", tags=["public"])


@router.post("/chat", response_model=PublicChatResponse)
async def public_chat(
    body: PublicChatRequest,
    db: AsyncSession = Depends(get_db),
):
    logger.info("Public chat request: widget_id=%s message=%s", body.widget_id, body.message[:50])
    ws = await widget_service.get_widget_settings_by_id(db, body.widget_id)
    if not ws or not ws.enabled:
        logger.warning("Widget not found or disabled: %s", body.widget_id)
        raise HTTPException(status_code=404, detail="Widget not found or disabled")

    conv = await chat_service.create_conversation(
        db,
        user_id=ws.user_id,
        customer_name=body.customer_name,
        customer_phone=body.customer_phone,
        language="fr",
    )
    logger.info("Created conversation: %s", conv.id)

    await chat_service.save_message(
        db, conv.id, "user", body.message, "fr"
    )

    try:
        ai_result = await ai_service.get_ai_response(
            db, ws.user_id, conv.id, body.message, "fr"
        )
    except Exception as e:
        logger.exception("AI service error: %s", e)
        raise HTTPException(status_code=500, detail="AI service error") from e

    await chat_service.save_message(
        db, conv.id, "assistant", ai_result["reply"], ai_result["language"],
        extra_data={"suggested_products": ai_result["suggested_products"]} if ai_result.get("suggested_products") else None,
    )

    return PublicChatResponse(
        reply=ai_result["reply"],
        conversation_id=conv.id,
        order=ai_result.get("order"),
        suggested_products=ai_result.get("suggested_products"),
    )


@router.post("/chat/{conversation_id}", response_model=PublicChatResponse)
async def public_chat_continue(
    conversation_id: uuid.UUID,
    body: PublicChatRequest,
    db: AsyncSession = Depends(get_db),
):
    logger.info("Public chat continue: conv=%s message=%s", conversation_id, body.message[:50])
    ws = await widget_service.get_widget_settings_by_id(db, body.widget_id)
    if not ws or not ws.enabled:
        raise HTTPException(status_code=404, detail="Widget not found or disabled")

    conv = await chat_service.get_conversation(db, conversation_id, ws.user_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await chat_service.save_message(
        db, conv.id, "user", body.message, "fr"
    )

    try:
        ai_result = await ai_service.get_ai_response(
            db, ws.user_id, conv.id, body.message, "fr"
        )
    except Exception as e:
        logger.exception("AI service error: %s", e)
        raise HTTPException(status_code=500, detail="AI service error") from e

    await chat_service.save_message(
        db, conv.id, "assistant", ai_result["reply"], ai_result["language"],
        extra_data={"suggested_products": ai_result["suggested_products"]} if ai_result.get("suggested_products") else None,
    )

    return PublicChatResponse(
        reply=ai_result["reply"],
        conversation_id=conv.id,
        order=ai_result.get("order"),
        suggested_products=ai_result.get("suggested_products"),
    )
