"""논문 전처리와 적재를 수행하는 파이프라인 모듈."""

from __future__ import annotations

from datetime import date as date_cls
from typing import Any, Optional

from src.integrations.fulltext_parser import FulltextParser
from src.integrations.paper_repository import PaperRepository
from src.integrations.paper_search import PaperSearchClient
from src.integrations.raw_store import RawPaperStore
from .tracing import build_pipeline_trace_config

DEFAULT_ALLOWED_CATEGORIES = {"cs.AI", "cs.CL", "cs.CV", "cs.LG", "cs.RO", "stat.ML"}


def _sum_result_values(results: list[dict[str, Any]], key: str) -> int:
    return sum(int(result.get(key, 0) or 0) for result in results)


def _build_sample_prepared(results: list[dict[str, Any]], *, limit: int = 5) -> list[dict[str, Any]]:
    return [
        {
            "arxiv_id": result.get("arxiv_id"),
            "title": result.get("title", ""),
            "primary_category": result.get("primary_category"),
            "chunk_count": result.get("chunk_count", 0),
            "fulltext_source": result.get("fulltext_source"),
            "fallback_used": result.get("fallback_used"),
            "section_count": result.get("section_count", 0),
            "text_length": result.get("text_length", 0),
        }
        for result in results[:limit]
    ]


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
    github_url = paper.get("githubRepo")
    github_stars = paper.get("githubStars")
    if isinstance(github, dict):
        github_url = github.get("url") or github.get("repoUrl") or github.get("repository") or github_url
        github_stars = github.get("stars") if github.get("stars") is not None else github_stars
    return {
        "upvotes": int(upvotes or 0),
        "github_url": github_url,
        "github_stars": int(github_stars) if github_stars is not None else None,
    }


def _extract_hf_authors(item: dict[str, Any]) -> list[str]:
    paper = item.get("paper")
    if not isinstance(paper, dict):
        return []
    authors = paper.get("authors")
    if not isinstance(authors, list):
        return []

    names: list[str] = []
    for author in authors:
        if not isinstance(author, dict):
            continue
        name = str(author.get("name") or "").strip()
        if name:
            names.append(name)
    return names


def _build_hf_pdf_url(arxiv_id: str) -> str:
    normalized = arxiv_id.strip()
    if not normalized:
        return ""
    return f"https://arxiv.org/pdf/{normalized}.pdf"


def _build_prepared_from_hf_item(arxiv_id: str, hf_item: dict[str, Any]) -> dict[str, Any]:
    paper = hf_item.get("paper")
    if not isinstance(paper, dict):
        paper = {}

    hf_signals = _extract_hf_signals(hf_item)
    return {
        "arxiv_id": arxiv_id,
        "title": str(paper.get("title") or "").strip(),
        "authors": _extract_hf_authors(hf_item),
        "abstract": str(paper.get("summary") or "").strip(),
        "primary_category": None,
        "categories": [],
        "pdf_url": _build_hf_pdf_url(arxiv_id),
        "published_at": paper.get("publishedAt"),
        "updated_at": paper.get("publishedAt"),
        **hf_signals,
        "source": "hf_daily_papers_raw",
    }


