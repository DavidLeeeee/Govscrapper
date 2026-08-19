# ETRI 작업 인수인계 문서

## 프로젝트

- 경로: `C:\Users\david\project\SolutionDev\03_GOV_BUIS_SCRAPPER`
- 환경: Windows PowerShell, Python/uv, FastAPI + 정적 client
- 로컬 실행: `uv run python app.py`
- ETRI 스크래핑 테스트:

```powershell
uv run python scripts/run_scraping.py --source etri_ebid_progress --start-date 2026-07-20 --end-date 2026-08-07 --max-pages 4
```

- 문법 검사 예시:

```powershell
.\.venv\Scripts\python.exe -m py_compile src\services\etri_ebid_service.py src\api\routes\notices.py src\scrapers\_etri.py
```

## 이전 세션 문제

이전 Codex 세션에서 Windows sandbox ACL 오류로 파일 읽기/수정이 막혔다.

오류 예:

```text
helper_unknown_error: apply deny-read ACLs
orchestrator_helper_exit_nonzero
apply_patch verification failed: Failed to read file to update ...
```

샌드박스 밖에서는 파일이 읽혔으므로, 파일 자체 권한보다는 Codex Windows sandbox helper 문제로 판단했다.

확인된 ACL 예:

```text
Owner: DESKTOP-DAVID\CodexSandboxOffline
Access: DESKTOP-DAVID\CodexSandboxUsers Allow Modify
```

새 세션에서는 먼저 아래 명령으로 정상 접근 여부를 확인한다.

```powershell
Get-Item src\services\etri_ebid_service.py | Select-Object FullName,Attributes,Length,LastWriteTime
rg -n "etri/original|_source_overrides|notice-origin-link|notice\.url|def _detail_payload|DETAIL_URL_CANDIDATES" src client
```

## 이미 반영되어 있어야 하는 변경

### 1. ETRI `posted_at` 보정

파일: `src/scrapers/_etri.py`

목표:

- 기존에는 ETRI 목록의 `입찰시작일`을 `posted_at`으로 사용했다.
- 실제 공고 등록일은 상세 POST 페이지의 `공고일시`에 있다.
- 새 스크랩부터는 상세 페이지에서 `공고일시`를 읽어 `posted_at`으로 저장해야 한다.

확인할 코드:

- `_to_notices()`에서 `detail_metadata = _fetch_detail_metadata(item.bid_no)`
- `posted_at = detail_metadata.get("posted_at") or _extract_date(item.bid_start_at)`
- `application_start_at`은 입찰시작일 유지
- `deadline`/`application_end_at`은 입찰종료일 유지
- `_fetch_detail_metadata()`가 `src.services.etri_ebid_service`의 `fetch_etri_detail_html`, `extract_etri_posted_at`, `extract_etri_budget_text`를 local import

### 2. ETRI 상세 파서

파일: `src/services/etri_ebid_service.py`

있어야 하는 함수:

- `extract_etri_posted_at(html: str) -> str | None`
- `extract_etri_budget_text(html: str) -> str | None`
- `_extract_labeled_date`
- `_parse_korean_or_iso_date`
- `_normalize_text`

목표:

- `<td>공고일시</td><td>2026년 08월 06일</td>` -> `2026-08-06`
- `<td>추정금액(VAT포함)</td><td>264,000,000 원</td>` -> `budget_text`

### 3. ETRI 저장소 key

파일: `src/services/storage_service.py`

`notice_key()`에 다음 로직이 있어야 한다.

```python
if source == "etri_ebid_progress":
    pblanc_id = str(notice.get("pblanc_id") or "")
    if pblanc_id:
        return source, "pblanc_id", pblanc_id
```

목표:

- ETRI URL이 바뀌어도 같은 `bid_no`/`pblanc_id`면 같은 공고로 병합
- 기존 URL과 프록시 URL 간 중복 저장 방지

### 4. Google Chat 알림 링크 절대화

파일: `src/services/notification_service.py`

목표:

- 알림에서 `</api/etri/original?...|제목>`처럼 깨지는 문제 해결
- `SITE_URL`이 있으면 `/api/...` 상대 URL을 `http://서버주소/api/...` 절대 URL로 변환

확인할 함수:

- `_absolute_url(url, site_url)`
- `build_daily_scraping_message()`에서 `_chat_link(_absolute_url(url, site_url), title)` 사용

## 현재 남은 핵심 요구사항

