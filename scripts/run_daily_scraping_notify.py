import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.contracts.notice import Notice
from src.contracts.scrape_options import ScrapeOptions
from src.scrapers._bizinfo_region import BizInfoRegionScraper
from src.scrapers.registry import SCRAPERS
from src.services.alarm_service import build_alarm_payload, read_alarm_payload, write_alarm_payload
from src.services.file_lock import file_lock
from src.services.marked_service import list_marked_notices
from src.services.notification_service import build_daily_scraping_message, send_google_chat_message
from src.services.scraping_service import run_scraping
from src.services.summarization_service import build_openai_summarizer
from src.settings import get_settings


def main() -> None:
    args = _parse_args()
    settings = get_settings()
    if not settings.google_chat_webhook_url:
        raise RuntimeError("CHAT_API_URL 또는 GOOGLE_CHAT_WEBHOOK_URL이 .env에 설정되어 있지 않습니다.")

    start_date, end_date = _resolve_date_range(args)
    options = ScrapeOptions.backfill(start_date=start_date, end_date=end_date)
    lock_path = settings.runtime_dir / "locks" / "daily_scraping_notify.lock"

    with file_lock(lock_path):
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

        general_result = run_scraping(
            data_dir=settings.data_dir,
            scrapers=SCRAPERS,
            options=options,
            google_chat_webhook_url=None,
            summarizer=summarizer,
            on_summary_progress=lambda message: print(message, flush=True),
            collect_scraped_notices=True,
        )

        regional_scraper = BizInfoRegionScraper(max_pages=args.regional_max_pages, with_detail=args.regional_with_detail)
        regional_result = run_scraping(
            data_dir=settings.data_dir / "regional",
            scrapers={regional_scraper.source_name: regional_scraper.scrape},
            options=options,
            google_chat_webhook_url=None,
            summarizer=None,
            collect_scraped_notices=True,
        )

        mark_records = list_marked_notices(settings.data_dir)
        alarm_payload = build_alarm_payload(
            start_date,
            end_date,
            _read_result_notices(general_result, "scraped_notices"),
            _read_result_notices(regional_result, "scraped_notices"),
            mark_records,
        )
        write_alarm_payload(settings.data_dir, alarm_payload)

        alarm_payload = read_alarm_payload(settings.data_dir)
        if alarm_payload is None:
            raise RuntimeError("알림 JSON을 읽지 못했습니다.")

        message = build_daily_scraping_message(
            alarm_payload["notices"],
            alarm_payload["regional_notices"],
            alarm_payload["new_mark_records"],
            total_mark_count=alarm_payload["total_mark_count"],
            site_url=settings.site_url,
        )
        send_google_chat_message(settings.google_chat_webhook_url, message)

        print(
            {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "general_new_count": general_result["new_count"],
                "regional_new_count": regional_result["new_count"],
                "alarm_notice_count": len(alarm_payload["notices"]),
                "alarm_regional_notice_count": len(alarm_payload["regional_notices"]),
                "new_mark_count": len(alarm_payload["new_mark_records"]),
                "total_mark_count": len(mark_records),
                "alarm_path": str(settings.data_dir / "alarm" / "latest.json"),
                "chat_notified": True,
            }
        )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="일반/지역 공고를 수집하고 Google Chat 알림을 한 번 전송합니다.")
    parser.add_argument("--start-date", help="수집 시작 등록일. 기본값: 어제")
    parser.add_argument("--end-date", help="수집 종료 등록일. 기본값: 오늘")
    parser.add_argument("--regional-max-pages", type=int, default=5)
    parser.add_argument("--regional-with-detail", action="store_true")
    return parser.parse_args()


def _resolve_date_range(args: argparse.Namespace) -> tuple[date, date]:
    today = datetime.now().date()
    start_date = date.fromisoformat(args.start_date) if args.start_date else today - timedelta(days=1)
    end_date = date.fromisoformat(args.end_date) if args.end_date else today
    if end_date < start_date:
        raise ValueError("--end-date는 --start-date보다 빠를 수 없습니다.")
    return start_date, end_date


def _read_result_notices(result: dict[str, object], key: str) -> list[Notice]:
    notices = result.get(key)
    return notices if isinstance(notices, list) else []


if __name__ == "__main__":
    main()
