from __future__ import annotations

import re
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Literal
from xml.etree import ElementTree

from src.services.deep_analysis.file_fetcher import FetchedFile
from src.services.detail_fetch_service import extract_readable_text


ParsedStatus = Literal["parsed", "unsupported", "failed"]


def extract_file_text(file: FetchedFile, max_chars: int = 16000) -> dict[str, str]:
    try:
        text = _extract_text(file)
        if not text.strip():
            return _result(file, "unsupported", "", "텍스트를 추출할 수 없는 파일 형식입니다.")
        return _result(file, "parsed", text[:max_chars], "")
    except Exception as exc:
        return _result(file, "failed", "", f"{type(exc).__name__}: {exc}")


def _extract_text(file: FetchedFile) -> str:
    extension = Path(file.name).suffix.lower()
    content_type = file.content_type.lower()

    if extension in {".txt", ".csv", ".md"} or "text/plain" in content_type:
        return _decode_text(file.content)

    if extension in {".html", ".htm"} or "html" in content_type:
        return extract_readable_text(_decode_text(file.content))

    if extension == ".docx":
        return _extract_docx_text(file.content)

    if extension == ".hwpx":
        return _extract_hwpx_text(file.content)

    return ""


def _extract_docx_text(content: bytes) -> str:
    with zipfile.ZipFile(BytesIO(content)) as archive:
        names = [name for name in archive.namelist() if name.startswith("word/") and name.endswith(".xml")]
        texts: list[str] = []
        for name in names:
            texts.extend(_xml_texts(archive.read(name)))
    return _clean_text("\n".join(texts))


def _extract_hwpx_text(content: bytes) -> str:
    with zipfile.ZipFile(BytesIO(content)) as archive:
        names = [name for name in archive.namelist() if name.endswith(".xml")]
        texts: list[str] = []
        for name in names:
            if not (name.startswith("Contents/") or name.startswith("Preview/") or "section" in name.lower()):
                continue
            texts.extend(_xml_texts(archive.read(name)))
    return _clean_text("\n".join(texts))


def _xml_texts(content: bytes) -> list[str]:
    root = ElementTree.fromstring(content)
    return [text.strip() for text in root.itertext() if text and text.strip()]


def _decode_text(content: bytes) -> str:
    for encoding in ("utf-8", "cp949", "euc-kr"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="ignore")


def _clean_text(value: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in value.splitlines()]
    return "\n".join(line for line in lines if line)


def _result(file: FetchedFile, status: ParsedStatus, text: str, error: str) -> dict[str, str]:
    return {
        "name": file.name,
        "url": file.url,
        "content_type": file.content_type,
        "status": status,
        "text": text,
        "error": error,
    }
