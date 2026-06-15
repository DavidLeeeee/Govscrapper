# 정부지원사업 스크래핑

## 환경
1. 리눅스 서버

### 필요 기능
1. 정부지원사업 웹사이트 스크래핑 및 분류
2. 웹사이트로 서비스를 제공해야 한다.
3. (고려중) 계정 별 키워드 탐색

### 스크래핑 대상 추가 검토 사항 (필수 아님)
1. AI API Call 요약
2. 키워드 GET (AI 또는 Hard Text 분류)
3. 파일을 제공해야 한다.

### 계정 관리
1. 회사 팀 내부적으로 사용할 것이기 때문에 보안 요소는 전혀 필요가 없다.
2. 서버 또한 외부 접근이 불가능한 내부 서버를 사용할 예정이다.
3. 간단한 json형태로 id-pass를 관리해도 충분하다.

-------

## 실행 명령어

- 서버 실행: `uv run python app.py`
- 핫리로드 서버 실행: `uv run uvicorn src.server:start_app --factory --reload --host 0.0.0.0 --port 8000`
- 서버 백그라운드 실행: `mkdir -p logs && nohup uv run python app.py > logs/server.log 2>&1 &`
- 서버 백그라운드 로그 확인: `tail -f logs/server.log`
- 서버 백그라운드 프로세스 확인: `ps aux | grep "python app.py"` or `ss -ltnp | grep 5090`
- 서버 백그라운드 중지: `pkill -f "python app.py"`

- 오늘 공고 스크래핑 실행: `uv run python scripts/run_scraping.py`
- 기간 공고 스크래핑 실행: `uv run python scripts/run_scraping.py --start-date 2026-05-22 --end-date 2026-05-29`
- 2025-01~2026-05 제목용 빠른 백필(AI 요약 제외, Linux): `SUMMARIZE_NOTICES=false uv run python scripts/run_scraping.py --start-date 2025-01-01 --end-date 2026-05-31 --max-pages 500`
- 2025-01~2026-05 제목용 빠른 백필(AI 요약 제외, PowerShell): `$env:SUMMARIZE_NOTICES="false"; uv run python scripts/run_scraping.py --start-date 2025-01-01 --end-date 2026-05-31 --max-pages 500`
<!-- - 전체 스크래퍼 백필 실행: `uv run python scripts/backfill_all.py --start-date 2026-06-01 --end-date 2026-06-10`  -->
<!-- - IRIS만 백필 실행: `uv run python scripts/backfill_iris.py --start-date 2026-06-01 --end-date 2026-06-10 --max-pages 5` -->

- 저장된 active 공고 요약 실행: `uv run python scripts/summarize_notices.py --limit 5`
- 특정 source만 요약 실행: `uv run python scripts/summarize_notices.py --source iris_btin_situ --limit 5`
- 이미 요약된 공고까지 강제 재요약: `uv run python scripts/summarize_notices.py --source iris_btin_situ --limit 5 --force`

- 일반/지역공고 마감 정렬/이동 실행: `uv run python scripts/align_expired.py`

- 직전 월 키워드 트렌드 생성: `uv run python scripts/generate_trends.py`
- 특정 월 키워드 트렌드 생성: `uv run python scripts/generate_trends.py --month 2026-06`
- 2025-01~2026-05 월별 키워드 트렌드 생성: `uv run python scripts/generate_trends.py --start-month 2025-01 --end-month 2026-05`
- 특정 월 키워드 트렌드 강제 재생성: `uv run python scripts/generate_trends.py --month 2026-06 --force`

- 지역공고 오늘 수집 실행: `uv run python scripts/run_regional_scraping.py`
- 지역공고 기간 수집 실행: `uv run python scripts/run_regional_scraping.py --start-date 2026-06-01 --end-date 2026-06-10 --max-pages 5`
- 지역공고 상세 포함 수집 실행: `uv run python scripts/run_regional_scraping.py --start-date 2026-06-01 --end-date 2026-06-10 --max-pages 5 --with-detail`
- cron용 어제~오늘 공고 수집 실행: `YESTERDAY=$(date -d "yesterday" +%F); TODAY=$(date +%F); uv run python scripts/run_scraping.py --start-date "$YESTERDAY" --end-date "$TODAY"`
- cron용 어제~오늘 지역공고 수집 실행: `YESTERDAY=$(date -d "yesterday" +%F); TODAY=$(date +%F); uv run python scripts/run_regional_scraping.py --start-date "$YESTERDAY" --end-date "$TODAY" --max-pages 5`
- cron용 어제~오늘 수집 + Google Chat 통합 알림 실행: `uv run python scripts/run_daily_scraping_notify.py`
- 최근 알림 JSON 확인: `cat data/alarm/latest.json`
- Google Chat 알림 URL 설정: `.env`에 `CHAT_API_URL=https://chat.googleapis.com/...`
- 알림 하단 바로가기 설정: `.env`에 `SITE_URL=http://서버주소:8000`
- cron 수정: `crontab -e`
- cron 등록 확인: `crontab -l`
- cron 로그 확인: `tail -f logs/cron-scraping.log`

## 서버 cron 등록 예시

```cron
0 1 * * * cd /home/shield/govscraper/Govscrapper && /home/shield/.local/bin/uv run python scripts/align_expired.py >> logs/cron-align-expired.log 2>&1
0 10 * * * cd /home/shield/govscraper/Govscrapper && /home/shield/.local/bin/uv run python scripts/run_daily_scraping_notify.py >> logs/cron-daily-notify.log 2>&1
10 1 1 * * cd /home/shield/govscraper/Govscrapper && /home/shield/.local/bin/uv run python scripts/generate_trends.py >> logs/cron-generate-trends.log 2>&1
```
