"""과거 HF Daily Papers 원본을 단계적으로 채우는 DAG 정의."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from airflow.sdk import dag, task

from src.pipeline import run_backfill_collect_papers


@dag(
    dag_id="arxplore_backfill_collect_papers",
    schedule="0 19 * * *",
    start_date=datetime(2026, 1, 1, tzinfo=ZoneInfo("Asia/Seoul")),
    catchup=False,
    params={
        "cursor_date": "",
        "oldest_date": "",
        "batch_days": 30,
        "state_name": "default",
    },
    tags=["arxplore", "collect", "papers", "backfill"],
)
def backfill_collect_papers_dag():
    @task(task_id="run_backfill_collect_papers")
    def _run(
        cursor_date: str | None = None,
        oldest_date: str | None = None,
        batch_days: str | int | None = None,
        state_name: str | None = None,
    ) -> dict:
        normalized_batch_days = int(str(batch_days or "30").strip() or "30")
        normalized_state_name = (state_name or "").strip() or "default"
        return run_backfill_collect_papers(
            cursor_date=(cursor_date or "").strip() or None,
            oldest_date=(oldest_date or "").strip() or None,
            batch_days=normalized_batch_days,
            state_name=normalized_state_name,
        )

    _run(
        cursor_date="{{ dag_run.conf.get('cursor_date', params.cursor_date) if dag_run else params.cursor_date }}",
        oldest_date="{{ dag_run.conf.get('oldest_date', params.oldest_date) if dag_run else params.oldest_date }}",
        batch_days="{{ dag_run.conf.get('batch_days', params.batch_days) if dag_run else params.batch_days }}",
        state_name="{{ dag_run.conf.get('state_name', params.state_name) if dag_run else params.state_name }}",
    )


dag = backfill_collect_papers_dag()
