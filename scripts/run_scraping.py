import argparse
import sys
from datetime import date, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.scrapers.registry import SCRAPERS, build_scrapers
from src.contracts.scrape_options import ScrapeOptions
from src.services.file_lock import file_lock
from src.services.scraping_service import run_scraping
from src.services.summarization_service import build_openai_summarizer
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
            scrapers=_build_target_scrapers(args),
            options=options,
            google_chat_webhook_url=None,
            summarizer=summarizer,
            on_summary_progress=lambda message: print(message, flush=True),
        )
        print(result)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="등록된 스크래퍼를 실행해 파일 저장소에 반영한다.")
    parser.add_argument("--start-date", help="수집 시작 등록일. 예: 2026-06-11")
    parser.add_argument("--end-date", help="수집 종료 등록일. 기본값: start-date 또는 오늘")
    parser.add_argument("--max-pages", type=int, help="각 사이트에서 조회할 최대 페이지 수. 긴 백필에서는 크게 지정한다.")
    parser.add_argument(
        "--source",
        action="append",
        help="특정 source만 수집한다. 여러 번 지정하거나 콤마로 구분 가능. 예: --source nipa --source nia",
    )
    return parser.parse_args()


def _build_scrape_options(args: argparse.Namespace, today: date) -> ScrapeOptions:
    if not args.start_date and not args.end_date:
        return ScrapeOptions.daily(today)

    start_date = date.fromisoformat(args.start_date) if args.start_date else today
    end_date = date.fromisoformat(args.end_date) if args.end_date else start_date
    if end_date < start_date:
        raise ValueError("--end-date는 --start-date보다 빠를 수 없습니다.")

    return ScrapeOptions.backfill(start_date=start_date, end_date=end_date)


def _build_target_scrapers(args: argparse.Namespace):
    scrapers = build_scrapers(max_pages=args.max_pages) if args.max_pages else SCRAPERS
    requested_sources = _parse_sources(args.source)
    if not requested_sources:
        return scrapers

    unknown_sources = sorted(source for source in requested_sources if source not in scrapers)
    if unknown_sources:
        available_sources = ", ".join(sorted(scrapers))
        raise ValueError(
            f"알 수 없는 source입니다: {', '.join(unknown_sources)}. "
            f"사용 가능 source: {available_sources}"
        )

    return {
        source: scraper
        for source, scraper in scrapers.items()
        if source in requested_sources
    }


def _parse_sources(values: list[str] | None) -> set[str]:
    if not values:
        return set()

    sources: set[str] = set()
    for value in values:
        sources.update(
            source.strip()
            for source in value.split(",")
            if source.strip()
        )
    return sources


if __name__ == "__main__":
    main()
