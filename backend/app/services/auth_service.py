import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.schemas.auth import RegisterRequest
from app.utils.security import (
    create_access_token,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)


class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.message = message
        self.status_code = status_code


async def register(db: AsyncSession, req: RegisterRequest) -> dict:
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalar_one_or_none():
        raise AuthError("Email already registered", 409)

    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        company_name=req.company_name,
        phone=req.phone,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


async def login(db: AsyncSession, email: str, password: str) -> dict:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.password_hash):
        raise AuthError("Invalid email or password", 401)

    token = create_access_token({"sub": str(user.id)})
    return {"access_token": token, "token_type": "bearer"}


async def request_password_reset(db: AsyncSession, email: str) -> dict:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        return {"detail": "If this email exists, a reset link has been sent"}

    token_str = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(hours=1)

    reset_token = PasswordResetToken(
        user_id=user.id,
        token=token_str,
        expires_at=expires_at,
    )
    db.add(reset_token)
    await db.commit()

    logger.debug("Password reset token for %s: %s", email, token_str)
    return {
        "detail": "If this email exists, a reset link has been sent",
        "reset_token": token_str,
    }


async def reset_password(db: AsyncSession, token_str: str, new_password: str) -> dict:
    result = await db.execute(
        select(PasswordResetToken).where(
            PasswordResetToken.token == token_str,
            not PasswordResetToken.used,
        )
    )
    reset_token = result.scalar_one_or_none()
    if not reset_token:
        raise AuthError("Invalid or expired reset token", 400)

    if reset_token.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        reset_token.used = True
        await db.commit()
        raise AuthError("Reset token has expired", 400)

    user_result = await db.execute(select(User).where(User.id == reset_token.user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise AuthError("User not found", 404)

    user.password_hash = hash_password(new_password)
    reset_token.used = True
    await db.commit()

    return {"detail": "Password reset successfully"}


async def get_current_user(db: AsyncSession, user_id: str) -> User:
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise AuthError("User not found", 404)
    return user
