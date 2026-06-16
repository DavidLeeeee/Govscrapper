from __future__ import annotations

import json
from typing import Any

import requests

from src.contracts.notice import Notice


class OpenAIDeepAnalyzer:
    def __init__(
        self,
        api_key: str,
        model: str,
        max_output_tokens: int = 1600,
        timeout: int = 60,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.max_output_tokens = max_output_tokens
        self.timeout = timeout

    def analyze(self, notice: Notice, material: dict[str, Any]) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "input": [
                {
                    "role": "developer",
                    "content": (
                        "너는 정부지원사업/RFP 문서를 개발자와 기술기획자가 빠르게 판단할 수 있게 분석하는 전문가다. "
                        "단순 행정 요약보다 사업 추진 목표, 배경, 필요성, 실제 요구사항, 구현해야 할 기능, 개발 포인트를 우선한다. "
                        "금액은 핵심이 아니며, 개발자가 참여/검토 여부를 판단하는 데 필요한 내용 중심으로 정리한다. "
                        "응답은 반드시 JSON 스키마를 따른다."
                    ),
                },
                {"role": "user", "content": _build_prompt(notice, material)},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "notice_deep_analysis",
                    "schema": {
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
                    },
                    "strict": True,
                }
            },
            "reasoning": {"effort": "minimal"},
            "max_output_tokens": self.max_output_tokens,
        }
        response = requests.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return _normalize_analysis(_parse_response(response.json()))


def _build_prompt(notice: Notice, material: dict[str, Any]) -> str:
    lines = [
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
                str(file.get("text") or "")[:14000],
                "",
            ]
        )

    if not material.get("files"):
        lines.append("첨부파일 텍스트 없음")

    return "\n".join(lines)[:50000]


def _parse_response(data: dict[str, Any]) -> dict[str, Any]:
    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return json.loads(output_text)

    for output in data.get("output", []):
        if not isinstance(output, dict):
            continue
        for content in output.get("content", []):
            if not isinstance(content, dict):
                continue
            parsed = content.get("parsed")
            if isinstance(parsed, dict):
                return parsed
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                return json.loads(text)

    raise ValueError("OpenAI deep analysis response did not include output text")


def _normalize_analysis(data: dict[str, Any]) -> dict[str, Any]:
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
