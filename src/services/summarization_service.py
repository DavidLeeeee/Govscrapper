"""공고 상세 텍스트 요약을 교체 가능한 구현으로 제공한다."""

from __future__ import annotations

import json
from json import JSONDecodeError
from collections.abc import Callable, Iterable
from datetime import datetime
from typing import Any, Protocol

import requests

from src.contracts.notice import Notice, NoticeSummary
from src.services.deadline_extract_service import extract_deadline_candidate
from src.services.detail_fetch_service import fetch_notice_detail_text
from src.services.storage_service import notice_key


class NoticeSummarizer(Protocol):
    def summarize(self, notice: Notice, detail_text: str) -> NoticeSummary:
        ...


class OpenAIResponsesSummarizer:
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-5.4-mini",
        max_detail_chars: int = 4000,
        max_output_tokens: int = 700,
        timeout: int = 30,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.max_detail_chars = max_detail_chars
        self.max_output_tokens = max_output_tokens
        self.timeout = timeout

    def summarize(self, notice: Notice, detail_text: str) -> NoticeSummary:
        payload = {
            "model": self.model,
            "input": [
                {
                    "role": "developer",
                    "content": (
                        "너는 정부지원사업 공고를 한국어로 요약하는 분석가다. "
                        "과장하지 말고, 본문에서 확인되는 사실만 사용한다. "
                        "마감일은 신청/접수/공모/입찰/의견제출 마감일을 인정한다. "
                        "사전규격공개, 입찰공고, 제안요청서 공개 공고에서는 '공개기간' 또는 '의견제출 기간'의 종료일을 마감일로 본다. "
                        "사업기간/평가일/설명회 일자는 마감일로 쓰지 않는다. "
                        "응답은 반드시 JSON 스키마를 따른다."
                    ),
                },
                {
                    "role": "user",
                    "content": self._build_prompt(notice, detail_text),
                },
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "notice_summary",
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "summary": {
                                "type": "string",
                                "description": "공고의 핵심을 2~3문장으로 짧게 요약한다.",
                            },
                            "detail_points": {
                                "type": "array",
                                "description": "지원대상, 지원내용, 신청방법, 유의사항 중심의 핵심 bullet.",
                                "items": {"type": "string"},
                                "minItems": 2,
                                "maxItems": 4,
                            },
                            "ai_deadline": {
                                "type": ["string", "null"],
                                "description": "본문에서 신청/접수/공모/입찰/의견제출 마감일이 명확히 확인될 때 YYYY-MM-DD 형식으로 반환한다. 사전규격공개는 공개기간 종료일을 사용한다. 없거나 불확실하면 null.",
                            },
                            "ai_deadline_text": {
                                "type": ["string", "null"],
                                "description": "마감일 판단에 사용한 원문 문구. 없거나 불확실하면 null.",
                            },
                            "ai_deadline_confidence": {
                                "type": "string",
                                "enum": ["high", "medium", "low", "none"],
                                "description": "신청/접수/공모/입찰/의견제출 마감일 추정 신뢰도.",
                            },
                        },
                        "required": [
                            "summary",
                            "detail_points",
                            "ai_deadline",
                            "ai_deadline_text",
                            "ai_deadline_confidence",
                        ],
                    },
                    "strict": True,
                }
            },
            "reasoning": {
                "effort": "minimal",
            },
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
        return _parse_summary_response(response.json())

    def _build_prompt(self, notice: Notice, detail_text: str) -> str:
        trimmed_detail = detail_text[: self.max_detail_chars]
        return "\n".join(
            [
                f"제목: {notice.get('title', '')}",
                f"출처: {notice.get('source', '')}",
                f"등록일: {notice.get('posted_at', '')}",
                f"마감일: {notice.get('deadline') or '확인 필요'}",
                f"원문 URL: {notice.get('url', '')}",
                "",
                "상세 본문:",
                trimmed_detail,
            ]
        )


class EmptySummarizer:
    def summarize(self, notice: Notice, detail_text: str) -> NoticeSummary:
        return {
            "summary": "",
            "detail_points": [],
            "ai_deadline": None,
            "ai_deadline_text": None,
            "ai_deadline_confidence": "none",
        }


