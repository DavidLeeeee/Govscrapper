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
    no_deadline_expire_days: int = 30
    openai_api_key: str | None = None
    openai_summary_model: str = "gpt-5-nano"
    openai_trend_model: str = "gpt-5.4-mini"
    openai_analysis_model: str = "gpt-5.4-mini"
    claude_analysis_model: str | None = None
    analysis_provider: str = "openai"
    analysis_max_file_chars: int = 14000
    analysis_max_prompt_chars: int = 50000
    analysis_max_output_tokens: int = 1600
    analysis_reasoning_effort: str = "low"
    summarize_notices: bool = False
    summary_max_detail_chars: int = 4000
    summary_max_output_tokens: int = 700


@lru_cache
def get_settings() -> Settings:
    """Settings 싱글톤 인스턴스를 반환한다."""
    analysis_provider = os.getenv("ANALYSIS_PROVIDER", "openai").strip().lower()
    default_file_chars = "50000" if analysis_provider == "claude" else "14000"
    default_prompt_chars = "180000" if analysis_provider == "claude" else "50000"
    default_output_tokens = "4000" if analysis_provider == "claude" else "1600"
    return Settings(
        port=int(os.getenv("PORT", "8000")),
        data_dir=Path(os.getenv("DATA_DIR", "data")),
        runtime_dir=Path(os.getenv("RUNTIME_DIR", "runtime")),
        google_chat_webhook_url=_read_optional_str("CHAT_API_URL") or _read_optional_str("GOOGLE_CHAT_WEBHOOK_URL"),
        site_url=_read_optional_str("SITE_URL"),
        no_deadline_expire_days=int(os.getenv("NO_DEADLINE_EXPIRE_DAYS", "30")),
        openai_api_key=_read_optional_str("OPENAI_API_KEY"),
        openai_summary_model=_read_str("OPENAI_SUMMARY_MODEL", "gpt-5-nano"),
        openai_trend_model=_read_str("OPENAI_TREND_MODEL", "gpt-5.4-mini"),
        openai_analysis_model=_read_str("OPENAI_ANALYSIS_MODEL", _read_str("OPENAI_TREND_MODEL", "gpt-5.4-mini")),
        claude_analysis_model=_read_optional_str("CLAUDE_ANALYSIS_MODEL"),
        analysis_provider=analysis_provider,
        analysis_max_file_chars=int(os.getenv("ANALYSIS_MAX_FILE_CHARS", default_file_chars)),
        analysis_max_prompt_chars=int(os.getenv("ANALYSIS_MAX_PROMPT_CHARS", default_prompt_chars)),
        analysis_max_output_tokens=int(os.getenv("ANALYSIS_MAX_OUTPUT_TOKENS", default_output_tokens)),
        analysis_reasoning_effort=_read_str("ANALYSIS_REASONING_EFFORT", "low"),
        summarize_notices=_read_bool(os.getenv("SUMMARIZE_NOTICES")),
        summary_max_detail_chars=int(os.getenv("SUMMARY_MAX_DETAIL_CHARS", "4000")),
        summary_max_output_tokens=int(os.getenv("SUMMARY_MAX_OUTPUT_TOKENS", "700")),
    )


def _read_bool(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _read_str(name: str, default: str) -> str:
    return str(os.getenv(name) or default).strip()


def _read_optional_str(name: str) -> str | None:
    value = str(os.getenv(name) or "").strip()
    return value or None
