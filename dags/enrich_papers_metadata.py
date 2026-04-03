"""저장된 논문의 arXiv 메타데이터를 후속 보강하는 DAG 정의."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from airflow.sdk import dag, task

from src.pipeline import run_enrich_papers_metadata


@dag(
    dag_id="arxplore_enrich_papers_metadata",
    schedule="30 20 * * *",
    start_date=datetime(2026, 1, 1, tzinfo=ZoneInfo("Asia/Seoul")),
    catchup=False,
    params={"max_papers": 30},
    tags=["arxplore", "enrich", "papers", "metadata"],
)
def enrich_papers_metadata_dag():
    @task(task_id="run_enrich_papers_metadata")
    def _run(max_papers: str | int | None = None) -> dict:
        normalized_max_papers = int(str(max_papers or "30").strip() or "30")
        return run_enrich_papers_metadata(max_papers=normalized_max_papers)

    _run(max_papers="{{ dag_run.conf.get('max_papers', params.max_papers) if dag_run else params.max_papers }}")


dag = enrich_papers_metadata_dag()
