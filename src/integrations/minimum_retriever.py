"""최소 retrieval 구현."""

from __future__ import annotations

from src.integrations.paper_repository import PaperRepository


class MinimumRetriever:
    """FTS/ILIKE 기반의 초기 청크 검색 경로."""

    def __init__(self, *, repository: PaperRepository | None = None) -> None:
        self.repository = repository or PaperRepository()

    def search_paper_chunks(self, query: str, *, limit: int = 5) -> list[dict]:
        """공용 반환 shape로 청크를 조회한다."""
        return self.repository.list_chunk_candidates_by_query(query, limit=limit)

    def search_paper_contexts(
        self,
        query: str,
        *,
        limit: int = 5,
        adjacency_window: int = 1,
    ) -> list[dict]:
        """검색 hit 주변 청크까지 묶어 LLM 입력용 문맥 단위를 반환한다."""
        candidates = self.search_paper_chunks(query, limit=limit)
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
