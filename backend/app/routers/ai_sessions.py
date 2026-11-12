import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.ai import (
    AIMessageCreate,
    AIMessageResponse,
    AISessionCreate,
    AISessionResponse,
    AISessionUpdate,
    AIToolCallCreate,
    AIToolCallResponse,
)
from app.services import platform_service

router = APIRouter(prefix="/api/ai/sessions", tags=["ai sessions"])


def _page_result(result, schema):
    return {
        "items": [schema.model_validate(item).model_dump() for item in result.items],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "total_pages": result.total_pages,
    }


@router.get("")
async def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await platform_service.list_ai_sessions(db, current_user.id, page, page_size, status)
    return _page_result(result, AISessionResponse)


@router.get("/{session_id}", response_model=AISessionResponse)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await platform_service.get_ai_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("", response_model=AISessionResponse, status_code=201)
async def create_session(
    data: AISessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await platform_service.create_ai_session(db, current_user.id, data)


@router.put("/{session_id}", response_model=AISessionResponse)
async def update_session(
    session_id: uuid.UUID,
    data: AISessionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await platform_service.get_ai_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return await platform_service.update_ai_session(db, session, data)


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await platform_service.get_ai_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await platform_service.delete_ai_session(db, session)


@router.get("/{session_id}/messages")
async def list_messages(
    session_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await platform_service.get_ai_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    result = await platform_service.list_ai_messages(db, session_id, page, page_size)
    return _page_result(result, AIMessageResponse)


@router.post("/{session_id}/messages", response_model=AIMessageResponse, status_code=201)
async def create_message(
    session_id: uuid.UUID,
    data: AIMessageCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await platform_service.get_ai_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return await platform_service.create_ai_message(db, session_id, data)


@router.get("/{session_id}/tool-calls")
async def list_tool_calls(
    session_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await platform_service.get_ai_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    result = await platform_service.list_ai_tool_calls(db, session_id, page, page_size)
    return _page_result(result, AIToolCallResponse)


@router.post("/{session_id}/tool-calls", response_model=AIToolCallResponse, status_code=201)
async def create_tool_call(
    session_id: uuid.UUID,
    data: AIToolCallCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = await platform_service.get_ai_session(db, session_id, current_user.id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    message_id = None
    result = await platform_service.list_ai_messages(db, session_id, 1, 1)
    if result.items:
        message_id = result.items[0].id
    if not message_id:
        raise HTTPException(status_code=422, detail="Session has no messages yet")
    return await platform_service.create_ai_tool_call(db, session_id, message_id, data)
