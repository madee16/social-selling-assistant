import logging
import uuid

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/uploads", tags=["uploads"])

SUPABASE_STORAGE_URL = f"{settings.supabase_url}/storage/v1/object/product-images"


@router.post("/product-image")
async def upload_product_image(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ext = (file.filename or "").split(".")[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "webp", "gif"):
        raise HTTPException(status_code=400, detail="Invalid file type. Allowed: jpg, jpeg, png, webp, gif")

    if file.content_type not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
        raise HTTPException(status_code=400, detail="Invalid content type")

    if file.size and file.size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")

    content = await file.read()
    file_name = f"{uuid.uuid4()}.{ext}"
    upload_url = f"{SUPABASE_STORAGE_URL}/{file_name}"

    # Prefer the server-side service-role key so the storage bucket can stay
    # private (not writable by the public anon key). Fall back to the anon key
    # only for backward compatibility in development.
    storage_key = settings.supabase_service_key or settings.supabase_anon_key
    if not settings.supabase_service_key:
        logger.warning("SUPABASE_SERVICE_KEY not set - falling back to anon key for storage upload")

    headers = {
        "Authorization": f"Bearer {storage_key}",
        "Content-Type": file.content_type or "application/octet-stream",
    }

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(upload_url, headers=headers, content=content)
            resp.raise_for_status()
    except httpx.HTTPError as e:
        logger.error("Supabase storage upload failed: %s", e)
        raise HTTPException(status_code=500, detail="Failed to upload image") from e

    public_url = f"{SUPABASE_STORAGE_URL}/{file_name}"
    return {"url": public_url}
