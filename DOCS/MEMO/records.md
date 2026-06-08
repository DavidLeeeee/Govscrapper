# 구현 기록

다른 환경에서 이어서 작업하기 위한 현재 구현 요약이다.

## 프로젝트 방향

- 팀 내부용 정부지원사업 스크래핑 도구
- Python 3.12 + FastAPI 기반
- DB 없이 파일 기반 저장소 사용
- 정기 실행은 리눅스 cron에서 Python script를 직접 실행하는 방향
- 웹 서버는 클라이언트 페이지/API/수동 실행용으로 사용

## 실행 명령

개발 서버:

```powershell
uv run uvicorn app:app --reload --port 8000
```

정기 스크래핑 수동 실행:

```powershell
uv run python scripts\run_scraping.py
```

마감 공고 정렬 수동 실행:

```powershell
uv run python scripts\align_expired.py
```

문법 확인:

```powershell
uv run python -m compileall src scripts
```

## 현재 의존성

`pyproject.toml` 기준:

- `fastapi`
- `uvicorn[standard]`
- `requests`
- `beautifulsoup4`

개발환경 기록은 `DOCS/001_DEV_ENV.md`에 유지한다.

새 라이브러리/도구를 추가하면 `AGENT.md` 규칙에 따라 `DOCS/001_DEV_ENV.md`에 이름, 버전, 사용 목적을 기록한다.

## 주요 디렉터리

```text
client/
  index.html
  static/css/app.css

data/
  sources/
  active/
  expired/
  marked/

runtime/
  locks/
  logs/

scripts/
  run_scraping.py
  align_expired.py
  backfill_iris.py

src/
  api/
  contracts/
  domain/
  schemas/
  scrapers/
  services/
```

## 서버/API 구조

- `app.py`: FastAPI 앱 진입점
- `src/server.py`: 앱 생성, static mount, 라우터 등록
- `/`: `client/index.html` 서빙
- `/static/*`: `client/static/` 정적 파일 서빙
- `/api/*`: API 영역
- `/api/health`: health check

## 데이터 저장 정책

파일 기반 저장소를 사용한다.

```text
data/sources/{source}/{yyyy-mm-dd}/items.json
data/active/{source}/items.json
data/expired/{source}/{yyyy}/items.json
data/marked/items.json
```

- `sources`: 스크래핑 날짜별 원본 파싱 결과
- `active`: 현재 검색 대상 공고
- `expired`: 마감된 공고
- `marked`: 사용자가 표시한 공고 상태

파일 쓰기는 `atomic_write_json()`으로 임시 파일 작성 후 교체한다.

## Notice 계약

공고 데이터 계약은 `src/contracts/notice.py`에 있다.

저장되는 Notice JSON은 항상 같은 기본 키를 가진다.

```json
{
  "source": "kisa_bid",
  "title": "...",
  "url": "...",
  "posted_at": "2026-06-05",
  "deadline": null,
  "scraped_at": "2026-06-05T17:34:08+09:00",
  "keywords": []
}
```

`deadline`을 파싱할 수 없는 사이트는 `null`로 저장한다.

`deadline == null`인 공고는 자동 마감 정렬 대상에서 제외하고 `active`에 유지한다.

## 스크래핑 옵션

스크래핑 실행 옵션은 `src/contracts/scrape_options.py`에 있다.

- `ScrapeMode.DAILY`: 정기 실행용
- `ScrapeMode.BACKFILL`: 최초 1회 넓은 범위 수집용
- `ScrapeOptions.daily(date)`
- `ScrapeOptions.backfill(start_date, end_date)`

모든 사이트별 스크래퍼는 `scrape(options: ScrapeOptions) -> list[Notice]` 형태를 따른다.

## 스크래퍼 구조

- `src/scrapers/SITES_INFO.py`: 스크래핑 대상 enum
- `src/scrapers/scrap_interface.py`: 스크래퍼 공통 인터페이스
- `src/scrapers/registry.py`: 실제 실행할 스크래퍼 등록 목록
- 사이트별 구현 파일은 `_kisa.py`처럼 `_` prefix 사용

현재 등록된 스크래퍼:

- `KisaBidScraper`
- source: `kisa_bid`
- target URL: `https://www.kisa.or.kr/403?page={page}`
- `IrisBtinSituScraper`
- source: `iris_btin_situ`
- target URL: `https://www.iris.go.kr/contents/retrieveBsnsAncmBtinSituListView.do`
- `NiaBidScraper`
- source: `nia`
- target URL: `https://www.nia.or.kr/site/nia_kor/ex/bbs/List.do?cbIdx=78336`

