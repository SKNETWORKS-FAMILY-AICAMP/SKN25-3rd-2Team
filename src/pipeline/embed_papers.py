"""임베딩 생성과 토픽 묶기 단계를 위한 파이프라인 스캐폴드 모듈."""

from __future__ import annotations

from typing import Any, Dict, Optional

from .tracing import build_pipeline_trace_config


def run_embed_papers(*, runtime: str = "airflow", user: Optional[str] = None) -> Dict[str, Any]:
    """임베딩 및 토픽 생성 단계의 실행 메타데이터를 반환합니다."""
    return {
        "stage": "embed_papers",
        "status": "scaffold",
        "trace_config": build_pipeline_trace_config(stage="embed_papers", runtime=runtime, user=user),
    }
