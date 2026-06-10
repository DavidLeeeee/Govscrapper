from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from src.scrapers.SITES_INFO import ScrapeTarget
from src.services.marked_service import apply_marked_state, list_marked_notices, mark_notice, unmark_notice
from src.services.storage_service import manually_expire_notice, merge_notices, notice_key_string, read_json_list, sort_notices


router = APIRouter(tags=["notices"])

SOURCE_NAMES = {
    target.source_name: target.display_name
    for target in ScrapeTarget
}


@router.get("/notices")
async def list_notices(request: Request) -> dict[str, Any]:
    settings = request.app.state.settings
    data_dir: Path = settings.data_dir
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
                    "source_display_name": SOURCE_NAMES.get(source, source),
                }
            )

    for items_path in expired_root.glob("*/*/items.json"):
        for notice in read_json_list(items_path):
            source = notice["source"]
            expired_notices.append(
                {
                    **notice,
                    "source_display_name": SOURCE_NAMES.get(source, source),
                    "expired": True,
                }
            )

    marked_records = list_marked_notices(data_dir)
    notices = apply_marked_state(notices, marked_records)
    notices = sort_notices(notices)
    expired_notices = sort_notices(apply_marked_state(expired_notices, marked_records))
    bookmarks = _build_bookmarks(notices, expired_notices, marked_records)

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
    expired_sources = [
        {"source": source, "display_name": display_name}
        for source, display_name in sorted(
            {
                notice["source"]: notice["source_display_name"]
                for notice in expired_notices
            }.items(),
            key=lambda item: item[1],
        )
    ]

    return {
        "notices": notices,
        "expired_notices": expired_notices,
        "bookmarks": bookmarks,
        "sources": sources,
        "expired_sources": expired_sources,
        "count": len(notices),
        "expired_count": len(expired_notices),
        "no_deadline_expire_days": settings.no_deadline_expire_days,
    }


def _build_bookmarks(
    active_notices: list[dict[str, Any]],
    expired_notices: list[dict[str, Any]],
    marked_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    marked_by_key = {str(record.get("key")): record for record in marked_records}
    all_notices = merge_notices(expired_notices, active_notices)
    bookmarks: list[dict[str, Any]] = []

    for notice in all_notices:
        key = notice_key_string(notice)
        mark = marked_by_key.get(key)
        if mark is None:
            continue

        bookmarks.append(
            {
                **notice,
                "marked": True,
                "mark": mark,
            }
        )

    return sort_notices(bookmarks)


@router.post("/notices/marks")
async def create_notice_mark(request: Request, notice: dict[str, Any]) -> dict[str, Any]:
    data_dir: Path = request.app.state.settings.data_dir
    marked_by = request.client.host if request.client else "shared"
    record = mark_notice(data_dir, notice, marked_by=marked_by)

    return {
        "key": record["key"],
        "mark": record,
    }


@router.post("/notices/marks/remove")
async def remove_notice_mark(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
    data_dir: Path = request.app.state.settings.data_dir
    key = str(payload.get("key") or "")

    if not key and isinstance(payload.get("notice"), dict):
        key = notice_key_string(payload["notice"])

    removed = unmark_notice(data_dir, key)

    return {
        "key": key,
        "removed": removed,
    }


@router.post("/notices/expire")
async def expire_notice(request: Request, notice: dict[str, Any]) -> dict[str, Any]:
    data_dir: Path = request.app.state.settings.data_dir
    expired_notice = manually_expire_notice(data_dir, notice)

    if expired_notice is None:
        raise HTTPException(status_code=404, detail="Active notice not found")

    source = expired_notice["source"]
    return {
        **expired_notice,
        "source_display_name": SOURCE_NAMES.get(source, source),
        "expired": True,
    }
