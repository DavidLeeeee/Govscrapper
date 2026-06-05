from src.server import start_app
from src.settings import get_settings

app = start_app()

if __name__ == "__main__":
    import uvicorn

    settings = get_settings()

    uvicorn.run(app=app, host="0.0.0.0", port=settings.port)