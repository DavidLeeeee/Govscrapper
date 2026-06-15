import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.file_lock import file_lock
from src.services.trends.openai_trend_service import OpenAITrendAnalyzer
from src.services.trends.trend_service import generate_and_store_monthly_trend
from src.settings import get_settings


def main() -> None:
    args = _parse_args()
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY가 .env에 설정되어 있지 않습니다.")

    analyzer = OpenAITrendAnalyzer(api_key=settings.openai_api_key, model=settings.openai_trend_model)
    lock_path = settings.runtime_dir / "locks" / "generate_trends.lock"
    with file_lock(lock_path):
        reports = [
            generate_and_store_monthly_trend(
                settings.data_dir,
                analyzer,
                month=month,
                force=args.force,
            )
            for month in _target_months(args)
        ]

    print(
        [
            {
                "month": report["month"],
                "generated_at": report["generated_at"],
                "notice_count": report["notice_count"],
                "trend_count": len(report["trend_notice_words"]),
                "emerging_count": len(report["developer_emerging_words"]),
            }
            for report in reports
        ]
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="월별 공고 제목 트렌드를 생성한다.")
    parser.add_argument("--month", help="분석 대상 월. 예: 2026-06. 기본값은 실행일 기준 직전 월")
    parser.add_argument("--start-month", help="범위 분석 시작 월. 예: 2025-01")
    parser.add_argument("--end-month", help="범위 분석 종료 월. 예: 2026-05")
    parser.add_argument("--force", action="store_true", help="이미 생성된 월도 다시 OpenAI 분석한다.")
    args = parser.parse_args()
    if args.month and (args.start_month or args.end_month):
        parser.error("--month와 --start-month/--end-month는 함께 사용할 수 없습니다.")
    if bool(args.start_month) != bool(args.end_month):
        parser.error("--start-month와 --end-month는 함께 지정해야 합니다.")
    return args


def _target_months(args: argparse.Namespace) -> list[str | None]:
    if args.start_month and args.end_month:
        return _month_range(args.start_month, args.end_month)
    return [args.month]


def _month_range(start_month: str, end_month: str) -> list[str]:
    start_year, start = _parse_month(start_month)
    end_year, end = _parse_month(end_month)
    if (end_year, end) < (start_year, start):
        raise ValueError("--end-month는 --start-month보다 빠를 수 없습니다.")

    months: list[str] = []
    year = start_year
    month = start
    while (year, month) <= (end_year, end):
        months.append(f"{year:04d}-{month:02d}")
        month += 1
        if month == 13:
            month = 1
            year += 1
    return months


def _parse_month(value: str) -> tuple[int, int]:
    parts = value.split("-")
    if len(parts) != 2:
        raise ValueError("월은 YYYY-MM 형식이어야 합니다.")
    year = int(parts[0])
    month = int(parts[1])
    if month < 1 or month > 12:
        raise ValueError("월은 01~12 사이여야 합니다.")
    return year, month


if __name__ == "__main__":
    main()
