import argparse
import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.contracts.scrape_options import ScrapeOptions
from src.scrapers.registry import SCRAPER_INSTANCES
from src.services.file_lock import file_lock
from src.services.scraping_service import run_scraping
from src.services.summarization_service import build_openai_summarizer
from src.settings import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="등록된 모든 스크래퍼를 넓은 날짜 범위로 수집해 파일 저장소에 반영한다.")
    parser.add_argument("--start-date", default="2026-05-20", help="수집 시작일. 기본값: 2026-06-01")
    parser.add_argument("--end-date", default=date.today().isoformat(), help="수집 종료일. 기본값: 오늘")
    args = parser.parse_args()

    settings = get_settings()
    lock_path = settings.runtime_dir / "locks" / "backfill_all.lock"
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

    options = ScrapeOptions.backfill(
        start_date=date.fromisoformat(args.start_date),
        end_date=date.fromisoformat(args.end_date),
    )
    scrapers = {
        scraper.target.source_name: scraper.scrape
        for scraper in SCRAPER_INSTANCES
    }

    with file_lock(lock_path):
        result = run_scraping(
            data_dir=settings.data_dir,
            scrapers=scrapers,
            options=options,
            google_chat_webhook_url=None,
            summarizer=summarizer,
            on_summary_progress=lambda message: print(message, flush=True),
        )
        print(result)


if __name__ == "__main__":
    main()
