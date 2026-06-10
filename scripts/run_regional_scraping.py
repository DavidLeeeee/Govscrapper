import sys
from argparse import ArgumentParser
from datetime import date, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.contracts.scrape_options import ScrapeOptions
from src.scrapers._bizinfo_region import BizInfoRegionScraper
from src.services.file_lock import file_lock
from src.services.scraping_service import run_scraping
from src.settings import get_settings


def main() -> None:
    args = _parse_args()
    settings = get_settings()
    lock_path = settings.runtime_dir / "locks" / "regional_scraping.lock"

    with file_lock(lock_path):
        today = datetime.now().date()
        start_date = date.fromisoformat(args.start_date) if args.start_date else today
        end_date = date.fromisoformat(args.end_date) if args.end_date else today
        scraper = BizInfoRegionScraper(max_pages=args.max_pages, with_detail=args.with_detail)
        result = run_scraping(
            data_dir=settings.data_dir / "regional",
            scrapers={scraper.source_name: scraper.scrape},
            options=ScrapeOptions.backfill(start_date, end_date),
            google_chat_webhook_url=None,
            summarizer=None,
        )
        print(result)


def _parse_args():
    parser = ArgumentParser(description="지역공고를 data/regional 아래로 수집합니다.")
    parser.add_argument("--start-date", help="수집 시작 등록일. 예: 2026-06-01")
    parser.add_argument("--end-date", help="수집 종료 등록일. 기본값은 오늘")
    parser.add_argument("--max-pages", type=int, default=5)
    parser.add_argument("--with-detail", action="store_true", help="상세 페이지까지 수집합니다.")
    return parser.parse_args()


if __name__ == "__main__":
    main()
