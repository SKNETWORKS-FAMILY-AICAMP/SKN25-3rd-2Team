"""논문 전처리 파이프라인 구현."""

from __future__ import annotations

from datetime import date as date_cls
from typing import Any, Dict, Optional

from src.integrations.fulltext_parser import FulltextParser
from src.integrations.paper_repository import PaperRepository
from src.integrations.paper_search import PaperSearchClient
from src.integrations.raw_store import RawPaperStore
from .tracing import build_pipeline_trace_config

DEFAULT_ALLOWED_CATEGORIES = {"cs.AI", "cs.CL", "cs.CV", "cs.LG", "cs.RO", "stat.ML"}


def _normalize_optional_date(value: str | None) -> str | None:
    normalized = (value or "").strip()
    return normalized or None


def _normalize_optional_positive_int(value: int | str | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    normalized = str(value).strip()
    if not normalized:
        return None
    parsed = int(normalized)
    return parsed if parsed > 0 else None


def _extract_candidate_arxiv_id(item: dict[str, Any]) -> str | None:
    paper = item.get("paper")
    if isinstance(paper, dict):
        for key in ("id", "arxivId", "arxiv_id"):
            value = paper.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    for key in ("id", "arxivId", "arxiv_id"):
        value = item.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _extract_hf_signals(item: dict[str, Any]) -> dict[str, Any]:
    paper = item.get("paper")
    if not isinstance(paper, dict):
        paper = {}
    upvotes = item.get("upvotes", paper.get("upvotes", 0))
    github = item.get("github", paper.get("github", {}))
    github_url = None
    github_stars = None
    if isinstance(github, dict):
        github_url = github.get("url") or github.get("repoUrl") or github.get("repository")
        github_stars = github.get("stars")
    return {
        "upvotes": int(upvotes or 0),
        "github_url": github_url,
        "github_stars": int(github_stars) if github_stars is not None else None,
    }


def _is_allowed_category(metadata: dict[str, Any], *, allowed: set[str]) -> bool:
    categories = metadata.get("categories") or []
    if isinstance(categories, list):
        category_set = {str(value) for value in categories if value}
    else:
        category_set = set()

    primary = metadata.get("primary_category")
    if primary:
        category_set.add(str(primary))

    return any(category in allowed for category in category_set)


def run_prepare_papers(
    *,
    runtime: str = "airflow",
    user: Optional[str] = None,
    target_date: str | None = None,
    allowed_categories: set[str] | None = None,
    max_papers: int | str | None = None,
) -> Dict[str, Any]:
    """원본 payload를 읽어 arXiv 보강/본문 파싱/청크 생성/적재를 수행한다."""
    normalized_target_date = _normalize_optional_date(target_date)
    normalized_date = (
        date_cls.fromisoformat(normalized_target_date).isoformat() if normalized_target_date else date_cls.today().isoformat()
    )
    allowed = allowed_categories or DEFAULT_ALLOWED_CATEGORIES
    normalized_max_papers = _normalize_optional_positive_int(max_papers)

    raw_store = RawPaperStore()
    search_client = PaperSearchClient()
    paper_repository = PaperRepository()
    parser = FulltextParser()

    raw_payload = raw_store.load_daily_papers_response(date=normalized_date)
    raw_count = len(raw_payload)

    raw_ids = [
        candidate
        for item in raw_payload
        if isinstance(item, dict)
        for candidate in [_extract_candidate_arxiv_id(item)]
        if candidate
    ]
    normalized_ids = [search_client.normalize_arxiv_id(value) for value in raw_ids]
    deduplicated_ids = list(dict.fromkeys(normalized_ids))
    selected_ids = deduplicated_ids[:normalized_max_papers]
    metadata_by_arxiv_id = search_client.fetch_arxiv_metadata(selected_ids)

    saved_papers = 0
    saved_fulltexts = 0
    saved_chunks = 0
    skipped_by_category = 0
    enriched_papers: list[dict[str, Any]] = []

    hf_by_id: dict[str, dict[str, Any]] = {}
    for item in raw_payload:
        if not isinstance(item, dict):
            continue
        candidate = _extract_candidate_arxiv_id(item)
        if not candidate:
            continue
        normalized = search_client.normalize_arxiv_id(candidate)
        hf_by_id[normalized] = item

    for arxiv_id, metadata in metadata_by_arxiv_id.items():
        if not _is_allowed_category(metadata, allowed=allowed):
            skipped_by_category += 1
            continue

        hf_item = hf_by_id.get(arxiv_id, {})
        hf_signals = _extract_hf_signals(hf_item)
        prepared = {
            **metadata,
            **hf_signals,
            "source": "hf_daily_papers+arxiv",
        }

        paper_repository.save_paper(prepared)
        saved_papers += 1

        fulltext = parser.parse_from_pdf_url(
            prepared.get("pdf_url") or "",
            fallback_text=prepared.get("abstract") or "",
        )
        chunks = parser.build_chunks(
            fulltext.text or prepared.get("abstract", ""),
            sections=fulltext.sections,
        )
        fulltext_quality_metrics = {
            **fulltext.quality_metrics,
            **parser.summarize_chunks(chunks),
        }
        if fulltext.text:
            paper_repository.save_paper_fulltext(
                arxiv_id,
                text=fulltext.text,
                sections=fulltext.sections,
                source=fulltext.source,
                quality_metrics=fulltext_quality_metrics,
            )
            saved_fulltexts += 1
        if chunks:
            paper_repository.save_paper_chunks(arxiv_id, chunks)
            saved_chunks += len(chunks)

        enriched_papers.append(
            {
                "arxiv_id": arxiv_id,
                "title": prepared.get("title", ""),
                "primary_category": prepared.get("primary_category"),
                "chunk_count": len(chunks),
                "fulltext_source": fulltext.source,
                "fallback_used": fulltext_quality_metrics.get("fallback_used"),
                "section_count": fulltext_quality_metrics.get("section_count", 0),
                "text_length": fulltext_quality_metrics.get("text_length", 0),
            }
        )

    fallback_fulltexts = sum(1 for paper in enriched_papers if paper.get("fallback_used"))

    return {
        "stage": "prepare_papers",
        "status": "success",
        "target_date": normalized_date,
        "raw_payload_count": raw_count,
        "arxiv_candidate_count": len(deduplicated_ids),
        "selected_candidate_count": len(selected_ids),
        "enriched_count": len(metadata_by_arxiv_id),
        "saved_papers": saved_papers,
        "saved_fulltexts": saved_fulltexts,
        "saved_chunks": saved_chunks,
        "skipped_by_category": skipped_by_category,
        "fallback_fulltexts": fallback_fulltexts,
        "sample_prepared": enriched_papers[:5],
        "trace_config": build_pipeline_trace_config(
            stage="prepare_papers",
            runtime=runtime,
            user=user,
            extra_metadata={
                "target_date": normalized_date,
                "raw_payload_count": raw_count,
                "selected_candidate_count": len(selected_ids),
                "saved_papers": saved_papers,
                "saved_chunks": saved_chunks,
                "fallback_fulltexts": fallback_fulltexts,
            },
        ),
    }
