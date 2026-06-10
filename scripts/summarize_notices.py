import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.services.file_lock import file_lock
from src.services.storage_service import atomic_write_json, read_json_list
from src.services.summarization_service import build_openai_summarizer, summarize_notices
from src.settings import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="저장된 active 공고 상세 페이지를 OpenAI API로 요약한다.")
    parser.add_argument("--source", help="특정 source만 처리한다. 예: iris_btin_situ")
    parser.add_argument("--limit", type=int, default=5, help="이번 실행에서 요약을 시도할 최대 공고 수")
    parser.add_argument("--force", action="store_true", help="이미 summary가 있는 공고도 다시 요약한다.")
    args = parser.parse_args()

    settings = get_settings()
    summarizer = build_openai_summarizer(
        api_key=settings.openai_api_key,
        model=settings.openai_summary_model,
        max_detail_chars=settings.summary_max_detail_chars,
        max_output_tokens=settings.summary_max_output_tokens,
    )
    if summarizer is None:
        raise RuntimeError("OPENAI_API_KEY가 .env에 설정되어 있지 않습니다.")

    remaining = args.limit
    result = {"files": {}, "attempted_count": 0, "summarized_count": 0, "skipped_count": 0, "error_count": 0}
    paths = sorted((settings.data_dir / "active").glob("*/items.json"))
    if args.source:
        paths = [path for path in paths if path.parent.name == args.source]

    lock_path = settings.runtime_dir / "locks" / "summarize_notices.lock"
    with file_lock(lock_path):
        for path in paths:
            if remaining <= 0:
                break

            print(f"[file] {path}", flush=True)
            notices = read_json_list(path)
            updated_notices, stats = summarize_notices(
                notices,
                summarizer,
                limit=remaining,
                on_progress=lambda message: print(message, flush=True),
                force=args.force,
            )
            atomic_write_json(path, updated_notices)
            remaining -= stats["attempted_count"]

            result["files"][str(path)] = stats
            result["attempted_count"] += stats["attempted_count"]
            result["summarized_count"] += stats["summarized_count"]
            result["skipped_count"] += stats["skipped_count"]
            result["error_count"] += stats["error_count"]

    print(result, flush=True)


if __name__ == "__main__":
    main()
