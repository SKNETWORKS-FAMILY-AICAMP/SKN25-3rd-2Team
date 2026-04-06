"""토픽과 토픽 문서 저장 계층을 담당하는 모듈"""

from __future__ import annotations

from src.core.models import TopicDocument


class TopicRepository:
    """토픽 메타데이터와 `TopicDocument`를 저장하고 조회하는 진입점."""

    def save_topic(self, topic_id: int, title: str, keywords: list[str] | None = None) -> int:
        """토픽 메타데이터를 저장하고 topic_id를 반환한다."""
        raise NotImplementedError("토픽 메타데이터 저장은 저장 담당자가 구현할 예정입니다.")

    def save_topic_papers(self, topic_id: int, arxiv_ids: list[str]) -> None:
        """토픽과 논문 간 매핑을 저장한다."""
        raise NotImplementedError("토픽-논문 매핑 저장은 저장 담당자가 구현할 예정입니다.")

    def save_topic_document(self, document: TopicDocument) -> int:
        """토픽 문서를 저장하고 topic_id를 반환한다."""
        raise NotImplementedError("토픽 문서 저장은 저장 담당자가 구현할 예정입니다.")

    def get_topic_document(self, topic_id: int) -> TopicDocument | None:
        """단일 토픽 문서를 조회한다."""
        raise NotImplementedError("토픽 문서 조회는 저장 담당자가 구현할 예정입니다.")

    def list_topic_documents(self, *, limit: int = 20) -> list[TopicDocument]:
        """메인 화면 카드 섹션에 사용할 토픽 문서 목록을 조회한다."""
        raise NotImplementedError("토픽 목록 조회는 저장 담당자가 구현할 예정입니다.")