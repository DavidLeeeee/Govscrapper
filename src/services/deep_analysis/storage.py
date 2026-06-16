from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from src.contracts.notice import Notice
from src.services.storage_service import atomic_write_json, notice_key_string, read_json_list, sort_notices


def analysis_key(notice_or_key: Notice | str) -> str:
    raw_key = notice_or_key if isinstance(notice_or_key, str) else notice_key_string(notice_or_key)
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:24]


def analysis_path(data_dir: Path, notice_or_key: Notice | str) -> Path:
    return data_dir / "analysis" / f"{analysis_key(notice_or_key)}.json"


def read_analysis(data_dir: Path, notice_or_key: Notice | str) -> dict[str, Any] | None:
    path = analysis_path(data_dir, notice_or_key)
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as file:
        data: Any = json.load(file)

    return data if isinstance(data, dict) else None


def write_analysis(data_dir: Path, notice: Notice, analysis: dict[str, Any]) -> dict[str, Any]:
    stored = {
        **analysis,
        "key": notice_key_string(notice),
        "analysis_key": analysis_key(notice),
        "title": notice.get("title"),
        "source": notice.get("source"),
        "url": notice.get("url"),
        "analyzed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    atomic_write_json(analysis_path(data_dir, notice), stored)
    return stored


def mark_notice_analysis_completed(data_dir: Path, notice: Notice) -> bool:
    target_key = notice_key_string(notice)
    updated = False

    for path in _notice_item_paths(data_dir):
        items = read_json_list(path)
        changed = False
        next_items: list[Notice] = []
        for item in items:
            if notice_key_string(item) == target_key:
                item = {**item, "analysis": True}  # type: ignore[assignment]
                changed = True
                updated = True
            next_items.append(item)

        if changed:
            atomic_write_json(path, sort_notices(next_items))

    return updated


def _notice_item_paths(data_dir: Path) -> list[Path]:
    paths: list[Path] = []
    paths.extend((data_dir / "active").glob("*/items.json"))
    paths.extend((data_dir / "expired").glob("*/*/items.json"))
    regional_root = data_dir / "regional"
    paths.extend((regional_root / "active").glob("*/items.json"))
    paths.extend((regional_root / "expired").glob("*/*/items.json"))

    unique_paths: dict[str, Path] = {}
    for path in paths:
        unique_paths[os.fspath(path)] = path
    return list(unique_paths.values())
