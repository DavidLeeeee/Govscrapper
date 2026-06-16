from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import requests

from src.services.detail_fetch_service import DEFAULT_HEADERS


@dataclass(frozen=True)
class FetchedFile:
    name: str
    url: str
    content_type: str
    content: bytes


def fetch_attachment(attachment: dict[str, str], timeout: int = 20, max_bytes: int = 20 * 1024 * 1024) -> FetchedFile:
    url = str(attachment.get("url") or "").strip()
    name = str(attachment.get("name") or "").strip() or _filename_from_url(url)
    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    response.raise_for_status()

    content = response.content[: max_bytes + 1]
    if len(content) > max_bytes:
        raise ValueError(f"파일 크기가 제한을 초과했습니다: {name}")

    return FetchedFile(
        name=name,
        url=url,
        content_type=response.headers.get("Content-Type", ""),
        content=content,
    )


def _filename_from_url(url: str) -> str:
    path = urlparse(url).path
    name = Path(path).name
    return name or url
