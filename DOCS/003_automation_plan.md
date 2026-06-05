# 자동화 계획

이 문서는 리눅스 서버에서 정기 스크래핑, 신규 공고 알림, 마감 공고 정리를 자동화하는 초기 계획을 정의한다.

디렉터리 구조는 개발 과정에서 변경될 수 있다.

## 목표

- 매일 오전 9시 30분에 스크래핑 실행
- 매일 오후 1시 30분에 스크래핑 실행
- 신규 공고가 있으면 Google Chat 등으로 알림 전송
- 매일 자정 이후 마감된 공고를 `expired` 영역으로 이동

## 기본 방향

정기 실행은 리눅스 서버의 `cron`을 사용한다.

FastAPI 서버는 웹 조회와 수동 실행용으로 사용하고, 정기 작업은 별도 Python 스크립트로 분리한다.

```text
cron
  -> Python script
      -> service layer
```

이 방식은 웹 서버 상태와 정기 작업을 분리할 수 있어 단순하고 안정적이다.

## 권장 구조

현재 기준 권장 구조는 다음과 같다.

```text
app/
  services/
    scraping_service.py
    storage_service.py
    notification_service.py
    align_service.py
  scrapers/
    bizinfo.py

scripts/
  run_scraping.py
  align_expired.py

data/
  sources/
  active/
  expired/

runtime/
  locks/
  logs/
```

| 경로 | 역할 |
|---|---|
| `app/services/scraping_service.py` | 전체 스크래핑 실행 흐름 관리 |
| `app/services/storage_service.py` | 파일 저장, 병합, 중복 제거 |
| `app/services/notification_service.py` | Google Chat 등 외부 알림 전송 |
| `app/services/align_service.py` | active/expired 공고 정렬 |
| `app/scrapers/` | 사이트별 스크래퍼 |
| `scripts/run_scraping.py` | cron에서 호출하는 스크래핑 실행 스크립트 |
| `scripts/align_expired.py` | cron에서 호출하는 active/expired 정렬 스크립트 |
| `data/sources/` | 날짜별 원본 스크래핑 결과 |
| `data/active/` | 현재 검색 대상 공고 |
| `data/expired/` | 마감된 공고 |
| `runtime/locks/` | 중복 실행 방지 lock 파일 |
| `runtime/logs/` | 작업 로그 |

## cron 설정

매일 오전 9시 30분, 오후 1시 30분에 스크래핑을 실행한다.

```cron
30 9,13 * * * cd /path/to/project && /path/to/project/.venv/bin/python scripts/run_scraping.py
```

매일 자정 직후 마감 공고를 정리한다.

```cron
5 0 * * * cd /path/to/project && /path/to/project/.venv/bin/python scripts/align_expired.py
```

실제 서버 경로에 맞게 `/path/to/project`는 수정한다.

## 스크래핑 실행 흐름

`scripts/run_scraping.py`는 다음 흐름으로 동작한다.

1. 중복 실행 방지 lock 획득
2. 대상 사이트별 스크래핑 실행
3. 원본 데이터를 `data/sources/{source_name}/{yyyy-mm-dd}/`에 저장
4. 파싱 결과를 `items.json`으로 저장
5. 기존 `data/active/{source_name}/items.json` 로드
6. 신규 데이터와 기존 active 데이터 병합
7. 중복 공고 제거
8. 신규 공고 목록 추출
9. `data/active/{source_name}/items.json` 갱신
10. 신규 공고가 있으면 알림 전송
11. 작업 로그 기록
12. lock 해제

## 신규 공고 판단 기준

신규 공고 판단은 우선 원문 URL을 기준으로 한다.

```text
source + url
```

URL이 안정적이지 않은 사이트는 다음 조합을 사용한다.

```text
source + title + deadline
```

## 알림 전송

신규 공고가 있을 때만 Google Chat 등 외부 알림을 전송한다.

초기 구현은 Google Chat Incoming Webhook을 사용한다.

알림 메시지 예시:

```text
[정부지원사업 신규 공고]
- 2026년 중소기업 수출지원사업
  https://example.com/notice/1

- 2026년 AI 바우처 지원사업
  https://example.com/notice/2
```

알림 실패가 스크래핑 결과 저장을 막지 않도록 한다.

즉, 스크래핑과 파일 저장은 완료하고 알림 실패만 로그로 남긴다.

## 마감 공고 정리 흐름

`scripts/align_expired.py`는 다음 흐름으로 동작한다.

1. 중복 실행 방지 lock 획득
2. `data/active/**/*.json` 탐색
3. 각 공고의 `deadline` 확인
4. `deadline < today` 인 공고를 마감 공고로 판단
5. 마감 공고를 `data/expired/{source_name}/{yyyy}/items.json`에 병합
6. `data/active/{source_name}/items.json`에는 유효 공고만 다시 저장
7. 작업 로그 기록
8. lock 해제

마감 여부는 스크래핑 날짜가 아니라 공고의 `deadline`을 기준으로 판단한다.

## 파일 저장 방식

파일 저장은 atomic write 방식으로 처리한다.

```text
items.json.tmp 작성
-> items.json 교체
```

중간에 프로세스가 종료되어도 기존 `items.json`이 깨지지 않도록 하기 위함이다.

## 중복 실행 방지

정기 작업은 lock 파일을 사용하여 중복 실행을 방지한다.

```text
runtime/locks/scraping.lock
runtime/locks/align.lock
```

이미 lock이 존재하면 새 작업은 실행하지 않고 로그만 남긴다.

단, 비정상 종료로 lock 파일이 남을 수 있으므로 lock 생성 시각을 함께 기록하고 오래된 lock은 무시하거나 제거하는 정책을 둔다.

## 로그

작업 로그는 `runtime/logs/`에 저장한다.

예시:

```text
runtime/logs/scraping.log
runtime/logs/align.log
```

로그에는 다음 내용을 남긴다.

- 작업 시작 시각
- 작업 종료 시각
- 대상 사이트
- 수집 공고 수
- 신규 공고 수
- 알림 전송 결과
- 오류 내용

## FastAPI와의 관계

FastAPI 서버는 다음 역할을 담당한다.

- active 공고 조회
- expired 공고 조회
- 파일 다운로드
- 수동 스크래핑 실행
- 작업 로그 확인

정기 작업과 FastAPI는 동일한 service layer를 호출한다.

```text
cron script -> service layer
FastAPI router -> service layer
```

스크래핑 로직을 API 라우터 내부에 직접 넣지 않는다.

## 향후 검토 사항

- 작업 큐 도입
- 실패한 사이트만 재시도
- 알림 채널 추가
- 관리자 화면에서 수동 재실행
- 공고별 확인 여부 저장
- 계정별 관심 키워드 알림
- SQLite 또는 PostgreSQL 전환
