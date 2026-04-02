"""외부 연동 계층 진입점."""

__all__ = [
    "EmbeddingClient",
    "MinimumRetriever",
    "PaperRepository",
    "PaperSearchClient",
    "RawPaperStore",
    "TopicRepository",
    "VectorRepository",
]


def __getattr__(name: str):
    if name == "EmbeddingClient":
        from .embedding_client import EmbeddingClient

        return EmbeddingClient
    if name == "PaperRepository":
        from .paper_repository import PaperRepository

        return PaperRepository
    if name == "MinimumRetriever":
        from .minimum_retriever import MinimumRetriever

        return MinimumRetriever
    if name == "PaperSearchClient":
        from .paper_search import PaperSearchClient

        return PaperSearchClient
    if name == "RawPaperStore":
        from .raw_store import RawPaperStore

        return RawPaperStore
    if name == "TopicRepository":
        from .topic_repository import TopicRepository

        return TopicRepository
    if name == "VectorRepository":
        from .vector_repository import VectorRepository

        return VectorRepository
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
