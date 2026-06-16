from __future__ import annotations

import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from src.contracts.notice import Notice
from src.services.detail_fetch_service import DEFAULT_HEADERS, extract_readable_text


FILE_HINT_PATTERN = re.compile(
    r"download|file|attach|atch|첨부|다운로드|\.(pdf|hwp|hwpx|docx?|xlsx?|pptx?|zip|txt)(\?|$)",
    re.I,
)


def discover_notice_materials(notice: Notice, timeout: int = 15) -> dict[str, object]:
    detail_url = str(notice.get("url") or "").strip()
    html = ""
    detail_text = ""
    attachments = _notice_attachments(notice)

    if detail_url:
        response = requests.get(detail_url, headers=DEFAULT_HEADERS, timeout=timeout)
        response.raise_for_status()
        response.encoding = response.encoding or response.apparent_encoding
        content_type = response.headers.get("Content-Type", "").lower()
        if "html" in content_type or "text" in content_type:
            html = response.text
            detail_text = extract_readable_text(html)
            attachments = _merge_attachments(attachments, _extract_attachments(html, detail_url))

    return {
        "detail_text": detail_text,
        "attachments": attachments,
    }


def _notice_attachments(notice: Notice) -> list[dict[str, str]]:
    attachments: list[dict[str, str]] = []
    for item in notice.get("attachments", []) or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("title") or item.get("filename") or "").strip()
        url = str(item.get("url") or item.get("href") or "").strip()
        if url:
            attachments.append({"name": name or url, "url": url})
    return attachments


def _extract_attachments(html: str, base_url: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    attachments: list[dict[str, str]] = []

    for link in soup.select("a[href]"):
        href = str(link.get("href") or "").strip()
        text = link.get_text(" ", strip=True)
        candidate = f"{text} {href}"
        if not href or not FILE_HINT_PATTERN.search(candidate):
            continue
        attachments.append(
            {
                "name": text or href,
                "url": urljoin(base_url, href),
            }
        )

    return attachments


def _merge_attachments(*groups: list[dict[str, str]]) -> list[dict[str, str]]:
    merged: list[dict[str, str]] = []
    seen: set[str] = set()
    for group in groups:
        for item in group:
            url = str(item.get("url") or "").strip()
            if not url or url in seen:
                continue
            seen.add(url)
            merged.append({"name": str(item.get("name") or url).strip(), "url": url})
    return merged
