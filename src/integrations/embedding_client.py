"""임베딩 생성 계층의 기본 뼈대를 담은 모듈."""

from __future__ import annotations

from collections.abc import Sequence


class EmbeddingClient:
    """문자열 목록을 임베딩 벡터로 변환하는 진입점."""

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """텍스트 목록을 벡터 목록으로 변환한다."""
        raise NotImplementedError("임베딩 생성은 저장 담당자 또는 LLM 담당자가 구현할 예정입니다.")
