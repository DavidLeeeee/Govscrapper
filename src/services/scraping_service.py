"""등록된 사이트별 스크래퍼를 실행하고 결과를 저장한다."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from src.contracts.notice import Notice
from src.contracts.scrape_options import ScrapeOptions
from src.services.summarization_service import NoticeSummarizer, summarize_notices
from src.services.storage_service import (
    atomic_write_json,
    find_new_notices,
    merge_notices,
    normalize_notices,
    read_json_list,
    source_active_path,
    source_snapshot_dir,
    sort_notices,
)

Scraper = Callable[[ScrapeOptions], list[Notice]]


def run_scraping(
    data_dir: Path,
    scrapers: dict[str, Scraper],
    options: ScrapeOptions,
    google_chat_webhook_url: str | None = None,
    summarizer: NoticeSummarizer | None = None,
    on_summary_progress: Callable[[str], None] | None = None,
    collect_new_notices: bool = False,
    collect_scraped_notices: bool = False,
) -> dict[str, Any]:
    result: dict[str, Any] = {"sources": {}, "new_count": 0, "summarized_count": 0, "summary_error_count": 0}
    if collect_new_notices:
        result["new_notices"] = []
    if collect_scraped_notices:
        result["scraped_notices"] = []
    today = datetime.now().date()
    active_paths_by_source: dict[str, Path] = {}
    scraped_items_by_source: dict[str, list[Notice]] = {}

    for source_name, scraper in scrapers.items():
        scraped_items = sort_notices(normalize_notices(scraper(options)))
        scraped_items_by_source[source_name] = scraped_items
        snapshot_dir = source_snapshot_dir(data_dir, source_name, today)
        atomic_write_json(snapshot_dir / "items.json", scraped_items)

        active_path = source_active_path(data_dir, source_name)
        active_paths_by_source[source_name] = active_path
        existing_items = read_json_list(active_path)
        new_items = find_new_notices(existing_items, scraped_items)
        merged_items = merge_notices(existing_items, scraped_items)
        atomic_write_json(active_path, merged_items)

        result["sources"][source_name] = {
            "scraped_count": len(scraped_items),
            "new_count": len(new_items),
            "summarized_count": 0,
            "summary_error_count": 0,
        }
        result["new_count"] += len(new_items)
        if collect_new_notices:
            result["new_notices"].extend(new_items)

    if summarizer is not None:
        for source_name, active_path in active_paths_by_source.items():
            scraped_items = scraped_items_by_source.get(source_name, [])
            if not scraped_items:
                continue
            if on_summary_progress is not None:
                on_summary_progress(f"[source] {source_name} 요약 시작")
            active_items = read_json_list(active_path)
            updated_items, summary_stats = summarize_notices(
                scraped_items,
                summarizer,
                active_items,
                on_progress=on_summary_progress,
            )
            atomic_write_json(active_path, merge_notices(active_items, updated_items))
            scraped_items_by_source[source_name] = updated_items
            result["sources"][source_name]["summarized_count"] = summary_stats["summarized_count"]
            result["sources"][source_name]["summary_error_count"] = summary_stats["error_count"]
            result["summarized_count"] += summary_stats["summarized_count"]
            result["summary_error_count"] += summary_stats["error_count"]

    if collect_scraped_notices:
        result["scraped_notices"] = [
            notice
            for source_name in active_paths_by_source
            for notice in scraped_items_by_source.get(source_name, [])
        ]

    return result
