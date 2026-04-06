"""외부 연동 계층의 주요 구현을 노출하는 진입점 모듈"""

__all__ = [
    "EmbeddingClient",
    "PaperRetriever",
    "PrepareJobRepository",
    "PaperRepository",
    "PaperSearchClient",
    "RawPaperStore",
    "VectorRepository",
]


def __getattr__(name: str):
    if name == "EmbeddingClient":
        from .embedding_client import EmbeddingClient

        return EmbeddingClient
    if name == "PaperRepository":
        from .paper_repository import PaperRepository

        return PaperRepository
    if name == "PaperRetriever":
        from .paper_retriever import PaperRetriever

        return PaperRetriever
    if name == "PrepareJobRepository":
        from .prepare_job_repository import PrepareJobRepository

        return PrepareJobRepository
    if name == "PaperSearchClient":
        from .paper_search import PaperSearchClient

        return PaperSearchClient
    if name == "RawPaperStore":
        from .raw_store import RawPaperStore

        return RawPaperStore
    if name == "VectorRepository":
        from .vector_repository import VectorRepository

        return VectorRepository
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
