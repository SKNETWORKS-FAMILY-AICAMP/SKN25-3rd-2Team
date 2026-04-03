"""날짜 범위 기준으로 prepare_papers를 순차 실행하고 결과를 기록한다."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.pipeline.prepare_papers import run_prepare_papers


def _iter_dates(start_date: date, end_date: date) -> list[date]:
    if start_date < end_date:
        raise ValueError("start_date는 end_date보다 같거나 늦어야 합니다.")

    current = start_date
    dates: list[date] = []
    while current >= end_date:
        dates.append(current)
        current -= timedelta(days=1)
    return dates


def main() -> int:
    parser = argparse.ArgumentParser(description="날짜 범위 기준으로 prepare_papers를 순차 실행한다.")
    parser.add_argument("--start-date", required=True, help="시작 날짜 (YYYY-MM-DD)")
    parser.add_argument("--end-date", required=True, help="종료 날짜 (YYYY-MM-DD)")
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=5.0,
        help="날짜별 실행 사이에 둘 대기 시간(초). 기본값은 5초다.",
    )
    parser.add_argument(
        "--max-papers",
        default="",
        help="run_prepare_papers에 전달할 max_papers 값이다. 비우면 해당 날짜 전체를 사용한다.",
    )
    args = parser.parse_args()

    start_date = date.fromisoformat(args.start_date)
    end_date = date.fromisoformat(args.end_date)
    target_dates = _iter_dates(start_date, end_date)

    successes: list[dict[str, object]] = []
    failures: list[dict[str, str]] = []

    for index, target in enumerate(target_dates, start=1):
        target_str = target.isoformat()
        try:
            result = run_prepare_papers(
                runtime="local",
                user="codex",
                target_date=target_str,
                max_papers=args.max_papers or None,
            )
            summary = {
                "date": target_str,
                "saved_papers": int(result.get("saved_papers", 0) or 0),
                "saved_fulltexts": int(result.get("saved_fulltexts", 0) or 0),
                "saved_chunks": int(result.get("saved_chunks", 0) or 0),
                "fallback_fulltexts": int(result.get("fallback_fulltexts", 0) or 0),
                "selected_candidate_count": int(result.get("selected_candidate_count", 0) or 0),
            }
            successes.append(summary)
            print(f"[{index}/{len(target_dates)}] success {target_str} {summary}")
        except Exception as exc:  # pragma: no cover - operational path
            failures.append({"date": target_str, "error": str(exc)})
            print(f"[{index}/{len(target_dates)}] failed  {target_str} error={exc}")

        if index < len(target_dates) and args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)

    summary = {
        "start_date": args.start_date,
        "end_date": args.end_date,
        "requested_days": len(target_dates),
        "success_count": len(successes),
        "failure_count": len(failures),
        "failures": failures,
    }
    print()
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
