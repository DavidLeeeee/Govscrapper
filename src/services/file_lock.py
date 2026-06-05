from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator

from src.domain.exception import ValidationError


@contextmanager
def file_lock(lock_path: Path, stale_after: timedelta = timedelta(hours=2)) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now()

    if lock_path.exists():
        created_at = datetime.fromtimestamp(lock_path.stat().st_mtime)
        if now - created_at <= stale_after:
            raise ValidationError(f"작업이 이미 실행 중입니다: {lock_path}")
        lock_path.unlink()

    lock_path.write_text(now.isoformat(), encoding="utf-8")
    try:
        yield
    finally:
        if lock_path.exists():
            lock_path.unlink()
