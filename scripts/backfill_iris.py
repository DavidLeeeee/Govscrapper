import argparse
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.contracts.scrape_options import ScrapeOptions
from src.scrapers._iris import IrisBtinSituScraper
from src.services.file_lock import file_lock
from src.services.scraping_service import run_scraping
from src.settings import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="IRIS 공고를 넓은 날짜 범위로 수집해 파일 저장소에 반영한다.")
    parser.add_argument("--start-date", required=True, help="수집 시작일. 예: 2026-05-01")
    parser.add_argument("--end-date", default=date.today().isoformat(), help="수집 종료일. 기본값: 오늘")
    parser.add_argument("--max-pages", type=int, default=5, help="조회할 최대 페이지 수")
    args = parser.parse_args()

    settings = get_settings()
    lock_path = settings.runtime_dir / "locks" / "iris_backfill.lock"
    scraper = IrisBtinSituScraper(max_pages=args.max_pages)
    options = ScrapeOptions.backfill(
        start_date=date.fromisoformat(args.start_date),
        end_date=date.fromisoformat(args.end_date),
    )

    with file_lock(lock_path):
        result = run_scraping(
            data_dir=settings.data_dir,
            scrapers={scraper.target.source_name: scraper.scrape},
            options=options,
            google_chat_webhook_url=None,
        )
        print(result)


if __name__ == "__main__":
    main()
