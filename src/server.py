from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from src.api.errors import domain_error_handler
from src.api.routes.health import router as health_router
from src.api.routes.notices import router as notices_router
from src.domain.exception import DomainError
from src.settings import Settings, get_settings


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CLIENT_DIR = PROJECT_ROOT / "client"
CLIENT_STATIC_DIR = CLIENT_DIR / "static"
CLIENT_INDEX_PATH = CLIENT_DIR / "index.html"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """애플리케이션 lifespan 컨텍스트.

    - startup: Settings를 로드해 app.state에 저장한다.
    - shutdown: 추후 필요 시 리소스 정리를 추가한다.
    """

    settings: Settings = get_settings()
    app.state.settings = settings

    yield


def start_app() -> FastAPI:
    app = FastAPI(title="Government Business Scraper", lifespan=lifespan)

    # 공통 예외 핸들러 등록:
    # 서비스가 던지는 도메인 예외(DomainError)는 여기서 HTTP 응답으로 변환된다.
    app.add_exception_handler(DomainError, domain_error_handler)

    if CLIENT_STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=CLIENT_STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    async def client_index() -> FileResponse:
        return FileResponse(CLIENT_INDEX_PATH)

    # API 라우터 등록
    app.include_router(health_router, prefix="/api")
    app.include_router(notices_router, prefix="/api")

    return app
