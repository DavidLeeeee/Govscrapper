from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Request

from src.scrapers.regional_registry import REGIONAL_SOURCE_NAMES
from src.services.storage_service import read_json_list, sort_notices


router = APIRouter(tags=["regional-notices"])


@router.get("/regional-notices")
async def list_regional_notices(request: Request) -> dict[str, Any]:
    data_dir: Path = request.app.state.settings.data_dir / "regional"
    active_root = data_dir / "active"
    expired_root = data_dir / "expired"
    notices: list[dict[str, Any]] = []
    expired_notices: list[dict[str, Any]] = []

    for items_path in active_root.glob("*/items.json"):
        for notice in read_json_list(items_path):
            source = notice["source"]
            notices.append(
                {
                    **notice,
                    "source_display_name": REGIONAL_SOURCE_NAMES.get(source, source),
                }
            )

    for items_path in expired_root.glob("*/*/items.json"):
        for notice in read_json_list(items_path):
            source = notice["source"]
            expired_notices.append(
                {
                    **notice,
                    "source_display_name": REGIONAL_SOURCE_NAMES.get(source, source),
                    "expired": True,
                }
            )

    notices = sort_notices(notices)
    expired_notices = sort_notices(expired_notices)

    return {
        "notices": notices,
        "expired_notices": expired_notices,
        "sources": _build_sources(notices),
        "expired_sources": _build_sources(expired_notices),
        "regions": _build_regions(notices),
        "expired_regions": _build_regions(expired_notices),
        "count": len(notices),
        "expired_count": len(expired_notices),
    }


def _build_sources(notices: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {"source": source, "display_name": display_name}
        for source, display_name in sorted(
            {
                str(notice["source"]): str(notice.get("source_display_name") or notice["source"])
                for notice in notices
            }.items(),
            key=lambda item: item[1],
        )
    ]


def _build_regions(notices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for notice in notices:
        region = str(notice.get("region") or "지역 미상")
        counts[region] = counts.get(region, 0) + 1

    return [
        {"region": region, "count": count}
        for region, count in sorted(counts.items(), key=lambda item: item[0])
    ]
