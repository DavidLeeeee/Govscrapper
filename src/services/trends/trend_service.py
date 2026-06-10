from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime
from pathlib import Path

from src.contracts.notice import Notice
from src.services.storage_service import read_json_list, sort_notices
from src.services.trends.contracts import TrendReport
from src.services.trends.openai_trend_service import OpenAITrendAnalyzer
from src.services.trends.storage import write_trend_report


TREND_WINDOWS = (1, 2, 6)


def generate_and_store_trends(data_dir: Path, analyzer: OpenAITrendAnalyzer) -> TrendReport:
    notices = _load_all_notices(data_dir)
    report: TrendReport = {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": "openai",
        "windows": {},
    }

    for months in TREND_WINDOWS:
        report["windows"][str(months)] = analyzer.analyze_window(_filter_recent_notices(notices, months), months)

    write_trend_report(data_dir, report)
    return report


def _load_all_notices(data_dir: Path) -> list[Notice]:
    notices: list[Notice] = []
    for path in (data_dir / "active").glob("*/items.json"):
        notices.extend(read_json_list(path))
    for path in (data_dir / "expired").glob("*/*/items.json"):
        notices.extend(read_json_list(path))
    return sort_notices(notices)


def _filter_recent_notices(notices: list[Notice], months: int) -> list[Notice]:
    cutoff = _subtract_months(date.today(), months)
    return [
        notice
        for notice in notices
        if (posted_at := _parse_date(str(notice.get("posted_at") or ""))) is not None and posted_at >= cutoff
    ]


def _subtract_months(value: date, months: int) -> date:
    month = value.month - months
    year = value.year
    while month <= 0:
        month += 12
        year -= 1
    day = min(value.day, monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _parse_date(value: str) -> date | None:
    try:
        return datetime.fromisoformat(value[:10]).date()
    except ValueError:
        return None
