"""RAG 응답 체인 뼈대."""

from __future__ import annotations
from typing import Any, Optional
from .models import TopicDocument


def answer_question(question: str,*,context_papers: list[dict[str, Any]],context_documents: list[TopicDocument],runtime: str = "dev",user: Optional[str] = None,) -> dict[str, Any]:
    """검색 결과를 바탕으로 답변, 근거 논문, 관련 토픽을 조합하는 진입점.

    LLM · RAG 담당자는 이 함수를 기준으로 Retriever 결과와 LLM 응답을 연결한다.
    최소 반환 구조는 `answer`, `source_papers`, `related_topics`를 포함하는 형태를 권장한다.
    """

    raise NotImplementedError("RAG 응답 체인은 LLM · RAG 담당자가 구현할 예정입니다.")
