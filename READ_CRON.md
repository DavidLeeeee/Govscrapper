# Cron 등록 방법

## 1. 서버 시간대 확인

- 현재 시간대 확인:
  ```bash
  date
  timedatectl
  ```

- Asia/Seoul이 아니면 변경:
  ```bash
  sudo timedatectl set-timezone Asia/Seoul
  ```

## 2. 로그 디렉터리 생성

- 프로젝트 루트에서 실행:
  ```bash
  mkdir -p logs
  ```

## 3. crontab 열기

- 현재 사용자 cron 편집:
  ```bash
  crontab -e
  ```

## 4. 매일 오전 10시 공고 수집 등록

- 마감 정렬: 매일 새벽 1시에 일반/지역공고의 마감 공고 이동
  ```cron
  0 1 * * * cd /path/to/03_GOV_BUIS_SCRAPPER && uv run python scripts/align_expired.py >> logs/cron-align-expired.log 2>&1
  ```

- 일반/지역 공고 수집 + Google Chat 통합 알림: 어제~오늘 등록 공고 수집 후 알림 1회 전송
  ```cron
  0 10 * * * cd /path/to/03_GOV_BUIS_SCRAPPER && uv run python scripts/run_daily_scraping_notify.py >> logs/cron-daily-notify.log 2>&1
  ```

- 월간 키워드 트렌드 생성: 매월 1일 새벽 1시 10분에 직전 월 공고 제목 분석
  ```cron
  10 1 1 * * cd /path/to/03_GOV_BUIS_SCRAPPER && uv run python scripts/generate_trends.py >> logs/cron-generate-trends.log 2>&1
  ```

`/path/to/03_GOV_BUIS_SCRAPPER`는 실제 프로젝트 경로로 바꾼다.
Google Chat 알림을 보내려면 `.env`에 `CHAT_API_URL`을 설정한다.

## 5. 등록 확인

- 등록된 cron 목록 확인:
  ```bash
  crontab -l
  ```

## 6. 로그 확인

- 마감 정렬 로그:
  ```bash
  tail -f logs/cron-align-expired.log
  ```

- 수집/알림 로그:
  ```bash
  tail -f logs/cron-daily-notify.log
  ```

- 월간 트렌드 생성 로그:
  ```bash
  tail -f logs/cron-generate-trends.log
  ```

- 최근 알림 원본 JSON:
  ```bash
  cat data/alarm/latest.json
  ```

## 주의

- cron에서는 `%`가 특수문자라 `date +\%F`처럼 escape 해야 한다.
- cron 환경에서는 PATH가 짧을 수 있다. `uv`를 찾지 못하면 `which uv`로 절대경로를 확인한 뒤 cron 명령의 `uv`를 절대경로로 바꾼다.
- AI 추정 마감일은 신뢰도가 `high`인 값만 자동 마감 정렬에 사용한다.
