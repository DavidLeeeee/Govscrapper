import argparse
import sys
from datetime import date, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.scrapers.registry import SCRAPERS
from src.contracts.scrape_options import ScrapeOptions
from src.services.file_lock import file_lock
from src.services.scraping_service import run_scraping
from src.services.summarization_service import build_openai_summarizer
from src.services.trends.openai_trend_service import OpenAITrendAnalyzer
from src.services.trends.trend_service import generate_and_store_trends
from src.settings import get_settings


def main() -> None:
    args = _parse_args()
    settings = get_settings()
    lock_path = settings.runtime_dir / "locks" / "scraping.lock"

    with file_lock(lock_path):
        today = datetime.now().date()
        options = _build_scrape_options(args, today)
        summarizer = None
        if settings.summarize_notices:
            summarizer = build_openai_summarizer(
                api_key=settings.openai_api_key,
                model=settings.openai_summary_model,
                max_detail_chars=settings.summary_max_detail_chars,
                max_output_tokens=settings.summary_max_output_tokens,
            )
            if summarizer is None:
                raise RuntimeError("SUMMARIZE_NOTICES=true 이지만 OPENAI_API_KEY가 .env에 설정되어 있지 않습니다.")

        result = run_scraping(
            data_dir=settings.data_dir,
            scrapers=SCRAPERS,
            options=options,
            google_chat_webhook_url=None,
            summarizer=summarizer,
            on_summary_progress=lambda message: print(message, flush=True),
        )
        if settings.generate_trends_after_scraping:
            if not settings.openai_api_key:
                raise RuntimeError("GENERATE_TRENDS_AFTER_SCRAPING=true 이지만 OPENAI_API_KEY가 .env에 설정되어 있지 않습니다.")
            print("[trends] 키워드 트렌드 생성 시작", flush=True)
            trend_report = generate_and_store_trends(
                settings.data_dir,
                OpenAITrendAnalyzer(
                    api_key=settings.openai_api_key,
                    model=settings.openai_trend_model,
                ),
            )
            result["trends_generated_at"] = trend_report["generated_at"]

        print(result)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="등록된 스크래퍼를 실행해 파일 저장소에 반영한다.")
    parser.add_argument("--start-date", help="수집 시작 등록일. 예: 2026-06-11")
    parser.add_argument("--end-date", help="수집 종료 등록일. 기본값: start-date 또는 오늘")
    return parser.parse_args()


def _build_scrape_options(args: argparse.Namespace, today: date) -> ScrapeOptions:
    if not args.start_date and not args.end_date:
        return ScrapeOptions.daily(today)

    start_date = date.fromisoformat(args.start_date) if args.start_date else today
    end_date = date.fromisoformat(args.end_date) if args.end_date else start_date
    if end_date < start_date:
        raise ValueError("--end-date는 --start-date보다 빠를 수 없습니다.")

    return ScrapeOptions.backfill(start_date=start_date, end_date=end_date)


if __name__ == "__main__":
    main()
