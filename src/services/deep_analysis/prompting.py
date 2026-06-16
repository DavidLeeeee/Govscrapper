from __future__ import annotations

import json
from typing import Any

from src.contracts.notice import Notice


SYSTEM_PROMPT = (
    "너는 정부지원사업/RFP 문서를 개발자와 기술기획자가 빠르게 판단할 수 있게 분석하는 전문가다. "
    "단순 행정 요약보다 사업 추진 목표, 배경, 필요성, 실제 요구사항, 구현해야 할 기능, 개발 포인트를 우선한다. "
    "금액은 핵심이 아니며, 개발자가 참여/검토 여부를 판단하는 데 필요한 내용 중심으로 정리한다. "
    "응답은 반드시 JSON만 출력한다."
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
        "JSON 필드: business_goal, business_background, business_necessity, main_development, major_requirements, implementation_points, technical_keywords, recommended_action",
        "",
        f"공고 제목: {notice.get('title')}",
        f"출처: {notice.get('source')}",
        f"등록일: {notice.get('posted_at')}",
        f"마감일: {notice.get('deadline') or notice.get('ai_deadline') or '확인 필요'}",
        f"원문 URL: {notice.get('url')}",
        "",
        "[첨부파일 텍스트]",
    ]

    for index, file in enumerate(material.get("files", [])[:5], start=1):
        lines.extend(
            [
                f"{index}. 파일명: {file.get('name')}",
                f"URL: {file.get('url')}",
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
    return json.loads(clean_text)


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
