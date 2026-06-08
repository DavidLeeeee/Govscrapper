"""파일 기반 저장소의 공통 읽기/쓰기와 경로 생성을 담당한다.
공고 병합, 신규 판별, 마감 기준 분리 같은 저장 관련 유틸도 포함한다."""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from datetime import date, datetime
from pathlib import Path
from typing import Any

from src.contracts.notice import Notice


def normalize_notice(notice: Notice) -> Notice:
    return {
        "source": str(notice.get("source", "")),
        "title": str(notice.get("title", "")),
        "url": str(notice.get("url", "")),
        "posted_at": str(notice.get("posted_at", "")),
        "deadline": notice.get("deadline"),
        "scraped_at": str(notice.get("scraped_at", datetime.now().astimezone().isoformat(timespec="seconds"))),
        "keywords": list(notice.get("keywords", [])),
    }


def normalize_notices(notices: Iterable[Notice]) -> list[Notice]:
    return [normalize_notice(notice) for notice in notices]


def read_json_list(path: Path) -> list[Notice]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(f"JSON list 형식이 아닙니다: {path}")

    return normalize_notices(data)


def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")

    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")

    os.replace(temp_path, path)


def notice_key(notice: Notice) -> tuple[str, str, str]:
    source = str(notice.get("source", ""))
    title = str(notice.get("title", ""))
    posted_at = str(notice.get("posted_at", ""))

    if source == "nia" and title and posted_at:
        return source, title, posted_at

    url = str(notice.get("url", ""))
    if url:
        return source, "url", url

    deadline = str(notice.get("deadline", ""))
    return source, title, deadline


def notice_key_string(notice: Notice) -> str:
    return ":".join(notice_key(notice))


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


def marked_path(data_dir: Path) -> Path:
    return data_dir / "marked" / "items.json"
