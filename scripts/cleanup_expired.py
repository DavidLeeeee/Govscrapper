import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.cleanup_service import cleanup_expired_notices
from src.services.file_lock import file_lock
from src.settings import get_settings


def main() -> None:
    settings = get_settings()
    lock_path = settings.runtime_dir / "locks" / "cleanup.lock"

    with file_lock(lock_path):
        result = cleanup_expired_notices(settings.data_dir)
        print(result)


if __name__ == "__main__":
    main()
