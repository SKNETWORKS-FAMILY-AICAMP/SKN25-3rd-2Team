"""논문 수집 파이프라인 구현."""

from __future__ import annotations

from datetime import date as date_cls
from typing import Any, Optional

from src.integrations.paper_search import PaperSearchClient
from src.integrations.raw_store import RawPaperStore

from .tracing import build_pipeline_trace_config


def run_collect_papers(
    *,
    runtime: str = "airflow",
    user: Optional[str] = None,
    target_date: str | None = None,
) -> dict[str, Any]:
    """HF Daily Papers를 수집하고 MongoDB에 원본을 저장한다."""
    normalized_target_date = (target_date or "").strip() or None
    normalized_date = (
        date_cls.fromisoformat(normalized_target_date).isoformat() if normalized_target_date else date_cls.today().isoformat()
    )

    search_client = PaperSearchClient()
    raw_store = RawPaperStore()

    payload = search_client.fetch_daily_papers(normalized_date)
    record_id = raw_store.save_daily_papers_response(date=normalized_date, payload=payload)

    sample_arxiv_ids = [
        paper.get("paper", {}).get("id")
        for paper in payload
        if isinstance(paper, dict) and isinstance(paper.get("paper"), dict) and paper.get("paper", {}).get("id")
    ][:5]

    trace_config = build_pipeline_trace_config(
        stage="collect_papers",
        runtime=runtime,
        user=user,
        extra_metadata={
            "target_date": normalized_date,
            "fetched_count": len(payload),
            "stored_record_id": record_id,
        },
    )

    return {
        "stage": "collect_papers",
        "status": "success",
        "target_date": normalized_date,
        "fetched_count": len(payload),
        "stored_record_id": record_id,
        "sample_arxiv_ids": sample_arxiv_ids,
        "trace_config": trace_config,
    }
