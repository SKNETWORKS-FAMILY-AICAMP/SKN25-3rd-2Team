"""서버 백필과 메타데이터 보강 자동화 DAG를 담당하는 모듈"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from airflow.utils.trigger_rule import TriggerRule
from airflow.sdk import dag, task

from src.pipeline import run_backfill_collect_papers, run_enrich_papers_metadata


@dag(
    dag_id="arxplore_maintenance",
    schedule="0 */3 * * *",
    start_date=datetime(2026, 1, 1, tzinfo=ZoneInfo("Asia/Seoul")),
    catchup=False,
    params={
        "backfill_cursor_date": "",
        "backfill_oldest_date": "",
        "backfill_batch_days": 30,
        "backfill_state_name": "default",
        "enrich_max_papers": 30,
    },
    tags=["arxplore", "backfill", "enrich", "papers"],
)
def maintenance_dag():
    @task(task_id="run_backfill_collect_papers")
    def _run_backfill(
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

    @task(task_id="run_enrich_papers_metadata", trigger_rule=TriggerRule.ALL_DONE)
    def _run_enrich(max_papers: str | int | None = None) -> dict:
        normalized_max_papers = int(str(max_papers or "30").strip() or "30")
        return run_enrich_papers_metadata(max_papers=normalized_max_papers)

    backfill = _run_backfill(
        cursor_date="{{ dag_run.conf.get('backfill_cursor_date', params.backfill_cursor_date) if dag_run else params.backfill_cursor_date }}",
        oldest_date="{{ dag_run.conf.get('backfill_oldest_date', params.backfill_oldest_date) if dag_run else params.backfill_oldest_date }}",
        batch_days="{{ dag_run.conf.get('backfill_batch_days', params.backfill_batch_days) if dag_run else params.backfill_batch_days }}",
        state_name="{{ dag_run.conf.get('backfill_state_name', params.backfill_state_name) if dag_run else params.backfill_state_name }}",
    )
    enrich = _run_enrich(
        max_papers="{{ dag_run.conf.get('enrich_max_papers', params.enrich_max_papers) if dag_run else params.enrich_max_papers }}"
    )
    backfill >> enrich


maintenance = maintenance_dag()
