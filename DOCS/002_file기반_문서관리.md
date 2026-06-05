# 파일 기반 문서 관리

이 문서는 스크래핑 결과를 DB 없이 파일과 폴더 구조로 관리하는 방식을 정의한다.

## 기본 방향

초기 프로토타입에서는 별도 DB를 사용하지 않고 파일 기반으로 스크래핑 결과를 관리한다.

검색 대상이 되는 현재 공고와, 보관 목적의 지난 공고를 물리적으로 분리한다.

```text
data/
  sources/
  active/
  expired/
  marked/
```

## 디렉터리 역할

| 경로 | 역할 |
|---|---|
| `data/sources/` | 사이트별, 날짜별 원본 스크래핑 결과 보관 |
| `data/active/` | 현재 검색 대상이 되는 유효 공고 보관 |
| `data/expired/` | 마감 기한이 지난 공고 보관 |
| `data/marked/` | 사용자가 표시한 공고 상태 보관 |

## 권장 구조

```text
data/
  sources/
    bizinfo/
      2026-06-05/
        raw.html
        items.json
      2026-06-06/
        raw.html
        items.json

  active/
    bizinfo/
      items.json

  expired/
    bizinfo/
      2026/
        items.json

  marked/
    items.json
```

## sources

`sources`는 스크래핑 시점의 원본 데이터를 보관하는 영역이다.

날짜별로 저장하여 특정 일자에 어떤 데이터가 수집되었는지 확인할 수 있게 한다.

```text
data/sources/{source_name}/{yyyy-mm-dd}/
```

예시:

```text
data/sources/bizinfo/2026-06-05/raw.html
data/sources/bizinfo/2026-06-05/items.json
```

| 파일 | 역할 |
|---|---|
| `raw.html` | 원본 HTML |
| `items.json` | 파싱된 공고 목록 |

## active

`active`는 실제 검색과 화면 표시의 기준이 되는 영역이다.

마감 기한이 지나지 않은 공고만 유지한다.

```text
data/active/{source_name}/items.json
```

검색 기능은 기본적으로 `data/active/`만 대상으로 한다.

이렇게 하면 지난 공고까지 매번 읽지 않아도 되므로 조건부 검색 효율을 유지할 수 있다.

## expired

`expired`는 마감 기한이 지난 공고를 보관하는 영역이다.

```text
data/expired/{source_name}/{yyyy}/items.json
```

지난 공고는 일반 검색 대상에서 제외한다.

필요한 경우 별도 화면 또는 별도 옵션으로만 조회한다.

## marked

`marked`는 사용자가 중요하다고 표시한 공고 상태를 보관하는 영역이다.

```text
data/marked/items.json
```

`marked`는 공고 원본 저장소가 아니라 공유 표시 상태 저장소로 사용한다.

화면에서는 `active` 공고 목록을 읽은 뒤, `marked` 데이터를 합쳐서 표시한다.

예시:

```json
[
  {
    "key": "bizinfo:url:https://example.com/notice/1",
    "source": "bizinfo",
    "title": "2026년 정부지원사업 공고",
    "url": "https://example.com/notice/1",
    "deadline": "2026-06-30",
    "marked_by": "admin",
    "marked_at": "2026-06-05T14:45:00+09:00",
    "memo": "팀 검토 필요"
  }
]
```

| 필드 | 설명 |
|---|---|
| `key` | 공고 고유 식별자 |
| `source` | 스크래핑 출처 이름 |
| `title` | 공고 제목 |
| `url` | 원문 URL |
| `deadline` | 공고 마감일 |
| `marked_by` | 표시한 사용자 |
| `marked_at` | 표시 시각 |
| `memo` | 선택 메모 |

## 공고 데이터 형식

공고는 JSON으로 저장한다.

최소 필드는 다음과 같다.