팀장님이 ETRI 공고를 “내 서버 IP 프록시 링크”가 아니라 “실제 ETRI 사이트 링크”로 보고 싶어한다.

현재 구조:

```text
카드/모달 원문공고열기
-> /api/etri/original?bid_no=EA...
-> 서버가 ETRI 세션 생성
-> ETRI 상세 POST 요청
-> 받아온 HTML을 내 서버에서 반환
```

문제:

- 브라우저 주소창이 `내 IP/api/etri/original?...`로 보인다.
- 팀장님은 `https://ebid.etri.re.kr/...` 형태를 원한다.

중요:

- ETRI 상세는 단순 GET URL로 열리지 않는다.
- 실제 상세는 `POST https://ebid.etri.re.kr/ebid/ebid/ebidCustInfoMainView.do`로 열린다.
- Payload에 `csSignature`, `biNo`, `search=Y`, `sch_fromDate`, `sch_toDate` 등이 필요하다.
- 그냥 실제 ETRI URL을 `href`로 걸면 `다시로그인` 페이지로 튕길 가능성이 높다.

## 추천 구현 방향

“자동 POST 중계 페이지”를 추가한다.

사용자 흐름:

```text
원문 공고 열기 클릭
-> 내 서버 /api/etri/open-external?bid_no=EA...
-> 서버가 HTML form 페이지 반환
-> 브라우저가 즉시 ETRI 실제 URL로 POST submit
-> 주소창은 https://ebid.etri.re.kr/ebid/ebid/ebidCustInfoMainView.do 로 이동
```

단, 실패 가능성이 있으므로 기존 프록시 링크는 fallback으로 유지한다.

## 구현 상세

### A. `src/services/etri_ebid_service.py`에 추가

상단 import:

```python
from html import escape
```

함수 추가:

```python
def build_etri_external_open_url(bid_no: str) -> str:
    return f"/api/etri/open-external?{urlencode({'bid_no': bid_no})}"


def build_etri_external_open_html(bid_no: str, timeout: int = 20) -> str:
    session = make_session()
    initialize_public_session(session)
    cs_signature = _fetch_cs_signature(session, timeout=timeout)
    payload = _detail_payload(bid_no, cs_signature, "")
    fallback_url = build_etri_original_url(bid_no)

    inputs = "\n".join(
        f'<input type="hidden" name="{escape(name)}" value="{escape(value)}">'
        for name, value in payload
    )

    return f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <title>ETRI 원문 공고 열기</title>
</head>
<body>
  <p>ETRI 원문 공고로 이동 중입니다.</p>
  <form id="etri-open-form" method="post" action="{DETAIL_URL_CANDIDATES[0]}">
    {inputs}
  </form>
  <p>자동으로 이동하지 않으면 아래 버튼을 누르세요.</p>
  <button type="submit" form="etri-open-form">ETRI 사이트에서 열기</button>
  <p><a href="{escape(fallback_url)}">프록시 화면으로 열기</a></p>
  <script>document.getElementById("etri-open-form").submit();</script>
</body>
</html>"""
```

주의:

- `DETAIL_URL_CANDIDATES[0]`는 반드시 `https://ebid.etri.re.kr/ebid/ebid/ebidCustInfoMainView.do`여야 한다.
- `_detail_payload()`는 기존 DevTools payload와 유사해야 한다.
- `pageGb`는 빈 값 `""`이 우선이다.

### B. `src/api/routes/notices.py` 수정

import 변경:

```python
from src.services.etri_ebid_service import (
    build_etri_external_open_html,
    build_etri_external_open_url,
    debug_etri_detail_candidates,
    fetch_etri_detail_html,
)
```

`_source_overrides()` 변경:

```python
return {
    "url": f"/api/etri/original?{urlencode({'bid_no': bid_no})}",
    "external_url": build_etri_external_open_url(bid_no),
}
```

라우트 추가:

```python
@router.get("/etri/open-external", response_class=HTMLResponse)
async def open_etri_external(bid_no: str) -> HTMLResponse:
    bid_no = bid_no.strip()
    if not bid_no:
        raise HTTPException(status_code=400, detail="bid_no is required")

    try:
        html = await asyncio.to_thread(build_etri_external_open_html, bid_no)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"ETRI external open failed: {exc}") from exc

    return HTMLResponse(html)
```

### C. `client/static/js/app.js` 수정

