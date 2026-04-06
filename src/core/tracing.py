"""토픽 분석 체인의 LangSmith trace 구성을 생성하는 모듈"""

from typing import Any, Dict, Optional
from src.shared import build_langsmith_trace_context

def build_analysis_trace_config(
    *,
    stage: str = "analyze_topic",
    runtime: str = "dev",
    user: Optional[str] = None,
    quality_score: Optional[float] = None,
    eval_tags: Optional[list[str]] = None,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """토픽 분석 체인의 LangSmith trace 설정을 생성합니다.
    
    Args:
        stage: 실행 단계 ("analyze_topic", "overview", "key_findings" 등). 기본값: "analyze_topic"
        runtime: 실행 환경 ("dev", "airflow", "local" 등). 기본값: "dev"
        user: 실행 사용자 ID (선택, LangSmith에 기록). 기본값: None
        quality_score: 평가 점수 (0.0~1.0, 선택, 평가 루프용). 기본값: None
        eval_tags: 평가 태그 (["high_quality", "needs_review"] 등, 선택). 기본값: None
        extra_metadata: 추가 메타데이터 (dict, 선택). 기본값: None
    
    Returns:
        Dict[str, Any]: LangChain .invoke()의 config 파라미터로 전달할 설정
    
    Raises:
        ValueError: stage, runtime, quality_score가 유효하지 않은 경우
    
    Example:
        >>> config = build_analysis_trace_config(
        ...     stage="overview",
        ...     runtime="dev",
        ...     user="user123",
        ...     quality_score=0.85,
        ...     eval_tags=["high_quality"]
        ... )
        >>> chain.invoke({"papers": data}, config=config)
    """
    # 입력값 검증
    valid_stages = {
        "analyze_topic",
        "overview",
        "key_findings",
        "topic_document",
        "translation",
        "detailed_summary",
        "analyze_paper_detail",
        "paper_overview",
        "paper_key_findings",
        "paper_detail_document",
    }
    if stage not in valid_stages:
        raise ValueError(f"stage는 {valid_stages} 중 하나여야 합니다. 받은 값: {stage}")
    
    valid_runtimes = {"dev", "airflow", "local", "test"}
    if runtime not in valid_runtimes:
        raise ValueError(f"runtime은 {valid_runtimes} 중 하나여야 합니다. 받은 값: {runtime}")
    
    if quality_score is not None and not (0.0 <= quality_score <= 1.0):
        raise ValueError(f"quality_score는 0.0~1.0 사이여야 합니다. 받은 값: {quality_score}")
    
    # 메타데이터 구성
    merged_metadata = extra_metadata or {}
    
    # 평가 정보 추가 (평가 루프용)
    if quality_score is not None:
        merged_metadata["quality_score"] = quality_score
    
    if eval_tags:
        merged_metadata["eval_tags"] = eval_tags
    
    # 기본 태그 설정 (stage별로 구분)
    base_tags = ["llm", "analysis", stage]
    if quality_score is not None and quality_score >= 0.8:
        base_tags.append("high_quality")
    elif quality_score is not None and quality_score < 0.5:
        base_tags.append("needs_review")
    
    try:
        context = build_langsmith_trace_context(
            stage=stage,
            runtime=runtime,
            user=user,
            extra_tags=base_tags,
            extra_metadata=merged_metadata,
        )
        return context.as_langchain_config()
    except Exception as e:
        raise RuntimeError(f"LangSmith trace 설정 생성 실패: {e}") from e

def build_overview_trace_config(
    *,
    runtime: str = "dev",
    user: Optional[str] = None,
    quality_score: Optional[float] = None,
) -> Dict[str, Any]:
    """토픽 개요 생성을 위한 trace 설정 (편의 함수).
    
    Args:
        runtime: 실행 환경. 기본값: "dev"
        user: 실행 사용자 ID. 기본값: None
        quality_score: 개요 품질 점수 (0.0~1.0). 기본값: None
    
    Returns:
        Dict[str, Any]: LangChain config
    """
    return build_analysis_trace_config(
        stage="overview",
        runtime=runtime,
        user=user,
        quality_score=quality_score,
    )

def build_key_findings_trace_config(
    *,
    runtime: str = "dev",
    user: Optional[str] = None,
    quality_score: Optional[float] = None,
) -> Dict[str, Any]:
    """토픽 핵심 발견 생성을 위한 trace 설정 (편의 함수).
    
    Args:
        runtime: 실행 환경. 기본값: "dev"
        user: 실행 사용자 ID. 기본값: None
        quality_score: 핵심 발견 품질 점수 (0.0~1.0). 기본값: None
    
    Returns:
        Dict[str, Any]: LangChain config
    """
    return build_analysis_trace_config(
        stage="key_findings",
        runtime=runtime,
        user=user,
        quality_score=quality_score,
    )


def build_paper_overview_trace_config(
    *,
    runtime: str = "dev",
    user: Optional[str] = None,
    quality_score: Optional[float] = None,
) -> Dict[str, Any]:
    return build_analysis_trace_config(
        stage="paper_overview",
        runtime=runtime,
        user=user,
        quality_score=quality_score,
    )


def build_paper_key_findings_trace_config(
    *,
    runtime: str = "dev",
    user: Optional[str] = None,
    quality_score: Optional[float] = None,
) -> Dict[str, Any]:
    return build_analysis_trace_config(
        stage="paper_key_findings",
        runtime=runtime,
        user=user,
        quality_score=quality_score,
    )


def build_translation_trace_config(
    *,
    runtime: str = "dev",
    user: Optional[str] = None,
    quality_score: Optional[float] = None,
) -> Dict[str, Any]:
    return build_analysis_trace_config(
        stage="translation",
        runtime=runtime,
        user=user,
        quality_score=quality_score,
    )


def build_detailed_summary_trace_config(
    *,
    runtime: str = "dev",
    user: Optional[str] = None,
    quality_score: Optional[float] = None,
) -> Dict[str, Any]:
    return build_analysis_trace_config(
        stage="detailed_summary",
        runtime=runtime,
        user=user,
        quality_score=quality_score,
    )
