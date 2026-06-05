"""active 공고를 기준으로 마감 여부를 다시 정렬한다.
마감된 공고는 expired 저장소로 이동하고 active에는 유효 공고만 남긴다."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from src.contracts.notice import Notice
from src.services.storage_service import (
    atomic_write_json,
    merge_notices,
    read_json_list,
    source_expired_path,
    split_by_deadline,
)


def align_expired_notices(data_dir: Path) -> dict[str, Any]:
    active_root = data_dir / "active"
    result: dict[str, Any] = {"sources": {}, "expired_count": 0}

    for active_path in active_root.glob("*/items.json"):
        source_name = active_path.parent.name
        notices = read_json_list(active_path)
        active_items, expired_items = split_by_deadline(notices)

        atomic_write_json(active_path, active_items)

        expired_by_year: dict[int, list[Notice]] = defaultdict(list)
        for notice in expired_items:
            deadline = datetime.fromisoformat(str(notice["deadline"])).date()
            expired_by_year[deadline.year].append(notice)

        for year, year_items in expired_by_year.items():
            expired_path = source_expired_path(data_dir, source_name, year)
            existing_expired = read_json_list(expired_path)
            atomic_write_json(expired_path, merge_notices(existing_expired, year_items))

        result["sources"][source_name] = {
            "active_count": len(active_items),
            "expired_count": len(expired_items),
        }
        result["expired_count"] += len(expired_items)

    return result
