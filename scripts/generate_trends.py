import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.file_lock import file_lock
from src.services.trends.openai_trend_service import OpenAITrendAnalyzer
from src.services.trends.trend_service import generate_and_store_trends
from src.settings import get_settings


def main() -> None:
    settings = get_settings()
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY가 .env에 설정되어 있지 않습니다.")

    analyzer = OpenAITrendAnalyzer(api_key=settings.openai_api_key, model=settings.openai_trend_model)
    lock_path = settings.runtime_dir / "locks" / "generate_trends.lock"
    with file_lock(lock_path):
        report = generate_and_store_trends(settings.data_dir, analyzer)

    print(
        {
            "generated_at": report["generated_at"],
            "windows": {
                key: {
                    "notice_count": value["notice_count"],
                    "trend_count": len(value["trend_notice_words"]),
                    "emerging_count": len(value["developer_emerging_words"]),
                }
                for key, value in report["windows"].items()
            },
        }
    )


if __name__ == "__main__":
    main()