def summarize_notices(
    notices: Iterable[Notice],
    summarizer: NoticeSummarizer,
    existing_notices: Iterable[Notice] = (),
    limit: int | None = None,
    on_progress: Callable[[str], None] | None = None,
    force: bool = False,
) -> tuple[list[Notice], dict[str, int]]:
    existing_by_key = {notice_key(notice): notice for notice in existing_notices}
    updated_notices: list[Notice] = []
    stats = {"attempted_count": 0, "summarized_count": 0, "skipped_count": 0, "error_count": 0}

    for notice in notices:
        updated = _copy_existing_summary(notice, existing_by_key.get(notice_key(notice)))
        if not force and _has_summary(updated):
            if not updated.get("deadline"):
                _emit_progress(on_progress, f"  - 기존 요약 공고 마감일 보강: {updated.get('title', '')}")
                try:
                    detail_text = fetch_notice_detail_text(updated)
                    deadline_candidate = extract_deadline_candidate(detail_text)
                    if deadline_candidate is not None:
                        updated["ai_deadline"] = deadline_candidate.deadline
                        updated["ai_deadline_text"] = deadline_candidate.source_text
                        updated["ai_deadline_confidence"] = deadline_candidate.confidence
                        _emit_progress(on_progress, f"  - 마감일 추출: {deadline_candidate.deadline}")
                    else:
                        _emit_progress(on_progress, "  - 마감일 후보 없음")
                except Exception as exc:
                    stats["error_count"] += 1
                    _emit_progress(on_progress, f"  - 마감일 보강 실패: {type(exc).__name__}: {exc}")

            stats["skipped_count"] += 1
            updated_notices.append(updated)
            continue

        if limit is not None and stats["attempted_count"] >= limit:
            stats["skipped_count"] += 1
            updated_notices.append(updated)
            continue

        stats["attempted_count"] += 1
        _emit_progress(on_progress, f"[{stats['attempted_count']}/{limit or '?'}] 상세 수집: {updated.get('title', '')}")
        try:
            detail_text = fetch_notice_detail_text(updated)
            if not detail_text:
                _emit_progress(on_progress, "  - 상세 본문 없음: 건너뜀")
                stats["skipped_count"] += 1
                updated_notices.append(updated)
                continue

            deadline_candidate = extract_deadline_candidate(detail_text)
            if deadline_candidate is not None:
                _emit_progress(on_progress, f"  - 마감일 추출: {deadline_candidate.deadline}")
            _emit_progress(on_progress, "  - OpenAI 요약 요청")
            summary = summarizer.summarize(updated, detail_text)
            updated["summary"] = summary["summary"]
            updated["detail_points"] = summary["detail_points"]
            if deadline_candidate is not None and not updated.get("deadline"):
                updated["ai_deadline"] = deadline_candidate.deadline
                updated["ai_deadline_text"] = deadline_candidate.source_text
                updated["ai_deadline_confidence"] = deadline_candidate.confidence
            else:
                updated["ai_deadline"] = summary["ai_deadline"]
                updated["ai_deadline_text"] = summary["ai_deadline_text"]
                updated["ai_deadline_confidence"] = summary["ai_deadline_confidence"]
            updated["detail_fetched_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
            stats["summarized_count"] += 1
            _emit_progress(on_progress, "  - 요약 완료")
        except Exception as exc:
            stats["error_count"] += 1
            _emit_progress(on_progress, f"  - 실패: {type(exc).__name__}: {exc}")

        updated_notices.append(updated)

    return updated_notices, stats


def build_openai_summarizer(
    api_key: str | None,
    model: str,
    max_detail_chars: int,
    max_output_tokens: int = 700,
) -> NoticeSummarizer | None:
    if not api_key:
        return None

    return OpenAIResponsesSummarizer(
        api_key=api_key,
        model=model,
        max_detail_chars=max_detail_chars,
        max_output_tokens=max_output_tokens,
    )


def _copy_existing_summary(notice: Notice, existing: Notice | None) -> Notice:
    if existing is None:
        return dict(notice)  # type: ignore[return-value]

    updated = dict(notice)
    for field in (
        "summary",
        "detail_points",
        "detail_fetched_at",
        "ai_deadline",
        "ai_deadline_text",
        "ai_deadline_confidence",
    ):
        if field not in updated and field in existing:
            updated[field] = existing[field]  # type: ignore[literal-required]

    return updated  # type: ignore[return-value]


def _has_summary(notice: Notice) -> bool:
    return bool(str(notice.get("summary") or "").strip())


def _parse_summary_response(data: dict[str, Any]) -> NoticeSummary:
    text = _extract_response_text(data)
    try:
        parsed = json.loads(text)
    except JSONDecodeError as exc:
        preview = text[:220].replace("\n", " ")
        tail = text[-220:].replace("\n", " ")
        raise ValueError(
            f"OpenAI JSON output was truncated or invalid: {exc}; length={len(text)}; head={preview}; tail={tail}"
        ) from exc
    summary = str(parsed.get("summary") or "").strip()
    detail_points = [str(point).strip() for point in parsed.get("detail_points", []) if str(point).strip()]
    ai_deadline = _normalize_ai_deadline(parsed.get("ai_deadline"))
    ai_deadline_text = str(parsed.get("ai_deadline_text") or "").strip() or None
    ai_deadline_confidence = str(parsed.get("ai_deadline_confidence") or "none").strip().lower()
    if ai_deadline_confidence not in {"high", "medium", "low", "none"}:
        ai_deadline_confidence = "none"
    if not summary:
        raise ValueError("OpenAI summary response did not include summary")

    return {
        "summary": summary,
        "detail_points": detail_points,
        "ai_deadline": ai_deadline,
        "ai_deadline_text": ai_deadline_text,
        "ai_deadline_confidence": ai_deadline_confidence,
    }


def _normalize_ai_deadline(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None

    try:
        datetime.fromisoformat(text[:10])
    except ValueError:
        return None

    return text[:10]


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
            if isinstance(parsed, str) and parsed.strip():
                return parsed
            content_text = content.get("content")
            if isinstance(content_text, str) and content_text.strip():
                return content_text

    raise ValueError(f"OpenAI response did not include output text: {_summarize_response_shape(data)}")


def _summarize_response_shape(data: dict[str, Any]) -> str:
    output_shapes: list[dict[str, Any]] = []
    for output in data.get("output", []):
        if not isinstance(output, dict):
            output_shapes.append({"type": type(output).__name__})
            continue

        output_shapes.append(
            {
                "type": output.get("type"),
                "status": output.get("status"),
                "content_types": [
                    content.get("type")
                    for content in output.get("content", [])
                    if isinstance(content, dict)
                ],
            }
        )

    return json.dumps(
        {
            "id": data.get("id"),
            "status": data.get("status"),
            "incomplete_details": data.get("incomplete_details"),
            "output_shapes": output_shapes,
        },
        ensure_ascii=False,
    )


def _emit_progress(on_progress: Callable[[str], None] | None, message: str) -> None:
    if on_progress is not None:
        on_progress(message)