## KISA 구현 상태

파일: `src/scrapers/_kisa.py`

현재 구현:

- `requests.Session` 사용
- `BeautifulSoup`으로 목록 페이지 파싱
- `/403/form?...postSeq=...` 링크 추출
- 같은 `tr`에서 `등록일` 추출
- `ScrapeOptions.start_date ~ end_date` 범위에 해당하는 공고만 반환
- 상세 페이지 본문/첨부파일/마감일 파싱은 아직 하지 않음

KISA 상세 페이지는 형식이 일정하지 않아 현재는 `deadline: null`로 저장한다.

## IRIS 구현 상태

파일: `src/scrapers/_iris.py`

현재 구현:

- `requests.Session` 사용
- `retrieveBsnsAncmBtinSituList.do`에 POST 요청
- `blngGovdSe[]` 반복 파라미터와 `blngGovdSeArr` pipe 문자열로 부처 코드 필터링
- 기본 부처 코드는 `AR4001`, `AR4981`
- 응답의 부처명도 `과학기술정보통신부`, `개인정보보호위원회`인지 한 번 더 필터링
- 응답의 `listBsnsAncmBtinSitu`를 `Notice`로 변환
- `ancmDe`를 `posted_at`으로 사용하고 없으면 `rcveStrDe` 사용
- `rcveEndDe`를 `deadline`으로 사용
- `YYYY.MM.DD`, `YYYY-MM-DD`를 모두 `YYYY-MM-DD`로 정규화

허용 부처 코드는 `IrisBtinSituScraper(government_codes=(...))`에서 자유롭게 추가/삭제한다.

허용 부처명은 `IrisBtinSituScraper(allowed_government_names=(...))`에서 자유롭게 추가/삭제한다.

`keywords`는 자동 메타데이터 저장소로 쓰지 않고, 현재는 빈 리스트로 둔다.

## NIA 구현 상태

파일: `src/scrapers/_nia.py`

현재 구현:

- `requests.Session` 사용
- `List.do?cbIdx=78336&pageIndex={page}` HTML 페이지 파싱
- `tr`, `li` 단위로 제목 링크와 등록일 추출
- row 기반 파싱 실패 시 텍스트 기반 fallback 사용
- 목록에서 마감일을 안정적으로 알 수 없으므로 `deadline: null`로 저장
- 상세 URL을 알 수 없으면 목록 URL fragment fallback 사용
- NIA는 URL 보정 과정에서 상세 URL이 바뀔 수 있어 중복 기준을 `source + title + posted_at`으로 사용

## 서비스 계층

- `storage_service.py`
  - JSON read/write
  - atomic write
  - Notice 정규화
  - 중복 제거
  - active/expired 경로 생성

- `scraping_service.py`
  - 등록된 스크래퍼 실행
  - sources 저장
  - active 병합
  - 신규 공고 판별
  - Google Chat 알림 호출

- `align_service.py`
  - active 공고 중 `deadline < today`인 공고를 expired로 이동
  - `deadline == null`은 active 유지

- `marked_service.py`
  - mark/unmark/list
  - active 공고에 marked 상태 합성

- `notification_service.py`
  - 신규 공고 메시지 생성
  - Google Chat Incoming Webhook 전송

- `file_lock.py`
  - cron/수동 실행 중복 방지용 lock 파일 관리

## 자동화 계획

리눅스 cron 예시:

```cron
30 9,13 * * * cd /path/to/project && /path/to/project/.venv/bin/python scripts/run_scraping.py
5 0 * * * cd /path/to/project && /path/to/project/.venv/bin/python scripts/align_expired.py
```

락 파일:

```text
runtime/locks/scraping.lock
runtime/locks/align.lock
```

## 남은 작업

- KISA 실제 사이트에서 `run_scraping.py` 결과 확인
- `data/active/kisa_bid/items.json` 저장 결과 확인
- 웹 화면에서 active 공고 목록 조회 API 추가
- mark/unmark API 추가
- Google Chat webhook 환경 변수 연동 확인
- 최초 1회 backfill 실행 스크립트 추가
- IRIS backfill은 `scripts/backfill_iris.py`로 실행 가능
- 다음 사이트 스크래퍼 추가

## 주의사항

- 현재 저장 데이터는 `.gitignore` 대상이다.
- `data/marked/.gitkeep`만 추적 대상으로 유지한다.
- 다른 컴퓨터에서 이어서 작업할 때는 `uv sync` 후 실행한다.
- Windows 샌드박스 환경에서는 FastAPI import 시 `_overlapped` 오류가 발생했던 적이 있다. 리눅스 서버 배포가 최종 기준이다.
