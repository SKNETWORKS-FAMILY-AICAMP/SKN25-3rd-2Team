"""지정한 날짜 범위의 HF Daily Papers 원본을 MongoDB에 순차 적재한다."""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.pipeline.collect_papers import run_collect_papers


def _iter_dates(start_date: date, end_date: date) -> list[date]:
    if start_date > end_date:
        raise ValueError("start_date는 end_date보다 늦을 수 없습니다.")
    current = start_date
    dates: list[date] = []
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    return dates


def _is_rate_limited_error(exc: Exception) -> bool:
    message = str(exc)
    return "429" in message or "Too Many Requests" in message


def _extract_error_url(exc: Exception) -> str | None:
    message = str(exc)
    marker = "url: "
    start = message.find(marker)
    if start == -1:
        return None
    return message[start + len(marker) :].strip() or None


def _format_rate_limit_context(exc: Exception) -> str:
    error_url = _extract_error_url(exc)
    if not error_url:
        return "HF Daily Papers"
    parsed = urlparse(error_url)
    return parsed.netloc or "HF Daily Papers"


def main() -> int:
    parser = argparse.ArgumentParser(description="날짜 범위 기준으로 HF Daily Papers raw를 백필한다.")
    parser.add_argument("--start-date", required=True, help="시작 날짜 (YYYY-MM-DD)")
    parser.add_argument("--end-date", required=True, help="종료 날짜 (YYYY-MM-DD)")
    parser.add_argument(
        "--sleep-seconds",
        type=float,
        default=0.5,
        help="각 날짜 요청 사이에 둘 대기 시간(초). 기본값은 0.5초다.",
    )
    parser.add_argument(
        "--max-rate-limit-retries",
        type=int,
        default=3,
        help="429 응답에 대해 날짜별로 재시도할 최대 횟수다. 기본값은 3회다.",
    )
    parser.add_argument(
        "--rate-limit-sleep-seconds",
        type=float,
        default=30.0,
        help="429 응답 후 첫 재시도 전 대기 시간(초)이다. 기본값은 30초다.",
    )
    parser.add_argument(
        "--rate-limit-backoff",
        type=float,
        default=2.0,
        help="429 응답 재시도 간격에 곱할 backoff 배수다. 기본값은 2.0이다.",
    )
    args = parser.parse_args()

    start_date = date.fromisoformat(args.start_date)
    end_date = date.fromisoformat(args.end_date)
    target_dates = _iter_dates(start_date, end_date)

    successes: list[dict[str, object]] = []
    failures: list[dict[str, str]] = []

    for index, target in enumerate(target_dates, start=1):
        target_str = target.isoformat()
        attempts = 0
        max_attempts = max(1, args.max_rate_limit_retries + 1)

        while attempts < max_attempts:
            attempts += 1
            try:
                result = run_collect_papers(runtime="local", user="codex", target_date=target_str)
                successes.append(
                    {
                        "date": target_str,
                        "fetched_count": int(result.get("fetched_count", 0) or 0),
                        "stored_record_id": str(result.get("stored_record_id") or ""),
                    }
                )
                retry_note = f" retries={attempts - 1}" if attempts > 1 else ""
                print(
                    f"[{index}/{len(target_dates)}] success {target_str} "
                    f"fetched={result.get('fetched_count', 0)}{retry_note}"
                )
                break
            except Exception as exc:  # pragma: no cover - operational path
                should_retry = _is_rate_limited_error(exc) and attempts < max_attempts
                if not should_retry:
                    failures.append({"date": target_str, "error": str(exc)})
                    print(f"[{index}/{len(target_dates)}] failed  {target_str} error={exc}")
                    break

                sleep_seconds = args.rate_limit_sleep_seconds * (
                    args.rate_limit_backoff ** (attempts - 1)
                )
                source_name = _format_rate_limit_context(exc)
                print(
                    f"[{index}/{len(target_dates)}] retry   {target_str} "
                    f"attempt={attempts}/{max_attempts - 1} source={source_name} "
                    f"sleep={sleep_seconds:.1f}s"
                )
                time.sleep(max(0.0, sleep_seconds))

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