```json
{
  "source": "bizinfo",
  "title": "2026년 정부지원사업 공고",
  "url": "https://example.com/notice/1",
  "posted_at": "2026-06-01",
  "deadline": "2026-06-30",
  "scraped_at": "2026-06-05T10:00:00+09:00",
  "keywords": ["수출", "제조", "AI"]
}
```

저장되는 공고 JSON은 항상 위 기본 키를 모두 가진다.

마감일을 안정적으로 파싱할 수 없는 사이트는 `deadline`을 `null`로 저장한다.

| 필드 | 설명 |
|---|---|
| `source` | 스크래핑 출처 이름 |
| `title` | 공고 제목 |
| `url` | 원문 URL |
| `posted_at` | 공고 게시일 |
| `deadline` | 공고 마감일. 알 수 없으면 `null` |
| `scraped_at` | 스크래핑 시각 |
| `keywords` | 분류 또는 검색용 키워드 |

## 마감 공고 이동 기준

마감 공고 여부는 스크래핑 날짜가 아니라 공고의 `deadline`을 기준으로 판단한다.

```text
deadline < today
```

위 조건을 만족하면 해당 공고를 `active`에서 제거하고 `expired`로 이동한다.

`deadline`이 `null`인 공고는 자동 마감 정리 대상에서 제외하고 `active`에 유지한다.

## 처리 흐름

정기 스크래핑 시 다음 순서로 처리한다.

1. 사이트별 스크래핑 실행
2. `data/sources/{source_name}/{yyyy-mm-dd}/`에 원본 저장
3. 파싱 결과를 `items.json`으로 저장
4. 기존 `active` 데이터와 신규 데이터를 병합
5. 중복 공고 제거
6. `deadline` 기준으로 active/expired 분리
7. `data/active/{source_name}/items.json` 갱신
8. `data/expired/{source_name}/{yyyy}/items.json` 갱신

## 중복 제거 기준

우선순위는 다음과 같다.

1. 원문 URL
2. 출처 + 제목 + 마감일

가능하면 원문 URL을 고유 식별자로 사용한다.

URL이 안정적이지 않은 사이트는 `source`, `title`, `deadline` 조합으로 중복 여부를 판단한다.

## 검색 기준

일반 검색은 `data/active/`만 대상으로 한다.

```text
data/active/**/*.json
```

지난 공고 검색이 필요한 경우에만 `data/expired/`를 별도로 검색한다.

```text
data/expired/**/*.json
```

검색 결과를 화면에 표시할 때는 `data/marked/items.json`을 함께 읽어 각 공고의 mark 여부를 합친다.

## 장점

- DB 없이 빠르게 구현할 수 있다.
- 결과 파일을 사람이 직접 확인하기 쉽다.
- 원본 HTML과 파싱 결과를 함께 보관할 수 있다.
- `active`와 `expired`를 분리하여 검색 범위를 줄일 수 있다.
- `marked`를 별도 저장소로 분리하여 모든 사용자에게 공유 표시 상태를 보여줄 수 있다.
- 추후 DB 전환 시 JSON 데이터를 마이그레이션하기 쉽다.

## 주의사항

- 파일 쓰기 중 서버가 종료될 수 있으므로 임시 파일에 먼저 저장한 뒤 교체한다.
- 여러 스크래핑 작업이 동시에 같은 파일을 수정하지 않도록 한다.
- 여러 사용자가 동시에 mark를 수정할 수 있으므로 파일 lock 적용을 검토한다.
- 공고의 마감일이 없는 경우 별도 정책이 필요하다.
- 파일 개수가 많아지면 연도 또는 월 단위로 분리한다.

## 향후 DB 전환 기준

다음 요구사항이 생기면 SQLite 또는 PostgreSQL 전환을 검토한다.

- 계정별 관심 키워드 저장
- 사용자가 확인한 공고 상태 저장
- 복잡한 필터 검색
- 대량 데이터 통계
- 동시 사용자 증가
- 관리자 화면에서 데이터 수정 필요
