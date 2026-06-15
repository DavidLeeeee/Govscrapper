from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from src.contracts.notice import Notice
from src.services.storage_service import read_json_list, sort_notices
from src.services.trends.contracts import MonthlyTrendReport
from src.services.trends.openai_trend_service import OpenAITrendAnalyzer
from src.services.trends.storage import read_monthly_trend, write_monthly_trend


def generate_and_store_monthly_trend(
    data_dir: Path,
    analyzer: OpenAITrendAnalyzer,
    month: str | None = None,
    force: bool = False,
) -> MonthlyTrendReport:
    target_month = month or previous_month(date.today())
    existing = read_monthly_trend(data_dir, target_month)
    if existing is not None and not force:
        return existing

    notices = _filter_month_notices(_load_all_notices(data_dir), target_month)
    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    if notices:
        report = analyzer.analyze_month(notices, target_month)
        report["generated_at"] = generated_at
    else:
        report = {
            "month": target_month,
            "generated_at": generated_at,
            "notice_count": 0,
            "trend_notice_words": [],
            "developer_emerging_words": [],
        }
    write_monthly_trend(data_dir, target_month, report)
    return report


def previous_month(value: date) -> str:
    year = value.year
    month = value.month - 1
    if month == 0:
        month = 12
        year -= 1
    return f"{year:04d}-{month:02d}"


def _load_all_notices(data_dir: Path) -> list[Notice]:
    notices: list[Notice] = []
    for path in (data_dir / "active").glob("*/items.json"):
        notices.extend(read_json_list(path))
    for path in (data_dir / "expired").glob("*/*/items.json"):
        notices.extend(read_json_list(path))
    return sort_notices(_dedupe_notices(notices))


def _filter_month_notices(notices: list[Notice], month: str) -> list[Notice]:
    return [
        notice
        for notice in notices
        if (posted_at := _parse_date(str(notice.get("posted_at") or ""))) is not None
        and f"{posted_at.year:04d}-{posted_at.month:02d}" == month
    ]


def _dedupe_notices(notices: list[Notice]) -> list[Notice]:
    deduped: list[Notice] = []
    seen: set[tuple[str, str, str]] = set()
    for notice in notices:
        key = (
            str(notice.get("source") or ""),
            str(notice.get("url") or ""),
            str(notice.get("title") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(notice)
    return deduped


def _parse_date(value: str) -> date | None:
    try:
        return datetime.fromisoformat(value[:10]).date()
    except ValueError:
        return None
