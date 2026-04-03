"""논문 chunk와 문맥 조회를 담당하는 모듈"""

from __future__ import annotations

from src.integrations.embedding_client import EmbeddingClient
from src.integrations.paper_repository import PaperRepository
from src.integrations.vector_repository import VectorRepository


class PaperRetriever:
    """논문 검색과 RAG용 문맥 구성을 담당하는 retrieval 경로."""

    def __init__(
        self,
        *,
        repository: PaperRepository | None = None,
        embedding_client: EmbeddingClient | None = None,
        vector_repository: VectorRepository | None = None,
    ) -> None:
        self.repository = repository or PaperRepository()
        self.embedding_client = embedding_client or EmbeddingClient()
        self.vector_repository = vector_repository or VectorRepository()

    def search_paper_chunks(
        self,
        query: str,
        *,
        limit: int = 5,
        arxiv_id: str | None = None,
    ) -> list[dict]:
        """공용 반환 shape로 청크를 조회한다."""
        return self.repository.list_chunk_candidates_by_query(query, limit=limit, arxiv_id=arxiv_id)

    def search_paper_contexts(
        self,
        query: str,
        *,
        limit: int = 5,
        adjacency_window: int = 1,
        arxiv_id: str | None = None,
    ) -> list[dict]:
        """검색 hit 주변 청크까지 묶어 LLM 입력용 문맥 단위를 반환한다."""
        candidates = self.search_paper_chunks(query, limit=limit, arxiv_id=arxiv_id)
        return self._build_contexts(candidates, adjacency_window=adjacency_window)

    def search_paper_contexts_by_vector(
        self,
        query: str,
        *,
        arxiv_id: str,
        limit: int = 5,
        adjacency_window: int = 1,
    ) -> list[dict]:
        """특정 논문 안에서만 벡터 검색 후 주변 문맥까지 묶어 반환한다."""
        query_embedding = self.embedding_client.embed_texts([query])[0]
        candidates = self.vector_repository.search_paper_chunks(
            query_embedding,
            limit=limit,
            arxiv_id=arxiv_id,
        )
        return self._build_contexts(candidates, adjacency_window=adjacency_window)

    def _build_contexts(self, candidates: list[dict], *, adjacency_window: int) -> list[dict]:
        """검색 결과를 주변 청크와 결합해 공용 context shape로 정규화한다."""
        normalized_window = max(0, adjacency_window)
        contexts: list[dict] = []
        for candidate in candidates:
            context_chunks = self.repository.list_chunk_window(
                candidate["arxiv_id"],
                int(candidate["chunk_index"]),
                window=normalized_window,
            )
            contexts.append(
                {
                    **candidate,
                    "context_chunks": context_chunks,
                    "context_text": "\n\n".join(chunk["chunk_text"] for chunk in context_chunks if chunk.get("chunk_text")),
                }
            )
        return contexts
