"""사용자가 표시한 공고(marked) 상태를 파일로 관리한다.
active 공고 목록에 marked 상태를 합쳐 화면 표시용 데이터로 만든다."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from src.contracts.notice import MarkRecord, Notice
from src.services.storage_service import (
    atomic_write_json,
    marked_path,
    notice_key_string,
    read_raw_json_list,
)


def list_marked_notices(data_dir: Path) -> list[MarkRecord]:
    return read_raw_json_list(marked_path(data_dir))  # type: ignore[return-value]


def mark_notice(data_dir: Path, notice: Notice, marked_by: str, memo: str | None = None) -> MarkRecord:
    records = list_marked_notices(data_dir)
    key = notice_key_string(notice)

    record: MarkRecord = {
        "key": key,
        "source": notice.get("source"),
        "title": notice.get("title"),
        "url": notice.get("url"),
        "deadline": notice.get("deadline"),
        "marked_by": marked_by,
        "marked_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "memo": memo,
    }

    updated = [existing for existing in records if existing.get("key") != key]
    updated.append(record)
    atomic_write_json(marked_path(data_dir), updated)

    return record


def unmark_notice(data_dir: Path, key: str) -> bool:
    records = list_marked_notices(data_dir)
    updated = [record for record in records if record.get("key") != key]

    if len(updated) == len(records):
        return False

    atomic_write_json(marked_path(data_dir), updated)
    return True


def apply_marked_state(notices: list[Notice], marked_records: list[MarkRecord]) -> list[Notice]:
    marked_by_key = {str(record.get("key")): record for record in marked_records}
    merged: list[Notice] = []

    for notice in notices:
        key = notice_key_string(notice)
        mark = marked_by_key.get(key)
        merged_notice = dict(notice)
        merged_notice["marked"] = mark is not None
        if mark is not None:
            merged_notice["mark"] = mark
        merged.append(merged_notice)

    return merged
