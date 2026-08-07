# 서버 프로세스 자동 실행/재시작 설정

서버가 재부팅되거나 `app.py` 프로세스가 죽었을 때 자동으로 다시 실행되도록 `systemd` 서비스로 등록한다.

## 서비스 파일 생성

```bash
sudo nano /etc/systemd/system/govscraper.service
```

```ini
[Unit]
Description=GovScraper FastAPI Server
After=network.target

[Service]
Type=simple
User=shield
WorkingDirectory=/home/shield/govscraper/Govscrapper
Environment="PATH=/home/shield/.local/bin:/home/shield/govscraper/Govscrapper/.venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/shield/.local/bin/uv run python app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## 서비스 등록/시작

```bash
sudo systemctl daemon-reload
sudo systemctl enable govscraper
sudo systemctl start govscraper
```

## 상태 확인

```bash
sudo systemctl status govscraper
```

## 로그 확인

```bash
journalctl -u govscraper -f
```

최근 로그만 확인:

```bash
journalctl -u govscraper -n 100
```

## 재시작/중지

```bash
sudo systemctl restart govscraper
sudo systemctl stop govscraper
```

## 코드 수정 후 반영

코드를 `git pull` 등으로 갱신한 뒤 서버를 재시작한다.

```bash
cd /home/shield/govscraper/Govscrapper
sudo systemctl restart govscraper
```

## 서비스 파일 수정 후 반영

`ExecStart`, `WorkingDirectory`, `Environment` 등을 수정했다면 `daemon-reload` 후 재시작한다.

```bash
sudo nano /etc/systemd/system/govscraper.service
sudo systemctl daemon-reload
sudo systemctl restart govscraper
```

## 자동 시작 해제

재부팅 시 자동 실행만 끈다.

```bash
sudo systemctl disable govscraper
```

## 서비스 삭제

```bash
sudo systemctl stop govscraper
sudo systemctl disable govscraper
sudo rm /etc/systemd/system/govscraper.service
sudo systemctl daemon-reload
sudo systemctl reset-failed
```

## uv 경로 확인

`uv` 경로가 다르면 서비스 파일의 `ExecStart`와 `Environment`를 수정한다.

```bash
which uv
ls -l /home/shield/.local/bin/uv
```

## 포트 확인

서버가 실제로 떠 있는지 확인한다.

```bash
ss -ltnp | grep 5090
```

포트가 다르면 `.env` 또는 서버 설정의 포트 값을 확인한다.