def _rebuild_fulltext_text_from_sections(sections: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for section in sections:
        title = str(section.get("title") or "").strip()
        text = str(section.get("text") or "").strip()
        if not text:
            continue
        if title in {"", "Front Matter", "Full Text"}:
            parts.append(text)
        else:
            parts.append(f"{title}\n{text}")
    return "\n\n".join(parts).strip()


def _repair_parsed_sections_with_metadata(fulltext, prepared: dict[str, Any]) -> None:
    metadata_abstract = " ".join(str(prepared.get("abstract") or "").split())
    if not metadata_abstract or not fulltext.sections:
        return

    repaired = False
    for section in fulltext.sections:
        title = str(section.get("title") or "").strip().lower()
        text = " ".join(str(section.get("text") or "").split())
        if title != "abstract" or not text:
            continue
        if text[0].islower():
            section["text"] = metadata_abstract
            repaired = True

    if not repaired:
        return

    fulltext.text = _rebuild_fulltext_text_from_sections(fulltext.sections) or fulltext.text
    fulltext.quality_metrics["text_length"] = len(fulltext.text)
    fulltext.quality_metrics["section_count"] = len(fulltext.sections)
    section_lengths = [len(str(section.get("text") or "")) for section in fulltext.sections]
    fulltext.quality_metrics["avg_section_chars"] = (
        round(sum(section_lengths) / len(section_lengths), 2) if section_lengths else 0
    )
    fulltext.quality_metrics["max_section_chars"] = max(section_lengths) if section_lengths else 0


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


def load_prepare_candidates(
    target_date: str | None,
    max_papers: int | str | None,
    *,
    metadata_mode: str = "arxiv",
    allowed_categories: set[str] | None = None,
    raw_store: RawPaperStore | None = None,
    search_client: PaperSearchClient | None = None,
) -> dict[str, Any]:
    """전처리 후보 논문과 실행 메타데이터를 로드한다."""
    normalized_target_date = _normalize_optional_date(target_date)
    normalized_date = (
        date_cls.fromisoformat(normalized_target_date).isoformat() if normalized_target_date else date_cls.today().isoformat()
    )
    normalized_max_papers = _normalize_optional_positive_int(max_papers)
    allowed = allowed_categories or DEFAULT_ALLOWED_CATEGORIES

    raw_store = raw_store or RawPaperStore()
    search_client = search_client or PaperSearchClient()

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
    hf_by_id: dict[str, dict[str, Any]] = {}
    for item in raw_payload:
        if not isinstance(item, dict):
            continue
        candidate = _extract_candidate_arxiv_id(item)
        if not candidate:
            continue
        normalized = search_client.normalize_arxiv_id(candidate)
        hf_by_id[normalized] = item

    candidates: list[dict[str, Any]] = []
    skipped_by_category = 0
    metadata_by_arxiv_id: dict[str, dict[str, Any]] = {}

    if metadata_mode == "arxiv":
        metadata_by_arxiv_id = search_client.fetch_arxiv_metadata(selected_ids)
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
            candidates.append(
                {
                    "arxiv_id": arxiv_id,
                    "prepared": prepared,
                }
            )
    elif metadata_mode == "hf_raw":
        for arxiv_id in selected_ids:
            hf_item = hf_by_id.get(arxiv_id)
            if not hf_item:
                continue
            candidates.append(
                {
                    "arxiv_id": arxiv_id,
                    "prepared": _build_prepared_from_hf_item(arxiv_id, hf_item),
                }
            )
    else:
        raise ValueError(f"지원하지 않는 metadata_mode입니다: {metadata_mode}")

    return {
        "metadata_mode": metadata_mode,
        "normalized_date": normalized_date,
        "raw_count": raw_count,
        "deduplicated_ids": deduplicated_ids,
        "selected_ids": selected_ids,
        "enriched_count": len(metadata_by_arxiv_id),
        "skipped_by_category": skipped_by_category,
        "candidates": candidates,
    }


def prepare_single_paper(
    candidate: dict[str, Any],
    *,
    parser: FulltextParser | None = None,
    paper_repository: PaperRepository | None = None,
) -> dict[str, Any]:
    """후보 논문 1건을 저장, 파싱, 청크 생성까지 수행한다."""
    parser = parser or FulltextParser()
    paper_repository = paper_repository or PaperRepository()

    arxiv_id = str(candidate.get("arxiv_id") or "").strip()
    prepared = candidate.get("prepared")
    if not arxiv_id:
        raise ValueError("candidate['arxiv_id']는 비어 있을 수 없습니다.")
    if not isinstance(prepared, dict):
        raise ValueError("candidate['prepared']는 dict여야 합니다.")

    paper_repository.save_paper(prepared)

    fulltext = parser.parse_from_pdf_url(
        prepared.get("pdf_url") or "",
        fallback_text=prepared.get("abstract") or "",
    )
    _repair_parsed_sections_with_metadata(fulltext, prepared)
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
            artifacts=fulltext.artifacts,
            parser_metadata=fulltext.parser_metadata,
        )
    if chunks:
        paper_repository.save_paper_chunks(arxiv_id, chunks)

    return {
        "arxiv_id": arxiv_id,
        "title": prepared.get("title", ""),
        "primary_category": prepared.get("primary_category"),
        "chunk_count": len(chunks),
        "fulltext_source": fulltext.source,
        "fallback_used": fulltext_quality_metrics.get("fallback_used"),
        "section_count": fulltext_quality_metrics.get("section_count", 0),
        "text_length": fulltext_quality_metrics.get("text_length", 0),
        "saved_paper": 1,
        "saved_fulltext": 1 if fulltext.text else 0,
        "saved_chunks": len(chunks),
        "artifacts": fulltext.artifacts,
        "parser_metadata": fulltext.parser_metadata,
        "quality_metrics": fulltext_quality_metrics,
    }


def aggregate_prepare_results(
    results: list[dict[str, Any]],
    *,
    normalized_date: str,
    raw_count: int,
    deduplicated_ids: list[str],
    selected_ids: list[str],
    enriched_count: int,
    skipped_by_category: int,
    runtime: str,
    user: Optional[str],
) -> dict[str, Any]:
    """prepare_single_paper 결과를 현재 파이프라인 반환 구조로 집계한다."""
    fallback_fulltexts = sum(1 for result in results if result.get("fallback_used"))
    saved_papers = _sum_result_values(results, "saved_paper")
    saved_fulltexts = _sum_result_values(results, "saved_fulltext")
    saved_chunks = _sum_result_values(results, "saved_chunks")

    return {
        "stage": "prepare_papers",
        "status": "success",
        "target_date": normalized_date,
        "raw_payload_count": raw_count,
        "arxiv_candidate_count": len(deduplicated_ids),
        "selected_candidate_count": len(selected_ids),
        "enriched_count": enriched_count,
        "saved_papers": saved_papers,
        "saved_fulltexts": saved_fulltexts,
        "saved_chunks": saved_chunks,
        "skipped_by_category": skipped_by_category,
        "fallback_fulltexts": fallback_fulltexts,
        "sample_prepared": _build_sample_prepared(results),
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


def run_prepare_papers(
    *,
    runtime: str = "airflow",
    user: Optional[str] = None,
    target_date: str | None = None,
    allowed_categories: set[str] | None = None,
    max_papers: int | str | None = None,
) -> dict[str, Any]:
    """원본 payload를 읽어 arXiv 보강/본문 파싱/청크 생성/적재를 수행한다."""
    prepare_context = load_prepare_candidates(
        target_date=target_date,
        max_papers=max_papers,
        metadata_mode="hf_raw",
        allowed_categories=allowed_categories,
    )
    paper_repository = PaperRepository()
    parser = FulltextParser()

    results = [
        prepare_single_paper(
            candidate,
            parser=parser,
            paper_repository=paper_repository,
        )
        for candidate in prepare_context["candidates"]
    ]

    return aggregate_prepare_results(
        results,
        normalized_date=prepare_context["normalized_date"],
        raw_count=prepare_context["raw_count"],
        deduplicated_ids=prepare_context["deduplicated_ids"],
        selected_ids=prepare_context["selected_ids"],
        enriched_count=prepare_context["enriched_count"],
        skipped_by_category=prepare_context["skipped_by_category"],
        runtime=runtime,
        user=user,
    )
