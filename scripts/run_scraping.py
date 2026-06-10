import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.scrapers.registry import SCRAPERS
from src.contracts.scrape_options import ScrapeOptions
from src.services.file_lock import file_lock
from src.services.scraping_service import run_scraping
from src.services.summarization_service import build_openai_summarizer
from src.settings import get_settings


def main() -> None:
    settings = get_settings()
    lock_path = settings.runtime_dir / "locks" / "scraping.lock"

    with file_lock(lock_path):
        today = datetime.now().date()
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
            options=ScrapeOptions.daily(today),
            google_chat_webhook_url=settings.google_chat_webhook_url,
            summarizer=summarizer,
            on_summary_progress=lambda message: print(message, flush=True),
        )
        print(result)


if __name__ == "__main__":
    main()
