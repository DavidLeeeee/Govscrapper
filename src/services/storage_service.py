"""파일 기반 저장소의 공통 읽기/쓰기와 경로 생성을 담당한다.
공고 병합, 신규 판별, 마감 기준 분리 같은 저장 관련 유틸도 포함한다."""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from src.contracts.notice import Notice


def normalize_notice(notice: Notice) -> Notice:
    normalized: Notice = {
        "source": str(notice.get("source", "")),
        "title": str(notice.get("title", "")),
        "url": str(notice.get("url", "")),
        "posted_at": str(notice.get("posted_at", "")),
        "deadline": notice.get("deadline"),
        "scraped_at": str(notice.get("scraped_at", datetime.now().astimezone().isoformat(timespec="seconds"))),
        "keywords": list(notice.get("keywords", [])),
    }

    if "summary" in notice:
        summary = notice.get("summary")
        normalized["summary"] = str(summary).strip() if summary else None

    if "detail_points" in notice:
        detail_points = notice.get("detail_points") or []
        normalized["detail_points"] = [str(point).strip() for point in detail_points if str(point).strip()]

    if "detail_fetched_at" in notice:
        fetched_at = notice.get("detail_fetched_at")
        normalized["detail_fetched_at"] = str(fetched_at).strip() if fetched_at else None

    return normalized


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


def read_raw_json_list(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(f"JSON list 형식이 아닙니다: {path}")

    return [item for item in data if isinstance(item, dict)]


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

    return sort_notices(list(merged.values()))


def sort_notices(notices: Iterable[Notice]) -> list[Notice]:
    return sorted(
        notices,
        key=lambda notice: (
            str(notice.get("posted_at") or ""),
            str(notice.get("scraped_at") or ""),
            str(notice.get("title") or ""),
        ),
        reverse=True,
    )


def find_new_notices(existing: Iterable[Notice], incoming: Iterable[Notice]) -> list[Notice]:
    existing_keys = {notice_key(notice) for notice in existing}
    return [notice for notice in incoming if notice_key(notice) not in existing_keys]


def split_by_deadline(
    notices: Iterable[Notice],
    today: date | None = None,
    no_deadline_expire_days: int = 60,
) -> tuple[list[Notice], list[Notice]]:
    current_date = today or datetime.now().date()
    active: list[Notice] = []
    expired: list[Notice] = []

    for notice in notices:
        expires_at = notice_expires_at(notice, no_deadline_expire_days)
        if expires_at is not None and expires_at < current_date:
            expired.append(notice)
        else:
            active.append(notice)

    return active, expired


def notice_expires_at(notice: Notice, no_deadline_expire_days: int = 60) -> date | None:
    deadline_value = notice.get("deadline")
    if deadline_value:
        return date.fromisoformat(str(deadline_value))

    base_date = _parse_notice_date(notice.get("posted_at")) or _parse_notice_date(notice.get("scraped_at"))
    if base_date is None:
        return None

    return base_date + timedelta(days=no_deadline_expire_days)


def _parse_notice_date(value: Any) -> date | None:
    if not value:
        return None

    text = str(value)
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def source_active_path(data_dir: Path, source_name: str) -> Path:
    return data_dir / "active" / source_name / "items.json"


def source_expired_path(data_dir: Path, source_name: str, year: int) -> Path:
    return data_dir / "expired" / source_name / str(year) / "items.json"


def source_snapshot_dir(data_dir: Path, source_name: str, snapshot_date: date) -> Path:
    return data_dir / "sources" / source_name / snapshot_date.isoformat()


def marked_path(data_dir: Path) -> Path:
    return data_dir / "marked" / "items.json"
