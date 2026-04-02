"""논문 수집 DAG."""

from __future__ import annotations

from datetime import datetime

from airflow.sdk import dag, task

from src.pipeline import run_collect_papers


@dag(
    dag_id="arxplore_collect_papers",
    schedule="10 16 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    params={"target_date": ""},
    tags=["arxplore", "collect", "papers"],
)
def collect_papers_dag():
    @task(task_id="run_collect_papers")
    def _run(target_date: str | None = None) -> dict:
        return run_collect_papers(target_date=target_date)

    _run(target_date="{{ dag_run.conf.get('target_date', params.target_date) if dag_run else params.target_date }}")


dag = collect_papers_dag()
