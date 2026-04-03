"""토픽 문서 생성을 오케스트레이션하는 DAG 스캐폴드."""

from __future__ import annotations

from datetime import datetime

from airflow.sdk import dag, task

from src.pipeline import run_analyze_topics


@dag(
    dag_id="arxplore_analyze_topics",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["arxplore", "analyze", "topics", "scaffold"],
)
def analyze_topics_dag():
    @task(task_id="run_analyze_topics")
    def _run() -> dict:
        return run_analyze_topics()

    _run()


dag = analyze_topics_dag()
