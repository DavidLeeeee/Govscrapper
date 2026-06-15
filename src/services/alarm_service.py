"""Google Chat 알림에 사용할 최신 수집 결과를 파일로 관리한다."""

from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, TypedDict

from src.contracts.notice import MarkRecord, Notice


class AlarmPayload(TypedDict):
    generated_at: str
    start_date: str
    end_date: str
    notices: list[Notice]
    regional_notices: list[Notice]
    new_mark_records: list[MarkRecord]
    total_mark_count: int


def alarm_path(data_dir: Path) -> Path:
    return data_dir / "alarm" / "latest.json"


def write_alarm_payload(data_dir: Path, payload: AlarmPayload) -> None:
    path = alarm_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")

    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")

    os.replace(temp_path, path)


def read_alarm_payload(data_dir: Path) -> AlarmPayload | None:
    path = alarm_path(data_dir)
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as file:
        data: Any = json.load(file)

    if not isinstance(data, dict):
        return None
    return data  # type: ignore[return-value]


def filter_notices_by_posted_at(notices: list[Notice], start_date: date, end_date: date) -> list[Notice]:
    filtered: list[Notice] = []
    for notice in notices:
        posted_at = _parse_date(notice.get("posted_at"))
        if posted_at is not None and start_date <= posted_at <= end_date:
            filtered.append(notice)
    return filtered


def filter_mark_records_by_marked_at(records: list[MarkRecord], start_date: date, end_date: date) -> list[MarkRecord]:
    filtered: list[MarkRecord] = []
    for record in records:
        marked_at = _parse_date(record.get("marked_at"))
        if marked_at is not None and start_date <= marked_at <= end_date:
            filtered.append(record)
    return filtered


def build_alarm_payload(
    start_date: date,
    end_date: date,
    notices: list[Notice],
    regional_notices: list[Notice],
    mark_records: list[MarkRecord],
) -> AlarmPayload:
    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "notices": filter_notices_by_posted_at(notices, start_date, end_date),
        "regional_notices": filter_notices_by_posted_at(regional_notices, start_date, end_date),
        "new_mark_records": filter_mark_records_by_marked_at(mark_records, start_date, end_date),
        "total_mark_count": len(mark_records),
    }


def _parse_date(value: Any) -> date | None:
    try:
        return datetime.fromisoformat(str(value or "")[:10]).date()
    except ValueError:
        return None
