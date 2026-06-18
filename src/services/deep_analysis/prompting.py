from __future__ import annotations

import json
from typing import Any

from src.contracts.notice import Notice


SYSTEM_PROMPT = (
    "너는 정부지원사업/RFP 문서를 개발자와 기술기획자가 빠르게 판단할 수 있게 분석하는 전문가다. "
    "단순 행정 요약보다 사업 추진 목표, 배경, 필요성, 실제 요구사항, 구현해야 할 기능, 개발 포인트를 우선한다. "
    "금액은 핵심이 아니며, 개발자가 참여/검토 여부를 판단하는 데 필요한 내용 중심으로 정리한다. "
    "응답은 반드시 JSON 객체 하나만 출력한다. 첫 글자는 {, 마지막 글자는 } 이어야 한다. "
    "첨부파일 접근에 실패했거나 근거가 부족해도 설명문을 따로 쓰지 말고, 각 필드에 확인 불가 사유를 넣어 JSON 스키마를 채운다."
)

ANALYSIS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "business_goal": {"type": "string"},
        "business_background": {"type": "string"},
        "business_necessity": {"type": "string"},
        "main_development": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
        "major_requirements": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
        "implementation_points": {"type": "array", "items": {"type": "string"}, "maxItems": 8},
        "technical_keywords": {"type": "array", "items": {"type": "string"}, "maxItems": 12},
        "recommended_action": {"type": "string"},
    },
    "required": [
        "business_goal",
        "business_background",
        "business_necessity",
        "main_development",
        "major_requirements",
        "implementation_points",
        "technical_keywords",
        "recommended_action",
    ],
}


def build_deep_analysis_prompt(
    notice: Notice,
    material: dict[str, Any],
    max_file_chars: int,
    max_prompt_chars: int,
) -> str:
    lines = [
        "다음 공고의 첨부파일만 근거로 심층 분석해라.",
        "상세 페이지 본문은 분석 근거로 사용하지 않는다.",
        "원본 첨부파일이 함께 제공된 경우, 아래의 추출 텍스트보다 원본 첨부파일 내용을 우선 근거로 사용해라.",
        "분석할 수 있는 첨부파일이 없거나 다운로드가 실패해도 반드시 JSON 객체만 반환해라.",
        "외부 URL 접속, WebFetch, WebSearch, 브라우징 도구 사용을 요청하거나 시도하지 마라.",
        "JSON 필드: business_goal, business_background, business_necessity, main_development, major_requirements, implementation_points, technical_keywords, recommended_action",
        "",
        f"공고 제목: {notice.get('title')}",
        f"출처: {notice.get('source')}",
        f"등록일: {notice.get('posted_at')}",
        f"마감일: {notice.get('deadline') or notice.get('ai_deadline') or '확인 필요'}",
        "",
        "[첨부파일 텍스트]",
    ]

    for index, file in enumerate(material.get("files", [])[:5], start=1):
        lines.extend(
            [
                f"{index}. 파일명: {file.get('name')}",
                f"상태: {file.get('status')}",
                f"오류: {file.get('error') or ''}",
                str(file.get("text") or "")[:max_file_chars],
                "",
            ]
        )

    if not material.get("files"):
        lines.append("첨부파일 텍스트 없음")

    return "\n".join(lines)[:max_prompt_chars]


def parse_analysis_json(text: str) -> dict[str, Any]:
    clean_text = text.strip()
    if clean_text.startswith("```"):
        clean_text = clean_text.strip("`")
        if clean_text.lower().startswith("json"):
            clean_text = clean_text[4:].strip()
    try:
        return json.loads(clean_text)
    except json.JSONDecodeError as exc:
        extracted = _extract_json_object(clean_text)
        if extracted:
            try:
                return json.loads(extracted)
            except json.JSONDecodeError:
                pass
        preview = clean_text[:500] or "<empty>"
        raise ValueError(f"AI analysis response was not valid JSON: {preview}") from exc


def normalize_analysis(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "business_goal": str(data.get("business_goal") or "").strip(),
        "business_background": str(data.get("business_background") or "").strip(),
        "business_necessity": str(data.get("business_necessity") or "").strip(),
        "main_development": _string_list(data.get("main_development")),
        "major_requirements": _string_list(data.get("major_requirements")),
        "implementation_points": _string_list(data.get("implementation_points")),
        "technical_keywords": _string_list(data.get("technical_keywords")),
        "recommended_action": str(data.get("recommended_action") or "").strip(),
    }


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _extract_json_object(text: str) -> str | None:
    start = text.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if escaped:
            escaped = False
            continue
        if char == "\\":
            escaped = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]

    return None
