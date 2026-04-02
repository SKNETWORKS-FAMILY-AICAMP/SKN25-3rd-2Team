"""논문 전처리 DAG."""

from __future__ import annotations

from datetime import datetime

from airflow.sdk import dag, task

from src.pipeline import run_prepare_papers


@dag(
    dag_id="arxplore_prepare_papers",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    params={"target_date": "", "max_papers": ""},
    tags=["arxplore", "prepare", "papers"],
)
def prepare_papers_dag():
    @task(task_id="run_prepare_papers")
    def _run(target_date: str | None = None, max_papers: str | None = None) -> dict:
        return run_prepare_papers(target_date=target_date, max_papers=max_papers)

    _run(
        target_date="{{ dag_run.conf.get('target_date', params.target_date) if dag_run else params.target_date }}",
        max_papers="{{ dag_run.conf.get('max_papers', params.max_papers) if dag_run else params.max_papers }}",
    )


dag = prepare_papers_dag()
