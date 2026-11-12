import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.auth import UserResponse
from app.schemas.settings import PasswordChange, PreferencesUpdate, ProfileUpdate
from app.utils.security import hash_password, verify_password

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=UserResponse)
async def get_settings(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    body: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.company_name is not None:
        current_user.company_name = body.company_name
    if body.phone is not None:
        current_user.phone = body.phone
    if body.company_logo_url is not None:
        current_user.company_logo_url = body.company_logo_url
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.put("/password")
async def change_password(
    body: PasswordChange,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.password_hash = hash_password(body.new_password)
    await db.commit()
    return {"detail": "Password updated successfully"}


@router.put("/preferences", response_model=UserResponse)
async def update_preferences(
    body: PreferencesUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if body.preferred_language is not None:
        current_user.preferred_language = body.preferred_language
    if body.currency is not None:
        current_user.currency = body.currency
    if body.notifications_enabled is not None:
        current_user.notifications_enabled = body.notifications_enabled
    if body.ai_custom_instructions is not None:
        current_user.ai_custom_instructions = body.ai_custom_instructions
    await db.commit()
    await db.refresh(current_user)
    return current_user
