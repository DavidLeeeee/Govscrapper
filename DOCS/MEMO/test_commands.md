# 테스트 명령어

## IRIS 넓은 범위 테스트

PowerShell에서 실행한다.

```powershell
uv run python -c "from datetime import date; from src.contracts.scrape_options import ScrapeOptions; from src.scrapers._iris import IrisBtinSituScraper; items=IrisBtinSituScraper(max_pages=1).scrape(ScrapeOptions.backfill(date(2026, 5, 1), date.today())); print(len(items)); print(items[:2])"
```

`uv`가 PATH에 잡히지 않으면 아래 명령을 사용한다.

```powershell
& 'C:\Users\david\AppData\Local\com.LangflowDesktop\uv\uv.exe' run python -c "from datetime import date; from src.contracts.scrape_options import ScrapeOptions; from src.scrapers._iris import IrisBtinSituScraper; items=IrisBtinSituScraper(max_pages=1).scrape(ScrapeOptions.backfill(date(2026, 5, 1), date.today())); print(len(items)); print(items[:2])"
```

날짜 범위를 바꾸려면 `date(2026, 5, 1)` 부분을 수정한다.

## IRIS 넓은 범위 저장 테스트

위 명령은 화면 출력만 확인한다.

실제 `data/sources/iris_btin_situ/`, `data/active/iris_btin_situ/items.json`에 저장하려면 아래 명령을 실행한다.

```powershell
uv run python scripts\backfill_iris.py --start-date 2026-05-01 --max-pages 1
```

`uv`가 PATH에 잡히지 않으면 아래 명령을 사용한다.

```powershell
& 'C:\Users\david\AppData\Local\com.LangflowDesktop\uv\uv.exe' run python scripts\backfill_iris.py --start-date 2026-05-01 --max-pages 1
```
