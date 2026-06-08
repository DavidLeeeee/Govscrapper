from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request

from src.scrapers.SITES_INFO import ScrapeTarget
from src.services.storage_service import read_json_list


router = APIRouter(tags=["notices"])

SOURCE_NAMES = {
    target.source_name: target.display_name
    for target in ScrapeTarget
}


@router.get("/notices")
async def list_notices(request: Request) -> dict[str, Any]:
    data_dir: Path = request.app.state.settings.data_dir
    active_root = data_dir / "active"
    notices: list[dict[str, Any]] = []

    for items_path in active_root.glob("*/items.json"):
        for notice in read_json_list(items_path):
            source = notice["source"]
            notices.append(
                {
                    **notice,
                    "source_display_name": SOURCE_NAMES.get(source, source),
                }
            )

    notices.sort(key=lambda notice: notice.get("posted_at", ""), reverse=True)

    sources = [
        {"source": source, "display_name": display_name}
        for source, display_name in sorted(
            {
                notice["source"]: notice["source_display_name"]
                for notice in notices
            }.items(),
            key=lambda item: item[1],
        )
    ]

    return {
        "notices": notices,
        "sources": sources,
        "count": len(notices),
    }
