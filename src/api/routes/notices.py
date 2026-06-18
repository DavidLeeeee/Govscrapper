import asyncio
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request

from src.scrapers.SITES_INFO import ScrapeTarget
from src.services.deep_analysis.claude_deep_analyzer import ClaudeSDKDeepAnalyzer
from src.services.deep_analysis.contracts import DeepAnalyzer
from src.services.deep_analysis.openai_deep_analyzer import OpenAIDeepAnalyzer
from src.services.deep_analysis.service import analyze_notice, get_analysis
from src.services.notification_service import build_shared_notice_message, send_google_chat_message
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


@router.post("/notices/share")
async def share_notice(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
    settings = request.app.state.settings
    webhook_url = settings.google_chat_webhook_url
    if not webhook_url:
        raise HTTPException(status_code=500, detail="CHAT_API_URL is not configured")

    notice = payload.get("notice")
    if not isinstance(notice, dict):
        raise HTTPException(status_code=400, detail="notice is required")

    share_url = str(payload.get("share_url") or "").strip()
    message = build_shared_notice_message(notice, share_url=share_url or None)
    send_google_chat_message(webhook_url, message)

    return {"shared": True}


@router.get("/notices/analysis")
async def read_notice_analysis(request: Request, key: str) -> dict[str, Any]:
    data_dir: Path = request.app.state.settings.data_dir
    analysis = get_analysis(data_dir, key)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis


@router.post("/notices/analysis")
async def create_notice_analysis(request: Request, notice: dict[str, Any]) -> dict[str, Any]:
    settings = request.app.state.settings
    if not notice.get("source") or not notice.get("title"):
        raise HTTPException(status_code=400, detail="notice source and title are required")

    analyzer = _build_deep_analyzer(settings)
    fallback_analyzer = _build_hwp_fallback_analyzer(settings)
    try:
        return await asyncio.to_thread(
            analyze_notice,
            settings.data_dir,
            notice,
            analyzer,
            fallback_analyzer=fallback_analyzer,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def _build_deep_analyzer(settings: Any) -> DeepAnalyzer:
    provider = settings.analysis_provider.strip().lower()
    if provider == "openai":
        if not settings.openai_api_key:
            raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured")
        return OpenAIDeepAnalyzer(
            api_key=settings.openai_api_key,
            model=settings.openai_analysis_model,
            max_file_chars=settings.analysis_max_file_chars,
            max_prompt_chars=settings.analysis_max_prompt_chars,
            max_output_tokens=settings.analysis_max_output_tokens,
            reasoning_effort=settings.analysis_reasoning_effort,
        )

    if provider == "claude":
        return ClaudeSDKDeepAnalyzer(
            model=settings.claude_analysis_model,
            max_file_chars=settings.analysis_max_file_chars,
            max_prompt_chars=settings.analysis_max_prompt_chars,
            max_output_tokens=settings.analysis_max_output_tokens,
        )

    raise HTTPException(status_code=500, detail=f"Unsupported ANALYSIS_PROVIDER: {settings.analysis_provider}")


def _build_hwp_fallback_analyzer(settings: Any) -> DeepAnalyzer | None:
    provider = str(settings.analysis_hwp_fallback_provider or "").strip().lower()
    if provider != "openai":
        return None
    if not settings.openai_api_key:
        raise HTTPException(status_code=500, detail="ANALYSIS_HWP_FALLBACK_PROVIDER=openai requires OPENAI_API_KEY")
    return OpenAIDeepAnalyzer(
        api_key=settings.openai_api_key,
        model=settings.openai_analysis_model,
        max_file_chars=settings.analysis_max_file_chars,
        max_prompt_chars=settings.analysis_max_prompt_chars,
        max_output_tokens=settings.analysis_max_output_tokens,
        reasoning_effort=settings.analysis_reasoning_effort,
    )
