from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.middleware.auth import get_current_user
from app.models.user import User
from app.schemas.analytics import (
    AnalyticsResponse,
    DateRangeParams,
)
from app.services import analytics_service

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("", response_model=AnalyticsResponse)
async def get_analytics(
    period: str = Query("day", pattern="^(day|week|month)$"),
    days: int = Query(30, ge=1, le=365),
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if start_date and end_date:
        params = DateRangeParams(
            start_date=start_date, end_date=end_date, period=period
        )
    else:
        params = DateRangeParams(period=period)
        if not start_date:
            params.start_date = datetime.now(UTC) - timedelta(days=days)

    return await analytics_service.get_analytics(db, current_user.id, params)
