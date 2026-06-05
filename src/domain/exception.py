"""도메인 계층에서 사용하는 예외 정의.
> 업무 규칙/비즈니스 규칙만 신경 쓰는 층 (ex) user가 없거나 email이 틀리는 것 등 로직 관련
rule 102:
- 서비스는 도메인 예외만 던지고, API 계층(api/errors.py)에서 HTTP 상태·JSON으로 매핑한다.
- 이 모듈에서는 "무슨 일이 잘못됐는지"만 표현하고, HTTP/JSON은 전혀 알지 못한다.
"""


class DomainError(Exception):
    """도메인 계층에서 사용하는 베이스 예외.

    새 도메인 예외는 이 클래스를 상속해서 정의한다.
    HTTP 상태 코드와 에러 JSON 형식은 api/errors.py에서만 결정한다.
    """


class NotFoundError(DomainError):
    """리소스를 찾을 수 없을 때 사용하는 예외.

    예:
        raise NotFoundError("user")
    """


class ValidationError(DomainError):
    """도메인 규칙 위반(유효성 검사 실패) 시 사용하는 예외.

    예:
        raise ValidationError("email is invalid")
    """


# 새 예외를 추가할 때 예시:
#
# class DuplicateError(DomainError):
#     \"\"\"중복 리소스가 발생했을 때 사용하는 예외.\"\"\"
#
# HTTP 상태/JSON 매핑은 api/errors.py의 핸들러에서만 추가한다.