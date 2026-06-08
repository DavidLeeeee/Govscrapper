"""등록된 사이트별 스크래퍼를 실행하고 결과를 저장한다.
신규 공고를 판별한 뒤 필요하면 알림 서비스까지 호출한다."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from src.contracts.notice import Notice
from src.contracts.scrape_options import ScrapeOptions
from src.services.notification_service import build_new_notice_message, send_google_chat_message
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
) -> dict[str, Any]:
    result: dict[str, Any] = {"sources": {}, "new_count": 0}
    today = datetime.now().date()

    for source_name, scraper in scrapers.items():
        scraped_items = sort_notices(normalize_notices(scraper(options)))
        snapshot_dir = source_snapshot_dir(data_dir, source_name, today)
        atomic_write_json(snapshot_dir / "items.json", scraped_items)

        active_path = source_active_path(data_dir, source_name)
        existing_items = read_json_list(active_path)
        new_items = find_new_notices(existing_items, scraped_items)
        merged_items = merge_notices(existing_items, scraped_items)
        atomic_write_json(active_path, merged_items)

        result["sources"][source_name] = {
            "scraped_count": len(scraped_items),
            "new_count": len(new_items),
        }
        result["new_count"] += len(new_items)

        if new_items and google_chat_webhook_url:
            message = build_new_notice_message(new_items)
            send_google_chat_message(google_chat_webhook_url, message)

    return result
