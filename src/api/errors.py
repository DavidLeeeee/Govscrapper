"""도메인 예외를 HTTP 상태·JSON 응답으로 매핑하는 레이어."""

from typing import Any, cast

from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.domain.exception import DomainError, NotFoundError, ValidationError


class ErrorResponse(BaseModel):
    """공통 에러 응답 스키마.

    에러 응답 형식은 가능한 한 이 모델로 통일한다.
    """

    code: str
    message: str
    trace_id: str | None = None


def _get_status_code_and_code(exc: DomainError) -> tuple[int, str]:
    """도메인 예외를 HTTP 상태 코드와 에러 코드 문자열로 변환한다.

    새 도메인 예외를 추가할 때는 이 함수에 분기를 추가한다.
    """

    if isinstance(exc, NotFoundError):
        return 404, "NOT_FOUND"

    if isinstance(exc, ValidationError):
        return 400, "VALIDATION_ERROR"

    # 기본값: 도메인 예외가 무엇이든 클라이언트에는 400 수준으로 응답
    return 400, "DOMAIN_ERROR"


async def domain_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """FastAPI exception handler.

    - 도메인 예외를 ErrorResponse(JSON)로 변환한다.
    - trace_id는 추후 미들웨어에서 request.state에 넣어두고 여기서 꺼내 쓸 수 있다.
    """

    if not isinstance(exc, DomainError):
        trace_id_fallback: str | None = getattr(request.state, "trace_id", None)
        fallback_error = ErrorResponse(
            code="INTERNAL_ERROR",
            message="Unexpected error type for DomainError handler",
            trace_id=trace_id_fallback,
        )
        return JSONResponse(
            status_code=500,
            content=fallback_error.model_dump(),
        )

    domain_exc = cast(DomainError, exc)
    status_code, code = _get_status_code_and_code(domain_exc)

    trace_id: str | None
    trace_id = getattr(request.state, "trace_id", None)

    error = ErrorResponse(code=code, message=str(exc), trace_id=trace_id)
    content: dict[str, Any] = error.model_dump()

    return JSONResponse(status_code=status_code, content=content)


# 새 도메인 예외를 추가할 때 절차 예시:
# 1) src/domain/exception.py에 DomainError를 상속하는 예외 클래스를 정의한다.
# 2) 위 _get_status_code_and_code()에 isinstance 분기를 추가하고,
#    HTTP 상태 코드와 에러 코드 문자열을 결정한다.
# 3) 필요 시 ErrorResponse에 필드를 추가하고, 클라이언트 계약을 업데이트한다.
