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
    no_deadline_expire_days: int = 60


@lru_cache
def get_settings() -> Settings:
    """Settings 싱글톤 인스턴스를 반환한다."""
    return Settings(
        port=int(os.getenv("PORT", "8000")),
        data_dir=Path(os.getenv("DATA_DIR", "data")),
        runtime_dir=Path(os.getenv("RUNTIME_DIR", "runtime")),
        google_chat_webhook_url=os.getenv("GOOGLE_CHAT_WEBHOOK_URL"),
        no_deadline_expire_days=int(os.getenv("NO_DEADLINE_EXPIRE_DAYS", "60")),
    )
