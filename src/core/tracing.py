"""토픽 분석 체인의 LangSmith trace 구성을 생성하는 모듈"""

from typing import Any, Dict, Optional

from src.shared import build_langsmith_trace_context


def build_analysis_trace_config(
    *,
    runtime: str,
    user: Optional[str] = None,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    context = build_langsmith_trace_context(
        stage="analyze",
        runtime=runtime,
        user=user,
        extra_tags=["llm", "summary", "topic-analysis"],
        extra_metadata=extra_metadata,
    )
    return context.as_langchain_config()
