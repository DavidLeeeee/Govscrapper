from __future__ import annotations

import json
import os
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path
from typing import Any

Notice = dict[str, Any]


def read_json_list(path: Path) -> list[Notice]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(f"JSON list 형식이 아닙니다: {path}")

    return data


def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")

    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")

    os.replace(temp_path, path)


def notice_key(notice: Notice) -> tuple[str, str, str]:
    source = str(notice.get("source", ""))
    url = str(notice.get("url", ""))
    if url:
        return source, "url", url

    title = str(notice.get("title", ""))
    deadline = str(notice.get("deadline", ""))
    return source, title, deadline


def merge_notices(existing: Iterable[Notice], incoming: Iterable[Notice]) -> list[Notice]:
    merged: dict[tuple[str, str, str], Notice] = {}

    for notice in existing:
        merged[notice_key(notice)] = notice

    for notice in incoming:
        merged[notice_key(notice)] = notice

    return list(merged.values())


def find_new_notices(existing: Iterable[Notice], incoming: Iterable[Notice]) -> list[Notice]:
    existing_keys = {notice_key(notice) for notice in existing}
    return [notice for notice in incoming if notice_key(notice) not in existing_keys]


def split_by_deadline(notices: Iterable[Notice], today: date | None = None) -> tuple[list[Notice], list[Notice]]:
    current_date = today or datetime.now().date()
    active: list[Notice] = []
    expired: list[Notice] = []

    for notice in notices:
        deadline_value = notice.get("deadline")
        if not deadline_value:
            active.append(notice)
            continue

        deadline = date.fromisoformat(str(deadline_value))
        if deadline < current_date:
            expired.append(notice)
        else:
            active.append(notice)

    return active, expired


def source_active_path(data_dir: Path, source_name: str) -> Path:
    return data_dir / "active" / source_name / "items.json"


def source_expired_path(data_dir: Path, source_name: str, year: int) -> Path:
    return data_dir / "expired" / source_name / str(year) / "items.json"


def source_snapshot_dir(data_dir: Path, source_name: str, snapshot_date: date) -> Path:
    return data_dir / "sources" / source_name / snapshot_date.isoformat()
