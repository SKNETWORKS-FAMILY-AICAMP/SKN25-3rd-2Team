"""토픽 문서 생성 파이프라인을 담당하는 모듈"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .tracing import build_pipeline_trace_config


def run_analyze_topics(*, runtime: str = "airflow", user: Optional[str] = None) -> Dict[str, Any]:
    """토픽 문서 생성 단계의 실행 메타데이터를 반환합니다."""
    return {
        "stage": "analyze_topics",
        "status": "scaffold",
        "trace_config": build_pipeline_trace_config(stage="analyze_topics", runtime=runtime, user=user),
    }
