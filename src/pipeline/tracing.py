"""파이프라인 실행 단계의 LangSmith trace 구성을 생성하는 모듈"""

from typing import Any, Dict, Optional

from src.shared import build_langsmith_trace_context


def build_pipeline_trace_config(
    stage: str,
    *,
    runtime: str = "airflow",
    user: Optional[str] = None,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    context = build_langsmith_trace_context(
        stage=stage,
        runtime=runtime,
        user=user,
        extra_tags=["pipeline"],
        extra_metadata=extra_metadata,
    )
    return context.as_langchain_config()
