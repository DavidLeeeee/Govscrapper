from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qsl, urlparse

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
    method = str(attachment.get("method") or "GET").strip().upper()
    headers = {**DEFAULT_HEADERS}
    referer = str(attachment.get("referer") or "").strip()
    if referer:
        headers["Referer"] = referer

    data = _parse_attachment_data(str(attachment.get("data") or ""))
    if method == "POST":
        response = requests.post(url, data=data, headers=headers, timeout=timeout)
    else:
        response = requests.get(url, params=data or None, headers=headers, timeout=timeout)
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


def _parse_attachment_data(value: str) -> dict[str, str]:
    if not value:
        return {}
    return {key: item_value for key, item_value in parse_qsl(value, keep_blank_values=True)}
