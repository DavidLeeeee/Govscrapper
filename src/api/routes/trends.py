from typing import Any

from fastapi import APIRouter, Query, Request

from src.services.trends.storage import read_trend_report


router = APIRouter(tags=["trends"])


@router.get("/trends")
async def get_trends(request: Request, month: str | None = Query(default=None)) -> dict[str, Any]:
    return read_trend_report(request.app.state.settings.data_dir, selected_month=month)
