import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationDetailResponse,
    ConversationResponse,
    CreatedOrderInfo,
    MessageResponse,
)
from app.services import ai_service, chat_service

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv_id = body.conversation_id

    if conv_id:
        conv = await chat_service.get_conversation(db, conv_id, current_user.id)
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        conv = await chat_service.create_conversation(
            db,
            user_id=current_user.id,
            customer_name=body.customer_name,
            customer_phone=body.customer_phone,
            customer_address=body.customer_address,
            language=body.language,
        )
        conv_id = conv.id

    await chat_service.save_message(
        db, conv_id, "user", body.message, body.language
    )

    ai_result = await ai_service.get_ai_response(
        db, current_user.id, conv_id, body.message, body.language
    )

    extra = {}
    if ai_result.get("suggested_products"):
        extra["suggested_products"] = ai_result["suggested_products"]
    await chat_service.save_message(
        db, conv_id, "assistant", ai_result["reply"], ai_result["language"], extra_data=extra or None
    )

    order_info = ai_result.get("order")
    return ChatResponse(
        conversation_id=conv_id,
        reply=ai_result["reply"],
        language=ai_result.get("language", body.language),
        order=CreatedOrderInfo(**order_info) if order_info else None,
        suggested_products=ai_result.get("suggested_products"),
    )


@router.get("/conversations")
async def list_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await chat_service.list_conversations(db, current_user.id, page, page_size)
    return {
        "items": [
            ConversationResponse.model_validate(c).model_dump()
            for c in result["items"]
        ],
        "total": result["total"],
        "page": result["page"],
        "page_size": result["page_size"],
        "total_pages": result["total_pages"],
    }


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation_detail(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv, messages = await chat_service.get_conversation_messages(
        db, conversation_id, current_user.id
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationDetailResponse(
        conversation=ConversationResponse.model_validate(conv),
        messages=[MessageResponse.model_validate(m) for m in messages],
    )


@router.patch("/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: uuid.UUID,
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    conv = await chat_service.update_conversation_info(
        db,
        conversation_id,
        current_user.id,
        customer_name=body.customer_name,
        customer_phone=body.customer_phone,
        customer_address=body.customer_address,
    )
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.patch("/conversations/{conversation_id}/close", response_model=ConversationResponse)
async def close_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    closed = await chat_service.close_conversation(db, conversation_id, current_user.id)
    if not closed:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv = await chat_service.get_conversation(db, conversation_id, current_user.id)
    return conv
