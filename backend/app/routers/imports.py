import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.services.import_service import ImportError, import_products_from_file

router = APIRouter(prefix="/api/import", tags=["import"])


@router.post("/products")
async def import_products(
    file: UploadFile = File(...),
    category_id: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if file.size and file.size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 5MB)")

    ext = (file.filename or "").lower()
    if not ext.endswith((".xlsx", ".xls", ".csv")):
        raise HTTPException(status_code=400, detail="Invalid file type. Allowed: .xlsx, .xls, .csv")

    cat_id = uuid.UUID(category_id) if category_id else None

    try:
        result = await import_products_from_file(db, current_user.id, file, cat_id)
        return result
    except ImportError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
