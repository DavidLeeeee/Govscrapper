from __future__ import annotations

import json
from typing import Any

import requests

from src.contracts.notice import Notice
from src.services.trends.contracts import EmergingTrendItem, MonthlyTrendReport, TrendItem


class OpenAITrendAnalyzer:
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-5.4-mini",
        max_output_tokens: int = 1200,
        timeout: int = 45,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.max_output_tokens = max_output_tokens
        self.timeout = timeout

    def analyze_month(self, notices: list[Notice], month: str) -> MonthlyTrendReport:
        payload = {
            "model": self.model,
            "input": [
                {
                    "role": "developer",
                    "content": (
                        "너는 정부지원사업 공고 제목만 보고 해당 월의 기술 트렌드를 분석하는 전문가다. "
                        "재공고, 재공모, 지원, 사업, 공고, 용역, 위탁연구, 조달입찰공고처럼 행정 절차나 공고 형식을 뜻하는 단어는 핵심 키워드로 뽑지 않는다. "
                        "AI, 데이터, 보안, 클라우드, 블록체인, PQC, 양자, 반도체, 로봇, 바이오, 디지털트윈처럼 기술/산업의 실제 방향을 드러내는 단어를 우선한다. "
                        "빈도가 1~2회여도 PQC 같은 구체적이고 중요한 기술어는 developer_emerging_words 또는 trend_notice_words에 포함할 수 있다. "
                        "trend_notice_words의 count는 제목 목록에서 해당 키워드가 직접 언급되거나 명확히 같은 주제로 언급된 제목 수다. "
                        "응답은 반드시 JSON 스키마를 따른다."
                    ),
                },
                {"role": "user", "content": self._build_prompt(notices, month)},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "monthly_trend",
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "trend_notice_words": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "keyword": {"type": "string"},
                                        "count": {"type": "integer"},
                                        "reason": {"type": "string"},
                                    },
                                    "required": ["keyword", "count", "reason"],
                                },
                                "maxItems": 10,
                            },
                            "developer_emerging_words": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "additionalProperties": False,
                                    "properties": {
                                        "keyword": {"type": "string"},
                                        "reason": {"type": "string"},
                                    },
                                    "required": ["keyword", "reason"],
                                },
                                "maxItems": 8,
                            },
                        },
                        "required": ["trend_notice_words", "developer_emerging_words"],
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
        parsed = _parse_response(response.json())
        return {
            "month": month,
            "notice_count": len(notices),
            "trend_notice_words": parsed["trend_notice_words"],
            "developer_emerging_words": parsed["developer_emerging_words"],
        }

    def _build_prompt(self, notices: list[Notice], month: str) -> str:
        lines = [
            f"분석 대상 월: {month}",
            "목표: 이 달 공고 제목들이 보여주는 실질적 기술/산업 흐름을 요약한다.",
            "주의: 단순히 많이 반복되는 행정 단어가 아니라, 기술 방향을 드러내는 핵심어를 뽑는다.",
            "공고 제목 목록:",
        ]
        for index, notice in enumerate(notices[:260], start=1):
            title = str(notice.get("title") or "").strip()
            posted_at = str(notice.get("posted_at") or "").strip()
            source = str(notice.get("source") or "").strip()
            lines.append(f"{index}. [{posted_at}] ({source}) {title}")
        return "\n".join(lines)


def _parse_response(data: dict[str, Any]) -> dict[str, Any]:
    parsed = json.loads(_extract_response_text(data))
    return {
        "trend_notice_words": _normalize_trend_items(parsed.get("trend_notice_words", [])),
        "developer_emerging_words": _normalize_emerging_items(parsed.get("developer_emerging_words", [])),
    }


def _extract_response_text(data: dict[str, Any]) -> str:
    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text

    for output in data.get("output", []):
        if not isinstance(output, dict):
            continue
        for content in output.get("content", []):
            if not isinstance(content, dict):
                continue
            text = content.get("text")
            if isinstance(text, str) and text.strip():
                return text
            parsed = content.get("parsed")
            if isinstance(parsed, dict):
                return json.dumps(parsed, ensure_ascii=False)

    raise ValueError("OpenAI trend response did not include output text")


def _normalize_trend_items(items: Any) -> list[TrendItem]:
    normalized: list[TrendItem] = []
    if not isinstance(items, list):
        return normalized

    for item in items:
        if not isinstance(item, dict):
            continue
        keyword = str(item.get("keyword") or "").strip()
        if not keyword:
            continue
        normalized.append(
            {
                "keyword": keyword,
                "count": int(item.get("count") or 0),
                "reason": str(item.get("reason") or "").strip(),
            }
        )
    return normalized


def _normalize_emerging_items(items: Any) -> list[EmergingTrendItem]:
    normalized: list[EmergingTrendItem] = []
    if not isinstance(items, list):
        return normalized

    for item in items:
        if not isinstance(item, dict):
            continue
        keyword = str(item.get("keyword") or "").strip()
        if not keyword:
            continue
        normalized.append(
            {
                "keyword": keyword,
                "reason": str(item.get("reason") or "").strip(),
            }
        )
    return normalized
