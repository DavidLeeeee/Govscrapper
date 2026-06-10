from typing import Any

from fastapi import APIRouter, Request

from src.services.trends.storage import read_trend_report


router = APIRouter(tags=["trends"])


@router.get("/trends")
async def get_trends(request: Request) -> dict[str, Any]:
    report = read_trend_report(request.app.state.settings.data_dir)
    if report is None:
        return {"generated_at": None, "source": "openai", "windows": {}}
    return report
