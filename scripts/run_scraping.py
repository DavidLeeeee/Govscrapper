import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.scrapers.registry import SCRAPERS
from src.services.file_lock import file_lock
from src.services.scraping_service import run_scraping
from src.settings import get_settings


def main() -> None:
    settings = get_settings()
    lock_path = settings.runtime_dir / "locks" / "scraping.lock"

    with file_lock(lock_path):
        result = run_scraping(
            data_dir=settings.data_dir,
            scrapers=SCRAPERS,
            google_chat_webhook_url=settings.google_chat_webhook_url,
        )
        print(result)


if __name__ == "__main__":
    main()
