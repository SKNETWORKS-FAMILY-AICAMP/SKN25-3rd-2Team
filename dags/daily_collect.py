"""서버 일일 수집 자동화 DAG를 담당하는 모듈"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from airflow.sdk import dag, task

from src.pipeline import run_collect_papers


@dag(
    dag_id="arxplore_daily_collect",
    schedule="0 18 * * *",
    start_date=datetime(2026, 1, 1, tzinfo=ZoneInfo("Asia/Seoul")),
    catchup=False,
    params={"target_date": ""},
    tags=["arxplore", "collect", "papers"],
)
def daily_collect_dag():
    @task(task_id="run_collect_papers")
    def _run(target_date: str | None = None) -> dict:
        return run_collect_papers(target_date=(target_date or "").strip() or None)

    _run(target_date="{{ dag_run.conf.get('target_date', params.target_date) if dag_run else params.target_date }}")


daily_collect = daily_collect_dag()
