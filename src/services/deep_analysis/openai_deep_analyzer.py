from __future__ import annotations

import json
from typing import Any

import requests

from src.contracts.notice import Notice
from src.services.deep_analysis.prompting import (
    ANALYSIS_SCHEMA,
    SYSTEM_PROMPT,
    build_deep_analysis_prompt,
    normalize_analysis,
    parse_analysis_json,
)


class OpenAIDeepAnalyzer:
    def __init__(
        self,
        api_key: str,
        model: str,
        max_file_chars: int = 14000,
        max_prompt_chars: int = 50000,
        max_output_tokens: int = 1600,
        reasoning_effort: str = "low",
        timeout: int = 60,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.max_file_chars = max_file_chars
        self.max_prompt_chars = max_prompt_chars
        self.max_output_tokens = max_output_tokens
        self.reasoning_effort = reasoning_effort
        self.timeout = timeout

    def analyze(self, notice: Notice, material: dict[str, Any]) -> dict[str, Any]:
        user_content = _build_user_content(
            notice,
            material,
            max_file_chars=self.max_file_chars,
            max_prompt_chars=self.max_prompt_chars,
        )
        payload = {
            "model": self.model,
            "input": [
                {"role": "developer", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "notice_deep_analysis",
                    "schema": ANALYSIS_SCHEMA,
                    "strict": True,
                }
            },
            "reasoning": {"effort": self.reasoning_effort},
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
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            detail = response.text[:1200]
            raise RuntimeError(f"OpenAI analysis request failed: {response.status_code} {detail}") from exc
        return normalize_analysis(_parse_response(response.json()))


def _build_user_content(
    notice: Notice,
    material: dict[str, Any],
    max_file_chars: int,
    max_prompt_chars: int,
) -> list[dict[str, str]]:
    content = [
        {
            "type": "input_text",
            "text": build_deep_analysis_prompt(
                notice,
                material,
                max_file_chars=max_file_chars,
                max_prompt_chars=max_prompt_chars,
            ),
        }
    ]

    for file in material.get("files", [])[:5]:
        file_data = file.get("input_file_data") if isinstance(file, dict) else None
        if not isinstance(file_data, str) or not file_data:
            continue
        filename = str(file.get("input_file_name") or file.get("name") or "attachment.pdf")
        content.append(
            {
                "type": "input_file",
                "filename": filename,
                "file_data": file_data,
            }
        )

    return content


def _parse_response(data: dict[str, Any]) -> dict[str, Any]:
    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return parse_analysis_json(output_text)

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
                return parse_analysis_json(text)

    raise ValueError("OpenAI deep analysis response did not include output text")
