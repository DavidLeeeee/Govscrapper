from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from src.services.trends.contracts import TrendReport


def trends_path(data_dir: Path) -> Path:
    return data_dir / "trends" / "latest.json"


def read_trend_report(data_dir: Path) -> TrendReport | None:
    path = trends_path(data_dir)
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as file:
        data: Any = json.load(file)

    if not isinstance(data, dict):
        return None

    return data  # type: ignore[return-value]


def write_trend_report(data_dir: Path, report: TrendReport) -> None:
    path = trends_path(data_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")

    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)
        file.write("\n")

    os.replace(temp_path, path)
