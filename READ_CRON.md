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

- 일반 공고: 어제~오늘 등록 공고 수집
  ```cron
  0 10 * * * cd /path/to/03_GOV_BUIS_SCRAPPER && YESTERDAY=$(date -d "yesterday" +\%F) && TODAY=$(date +\%F) && uv run python scripts/run_scraping.py --start-date "$YESTERDAY" --end-date "$TODAY" >> logs/cron-scraping.log 2>&1
  ```

- 지역공고: 어제~오늘 등록 공고 수집
  ```cron
  5 10 * * * cd /path/to/03_GOV_BUIS_SCRAPPER && YESTERDAY=$(date -d "yesterday" +\%F) && TODAY=$(date +\%F) && uv run python scripts/run_regional_scraping.py --start-date "$YESTERDAY" --end-date "$TODAY" --max-pages 5 >> logs/cron-regional.log 2>&1
  ```

`/path/to/03_GOV_BUIS_SCRAPPER`는 실제 프로젝트 경로로 바꾼다.

## 5. 등록 확인

- 등록된 cron 목록 확인:
  ```bash
  crontab -l
  ```

## 6. 로그 확인

- 일반 공고 로그:
  ```bash
  tail -f logs/cron-scraping.log
  ```

- 지역공고 로그:
  ```bash
  tail -f logs/cron-regional.log
  ```

## 주의

- cron에서는 `%`가 특수문자라 `date +\%F`처럼 escape 해야 한다.
- cron 환경에서는 PATH가 짧을 수 있다. `uv`를 찾지 못하면 `which uv`로 절대경로를 확인한 뒤 cron 명령의 `uv`를 절대경로로 바꾼다.
