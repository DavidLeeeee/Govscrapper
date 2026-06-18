from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Any

from src.contracts.notice import Notice
from src.services.deep_analysis.attachment_discovery import discover_notice_materials
from src.services.deep_analysis.contracts import DeepAnalyzer
from src.services.deep_analysis.file_fetcher import FetchedFile
from src.services.deep_analysis.file_fetcher import fetch_attachment
from src.services.deep_analysis.storage import analysis_key, mark_notice_analysis_completed, read_analysis, write_analysis
from src.services.deep_analysis.text_extractors import extract_file_text

ANALYSIS_VERSION = 2
OPENAI_INPUT_FILE_MAX_BYTES = 20 * 1024 * 1024


def get_analysis(data_dir: Path, notice_key: str) -> dict[str, Any] | None:
    return read_analysis(data_dir, notice_key)


def analyze_notice(
    data_dir: Path,
    notice: Notice,
    analyzer: DeepAnalyzer,
    fallback_analyzer: DeepAnalyzer | None = None,
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
            parsed = extract_file_text(fetched)
            local_file = _save_local_hwp_file(data_dir, notice, fetched)
            if local_file:
                parsed.update(local_file)
                if parsed.get("status") == "unsupported":
                    parsed["status"] = "local_file"
                    parsed["error"] = "HWP 원본을 Claude 로컬 파일 분석용으로 저장했습니다."
            attachable = _build_openai_input_file(fetched)
            if attachable:
                parsed.update(attachable)
                if parsed.get("status") == "unsupported":
                    parsed["status"] = "attached"
                    parsed["error"] = "텍스트 추출 대신 원본 파일을 AI 요청에 첨부합니다."
            files.append(parsed)
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
        "attachments": materials.get("attachments") or [],
        "files": files,
    }
    selected_analyzer = fallback_analyzer if fallback_analyzer and _needs_hwp_fallback(files) else analyzer
    analysis = selected_analyzer.analyze(notice, analysis_input)
    if selected_analyzer is fallback_analyzer:
        analysis["analysis_fallback"] = {
            "reason": "hwp_without_extracted_text",
            "provider": "openai",
        }
    stored = write_analysis(
        data_dir,
        notice,
        {
            "status": "completed",
            "analysis_version": ANALYSIS_VERSION,
            "files": [
                {
                    "name": file.get("name"),
                    "url": file.get("url"),
                    "status": file.get("status"),
                    "error": file.get("error"),
                    "attached": bool(file.get("input_file_data")),
                    "local_file": bool(file.get("local_path")),
                }
                for file in files
            ],
            **analysis,
        },
    )
    mark_notice_analysis_completed(data_dir, notice)
    return stored


def _needs_hwp_fallback(files: list[dict[str, Any]]) -> bool:
    # OpenAI Responses file input does not support legacy .hwp binary files.
    # Keep this hook for future converted HWP text/PDF support, but do not
    # fallback on raw HWP-only failures because it only produces a 400 error.
    return False


def _has_unparsed_hwp(files: list[dict[str, Any]]) -> bool:
    for file in files:
        name = str(file.get("name") or "").lower()
        content_type = str(file.get("content_type") or "").lower()
        is_hwp = name.endswith(".hwp") or ("hwp" in content_type and "hwpx" not in content_type)
        if is_hwp and not str(file.get("text") or "").strip():
            return True
    return False


def _build_openai_input_file(file: FetchedFile) -> dict[str, str] | None:
    extension = Path(file.name).suffix.lower()
    content_type = file.content_type.lower()
    mime_type = _input_file_mime_type(extension, content_type)
    if not mime_type:
        return None
    if not file.content or len(file.content) > OPENAI_INPUT_FILE_MAX_BYTES:
        return None

    encoded = base64.b64encode(file.content).decode("ascii")
    return {
        "input_file_name": file.name or f"attachment{extension or ''}",
        "input_file_data": f"data:{mime_type};base64,{encoded}",
    }


def _input_file_mime_type(extension: str, content_type: str) -> str | None:
    if extension == ".pdf" or "pdf" in content_type:
        return "application/pdf"
    if extension == ".hwpx" or "hwpx" in content_type:
        return "application/vnd.hancom.hwpx"
    return None


def _save_local_hwp_file(data_dir: Path, notice: Notice, file: FetchedFile) -> dict[str, str] | None:
    extension = Path(file.name).suffix.lower()
    content_type = file.content_type.lower()
    if extension != ".hwp" and ("hwp" not in content_type or "hwpx" in content_type):
        return None
    if not file.content:
        return None

    directory = data_dir / "analysis_files" / analysis_key(notice)
    directory.mkdir(parents=True, exist_ok=True)
    filename = _safe_filename(file.name or "attachment.hwp")
    if not filename.lower().endswith(".hwp"):
        filename = f"{filename}.hwp"
    path = directory / filename
    path.write_bytes(file.content)
    return {"local_path": str(path.resolve())}


def _safe_filename(value: str) -> str:
    name = Path(value).name.strip() or "attachment.hwp"
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)[:180]
