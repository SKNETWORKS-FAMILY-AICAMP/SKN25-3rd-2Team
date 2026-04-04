"""논문 chunk와 문맥 조회를 담당하는 모듈"""

from __future__ import annotations

import re

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
        arxiv_id: str | None = None,
        limit: int = 5,
        adjacency_window: int = 1,
    ) -> list[dict]:
        """벡터 검색 후 주변 문맥까지 묶어 반환한다. arxiv_id를 주면 해당 논문 내로 한정한다."""
        query_embedding = self.embedding_client.embed_texts([query])[0]
        candidates = self.vector_repository.search_paper_chunks(
            query_embedding,
            limit=limit,
            arxiv_id=arxiv_id,
        )
        candidates = self._rerank_vector_candidates(query, candidates)
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

    def _rerank_vector_candidates(self, query: str, candidates: list[dict]) -> list[dict]:
        """벡터 검색 결과를 섹션 prior와 lexical overlap으로 한 번 더 정렬한다."""
        query_tokens = self._query_tokens(query)
        query_lowered = query.lower()
        appendix_requested = any(keyword in query_lowered for keyword in ("appendix", "supplement", "additional analysis"))
        conclusion_requested = any(keyword in query_lowered for keyword in ("conclusion", "limitation", "discussion"))
        reference_requested = any(keyword in query_lowered for keyword in ("reference", "bibliography", "citation"))

        reranked: list[dict] = []
        for candidate in candidates:
            section_title = str(candidate.get("section_title") or "")
            section_lowered = section_title.lower()
            chunk_text = str(candidate.get("chunk_text") or "")
            content_role = str(candidate.get("content_role") or "")
            overlap_bonus = self._lexical_overlap_bonus(query_tokens, f"{section_title} {chunk_text}")

            rerank_adjustment = overlap_bonus
            if not appendix_requested and any(
                keyword in section_lowered
                for keyword in ("appendix", "additional analysis", "supplementary", "experimental details", "implementation details")
            ):
                rerank_adjustment -= 0.08
            if not conclusion_requested and any(keyword in section_lowered for keyword in ("conclusion", "discussion", "limitations")):
                rerank_adjustment -= 0.03
            if not reference_requested and any(keyword in section_lowered for keyword in ("reference", "bibliography", "acknowledg")):
                rerank_adjustment -= 0.18
            if content_role in {"front_matter", "table_like"}:
                rerank_adjustment -= 0.02
            if not reference_requested and self._looks_reference_like_text(chunk_text):
                rerank_adjustment -= 0.14

            reranked.append(
                {
                    **candidate,
                    "similarity_score": float(candidate.get("similarity_score") or 0.0) + rerank_adjustment,
                    "rerank_adjustment": rerank_adjustment,
                }
            )

        return sorted(reranked, key=lambda item: (float(item.get("similarity_score") or 0.0), int(item.get("chunk_id") or 0)), reverse=True)

    @staticmethod
    def _query_tokens(query: str) -> set[str]:
        """짧은 영문 질의에서 의미 있는 토큰만 뽑는다."""
        return {
            token
            for token in re.findall(r"[a-z0-9]+", query.lower())
            if len(token) >= 3 and token not in {"the", "and", "for", "with", "from", "that", "this"}
        }

    @staticmethod
    def _lexical_overlap_bonus(query_tokens: set[str], text: str) -> float:
        """질의 토큰이 chunk에 얼마나 직접 등장하는지 계산한다."""
        if not query_tokens:
            return 0.0

        text_tokens = set(re.findall(r"[a-z0-9]+", text.lower()))
        if not text_tokens:
            return 0.0

        overlap = len(query_tokens & text_tokens)
        if overlap == 0:
            return 0.0

        return min(0.12, 0.03 * overlap)

    @staticmethod
    def _looks_reference_like_text(text: str) -> bool:
        """본문 검색에서 제외해야 할 reference-like 청크를 감지한다."""
        compact = " ".join(text.split())[:1200]
        if not compact:
            return False

        reference_markers = len(re.findall(r"\[\d+\]", compact))
        year_markers = len(re.findall(r"\b(?:19|20)\d{2}\b", compact))
        venue_markers = len(
            re.findall(
                r"\b(?:arXiv preprint|Proceedings|Conference|CVPR|ICCV|ECCV|NeurIPS|ICLR|ACL|EMNLP|AAAI)\b",
                compact,
                re.IGNORECASE,
            )
        )
        author_list_like = bool(
            re.match(
                r"^(?:[A-Z][A-Za-z'`.-]+,\s+[A-Z](?:\.[A-Z])?(?:,\s+[A-Z][A-Za-z'`.-]+,\s+[A-Z](?:\.[A-Z])?){1,}|(?:\[\d+\]\s*)?[A-Z][A-Za-z'`.-]+,)",
                compact,
            )
        )

        if reference_markers >= 3:
            return True
        if reference_markers >= 2 and year_markers >= 2:
            return True
        if venue_markers >= 2 and year_markers >= 2:
            return True
        if author_list_like and year_markers >= 1 and venue_markers >= 1:
            return True
        return False
