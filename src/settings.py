from functools import lru_cache
import os
from pathlib import Path
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    """애플리케이션 전역 설정.

    외부 의존성을 늘리지 않고 환경 변수에서 필요한 설정만 읽는다.
    """

    port: int = 8000
    data_dir: Path = Path("data")
    runtime_dir: Path = Path("runtime")
    google_chat_webhook_url: str | None = None
    site_url: str | None = None
    no_deadline_expire_days: int = 60
    openai_api_key: str | None = None
    openai_summary_model: str = "gpt-5-nano"
    openai_trend_model: str = "gpt-5.4-mini"
    summarize_notices: bool = False
    summary_max_detail_chars: int = 4000
    summary_max_output_tokens: int = 700


@lru_cache
def get_settings() -> Settings:
    """Settings 싱글톤 인스턴스를 반환한다."""
    return Settings(
        port=int(os.getenv("PORT", "8000")),
        data_dir=Path(os.getenv("DATA_DIR", "data")),
        runtime_dir=Path(os.getenv("RUNTIME_DIR", "runtime")),
        google_chat_webhook_url=os.getenv("CHAT_API_URL") or os.getenv("GOOGLE_CHAT_WEBHOOK_URL"),
        site_url=os.getenv("SITE_URL") or None,
        no_deadline_expire_days=int(os.getenv("NO_DEADLINE_EXPIRE_DAYS", "60")),
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        openai_summary_model=os.getenv("OPENAI_SUMMARY_MODEL", "gpt-5-nano"),
        openai_trend_model=os.getenv("OPENAI_TREND_MODEL", "gpt-5.4-mini"),
        summarize_notices=_read_bool(os.getenv("SUMMARIZE_NOTICES")),
        summary_max_detail_chars=int(os.getenv("SUMMARY_MAX_DETAIL_CHARS", "4000")),
        summary_max_output_tokens=int(os.getenv("SUMMARY_MAX_OUTPUT_TOKENS", "700")),
    )


def _read_bool(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}
