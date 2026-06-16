from __future__ import annotations

from typing import Any, Protocol

from src.contracts.notice import Notice


class DeepAnalyzer(Protocol):
    def analyze(self, notice: Notice, material: dict[str, Any]) -> dict[str, Any]:
        """첨부파일 추출 내용을 심층 분석한다."""