모달의 원문 링크가 현재 대략 이런 형태일 가능성이 크다.

```javascript
<a class="notice-origin-link" href="${escapeAttribute(notice.url)}" target="_blank" rel="noreferrer">원문 공고 열기</a>
```

이를 다음처럼 변경한다.

```javascript
<a class="notice-origin-link" href="${escapeAttribute(getNoticeOriginUrl(notice))}" target="_blank" rel="noreferrer">원문 공고 열기</a>
```

함수 추가:

```javascript
function getNoticeOriginUrl(notice) {
  return notice.external_url || notice.url || "#";
}
```

목표:

- 일반 공고는 기존 `url`
- ETRI 공고는 `external_url` 우선 사용
- `url`은 내부 프록시/분석용으로 계속 유지 가능

### D. 공유 메시지 쪽 선택 사항

`build_shared_notice_message()`에서 원문 링크도 실제 ETRI 외부 오픈을 쓰고 싶다면 notice의 `external_url`을 우선하도록 변경 가능하다.

현재:

```python
origin_url = str(notice.get("url") or "").strip()
```

추천:

```python
origin_url = str(notice.get("external_url") or notice.get("url") or "").strip()
```

단, Google Chat 메시지에서 상대 URL 문제가 생길 수 있으므로 절대 URL 변환까지 같이 고려해야 한다. 우선 모달 버튼부터 수정하는 것을 추천한다.

## 테스트 방법

### 1. 문법 검사

```powershell
.\.venv\Scripts\python.exe -m py_compile src\services\etri_ebid_service.py src\api\routes\notices.py src\scrapers\_etri.py src\services\notification_service.py src\services\storage_service.py
```

### 2. 서버 실행

```powershell
uv run python app.py
```

### 3. API 확인

브라우저에서:

```text
http://localhost:8000/api/etri/open-external?bid_no=EA20261819%2801%29
```

기대:

- 잠깐 내 서버 안내 페이지가 열린다.
- 곧바로 `https://ebid.etri.re.kr/ebid/ebid/ebidCustInfoMainView.do`로 POST 이동한다.
- 성공하면 ETRI 실제 상세 화면이 보인다.
- 실패하면 페이지 내 fallback 링크로 `/api/etri/original?...` 사용 가능하다.

### 4. 공고 API 확인

```text
http://localhost:8000/api/notices
```

ETRI notice에 아래 필드가 있어야 한다.

```json
{
  "url": "/api/etri/original?bid_no=...",
  "external_url": "/api/etri/open-external?bid_no=..."
}
```

### 5. 클라이언트 확인

- ETRI 공고 모달 열기
- `원문 공고 열기` 클릭
- 새 탭 주소창이 가능하면 `https://ebid.etri.re.kr/...`로 이동하는지 확인

## ETRI POST payload 참고

사용자가 DevTools에서 확인한 성공 요청:

URL:

```text
https://ebid.etri.re.kr/ebid/ebid/ebidCustInfoMainView.do
```

Method:

```text
POST
```

Payload 핵심:

```text
csSignature=P3D8cHkCMpk6qYEWN/1aOA==
pageNo=1
biNo=EA20261819(01)
tabId=
biType=
pageGb=
sch_biBizList=
search=Y
order=
sch_biNo=
sch_biName=
sch_succDeciMeth=
sch_biState=
sch_fromDate=20260730
sch_toDate=20261006
sch_spotFromDate=
sch_spotToDate=
sch_enterFromDate=
sch_enterToDate=
interestBiNo=EA20261819(01)
```

성공 HTML 특징:

- title: `입찰공고 - 입찰내용 - 한국전자통신연구원 : ETRI`
- hidden `biNo`
- `공고일시`: `2026년 08월 06일`
- `추정금액(VAT포함)`: `264,000,000 원`
- 첨부파일은 `fileDownloadEncStr(...)` onclick 기반

## 주의사항

- ETRI 실제 사이트 직접 링크 요구는 UX 요구사항으로 이해하되, 기술적으로는 POST 기반이라 일반 href로는 어렵다.
- 자동 POST 중계가 최선이지만, ETRI가 세션/쿠키 정책을 더 엄격히 적용하면 실패할 수 있다.
- 따라서 `/api/etri/original` 프록시는 삭제하지 말 것.
- AI 심층분석/첨부파일 수집은 프록시/서버 fetch 기반으로 계속 유지하는 것이 좋다.
