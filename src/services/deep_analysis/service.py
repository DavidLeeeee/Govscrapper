from __future__ import annotations

from pathlib import Path
from typing import Any

from src.contracts.notice import Notice
from src.services.deep_analysis.attachment_discovery import discover_notice_materials
from src.services.deep_analysis.file_fetcher import fetch_attachment
from src.services.deep_analysis.openai_deep_analyzer import OpenAIDeepAnalyzer
from src.services.deep_analysis.storage import mark_notice_analysis_completed, read_analysis, write_analysis
from src.services.deep_analysis.text_extractors import extract_file_text


def get_analysis(data_dir: Path, notice_key: str) -> dict[str, Any] | None:
    return read_analysis(data_dir, notice_key)


def analyze_notice(
    data_dir: Path,
    notice: Notice,
    analyzer: OpenAIDeepAnalyzer,
    max_files: int = 5,
) -> dict[str, Any]:
    cached = read_analysis(data_dir, notice)
    if cached is not None:
        mark_notice_analysis_completed(data_dir, notice)
        return cached

    materials = discover_notice_materials(notice)
    files = []
    for attachment in list(materials.get("attachments", []))[:max_files]:
        if not isinstance(attachment, dict):
            continue
        try:
            fetched = fetch_attachment(attachment)
            files.append(extract_file_text(fetched))
        except Exception as exc:
            files.append(
                {
                    "name": str(attachment.get("name") or attachment.get("url") or "첨부파일"),
                    "url": str(attachment.get("url") or ""),
                    "content_type": "",
                    "status": "failed",
                    "text": "",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    analysis_input = {
        "detail_text": materials.get("detail_text") or "",
        "attachments": materials.get("attachments") or [],
        "files": files,
    }
    analysis = analyzer.analyze(notice, analysis_input)
    stored = write_analysis(
        data_dir,
        notice,
        {
            "status": "completed",
            "files": [
                {
                    "name": file.get("name"),
                    "url": file.get("url"),
                    "status": file.get("status"),
                    "error": file.get("error"),
                }
                for file in files
            ],
            **analysis,
        },
    )
    mark_notice_analysis_completed(data_dir, notice)
    return stored
