from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from src.services.trends.contracts import MonthlyTrendReport, TrendReport


MONTH_PATTERN = re.compile(r"^\d{4}-\d{2}$")


def monthly_trends_dir(data_dir: Path) -> Path:
    return data_dir / "trends" / "monthly"


def monthly_trend_path(data_dir: Path, month: str) -> Path:
    _validate_month(month)
    return monthly_trends_dir(data_dir) / f"{month}.json"


def list_available_months(data_dir: Path) -> list[str]:
    path = monthly_trends_dir(data_dir)
    if not path.exists():
        return []

    months = [
        item.stem
        for item in path.glob("*.json")
        if item.is_file() and MONTH_PATTERN.match(item.stem)
    ]
    return sorted(months, reverse=True)


def read_monthly_trend(data_dir: Path, month: str) -> MonthlyTrendReport | None:
    path = monthly_trend_path(data_dir, month)
    if not path.exists():
        return None

    with path.open("r", encoding="utf-8") as file:
        data: Any = json.load(file)

    if not isinstance(data, dict):
        return None

    return data  # type: ignore[return-value]


def read_trend_report(data_dir: Path, selected_month: str | None = None, display_count: int = 3) -> TrendReport:
    available_months = list_available_months(data_dir)
    selected = selected_month if selected_month in available_months else (available_months[0] if available_months else None)
    months: dict[str, MonthlyTrendReport] = {}

    if selected is not None:
        for month in _previous_months(selected, display_count):
            report = read_monthly_trend(data_dir, month)
            if report is not None:
                months[month] = report

    return {
        "generated_at": max((str(report.get("generated_at") or "") for report in months.values()), default=""),
        "source": "openai",
        "months": months,
        "available_months": available_months,
    }


def write_monthly_trend(data_dir: Path, month: str, report: MonthlyTrendReport) -> None:
    path = monthly_trend_path(data_dir, month)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")

    with temp_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, ensure_ascii=False, indent=2)
        file.write("\n")

    os.replace(temp_path, path)


def _previous_months(month: str, count: int) -> list[str]:
    year, month_number = [int(part) for part in month.split("-")]
    result: list[str] = []
    for _ in range(count):
        result.append(f"{year:04d}-{month_number:02d}")
        month_number -= 1
        if month_number == 0:
            month_number = 12
            year -= 1
    return result


def _validate_month(month: str) -> None:
    if not MONTH_PATTERN.match(month):
        raise ValueError("month는 YYYY-MM 형식이어야 합니다.")
