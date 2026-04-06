"""토픽 문서 생성 프로토타입 체인을 담당하는 모듈

현재 구현은 `TopicDocument` 계약을 기준으로 한 초기 프로토타입이다
실제 저장 계층, 검색 계층, 평가 기준이 정리되면 입력 구조와 호출 방식이 확장될 수 있다
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from src.shared import get_settings

from .models import PaperRef, RelatedTopic, TopicDocument
from .prompts import KEY_FINDINGS_PROMPT, OVERVIEW_PROMPT
from .tracing import build_analysis_trace_config, build_overview_trace_config, build_key_findings_trace_config


def _build_llm() -> ChatOpenAI:
    settings = get_settings()
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY가 설정되지 않아 토픽 문서 생성 체인을 실행할 수 없습니다.")

    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=0.3,
    )


def _extract_author_names(authors: Any) -> list[str]:
    if not authors:
        return []

    names: list[str] = []
    for author in authors:
        if isinstance(author, str):
            names.append(author)
            continue
        if isinstance(author, dict):
            name = author.get("name")
            if name:
                names.append(name)
    return names


def _format_papers(papers: List[Dict[str, Any]]) -> str:
    """논문 목록을 프롬프트에 넣을 텍스트로 변환합니다."""
    if not papers:
        raise ValueError("토픽 문서 생성에는 최소 1편 이상의 논문이 필요합니다.")

    parts = []
    for i, paper in enumerate(papers, 1):
        title = paper.get("title", "제목 없음")
        authors = ", ".join(_extract_author_names(paper.get("authors"))) or "저자 미상"
        abstract = paper.get("abstract", paper.get("summary", ""))
        arxiv_id = paper.get("arxiv_id", paper.get("id", "ID 없음"))
        pdf_url = paper.get("pdf_url", "PDF URL 없음")
        published_at = paper.get("published_at", paper.get("publishedAt", "발행일 미상"))
        upvotes = paper.get("upvotes")
        github_url = paper.get("github_url", paper.get("githubRepo"))
        github_stars = paper.get("github_stars", paper.get("githubStars"))
        categories = ", ".join(paper.get("categories", [])) or paper.get("primary_category", "카테고리 미상")
        metrics = []
        if upvotes is not None:
            metrics.append(f"HF upvotes: {upvotes}")
        if github_url:
            if github_stars is not None:
                metrics.append(f"GitHub: {github_url} (stars={github_stars})")
            else:
                metrics.append(f"GitHub: {github_url}")
        metrics_text = " | ".join(metrics) if metrics else "부가 지표 없음"
        parts.append(
            f"[논문 {i}] {title}\n"
            f"arXiv ID: {arxiv_id}\n"
            f"저자: {authors}\n"
            f"발행일: {published_at}\n"
            f"카테고리: {categories}\n"
            f"PDF: {pdf_url}\n"
            f"지표: {metrics_text}\n"
            f"초록: {abstract}"
        )
    return "\n\n---\n\n".join(parts)


def _extract_key_findings(text: str) -> list[str]:
    findings: list[str] = []
    for line in text.splitlines():
        cleaned = line.strip().lstrip("-*• ").strip()
        if cleaned:
            findings.append(cleaned)
    return findings


def _build_paper_refs(papers: List[Dict[str, Any]]) -> list[PaperRef]:
    refs: list[PaperRef] = []
    for index, paper in enumerate(papers, 1):
        refs.append(
            PaperRef(
                arxiv_id=str(paper.get("arxiv_id", paper.get("id", index))),
                title=paper.get("title", "제목 없음"),
                authors=_extract_author_names(paper.get("authors")),
                abstract=paper.get("abstract", paper.get("summary", "")),
                pdf_url=paper.get("pdf_url", ""),
                published_at=paper.get("published_at", paper.get("publishedAt")),
                upvotes=paper.get("upvotes", 0) or 0,
                github_url=paper.get("github_url", paper.get("githubRepo")),
                github_stars=paper.get("github_stars", paper.get("githubStars")),
                citation_count=paper.get("citation_count"),
            )
        )
    return refs


def _build_related_topics(related_topics: Optional[List[Dict[str, Any]]]) -> list[RelatedTopic]:
    if not related_topics:
        return []

    return [
        RelatedTopic(
            topic_id=topic["topic_id"],
            title=topic["title"],
        )
        for topic in related_topics
    ]


def build_topic_overview(
    papers: List[Dict[str, Any]],
    *,
    runtime: str = "dev",
    user: Optional[str] = None,
) -> str:
    """토픽 문서의 개요를 생성합니다."""
    chain = OVERVIEW_PROMPT | _build_llm() | StrOutputParser()
    config = build_analysis_trace_config(runtime=runtime, user=user)
    return chain.invoke(
        {"papers": _format_papers(papers)},
        config=config,
    )


def build_topic_key_findings(
    papers: List[Dict[str, Any]],
    *,
    runtime: str = "dev",
    user: Optional[str] = None,
) -> list[str]:
    """토픽 문서의 핵심 발견 목록을 생성합니다."""
    chain = KEY_FINDINGS_PROMPT | _build_llm() | StrOutputParser()
    config = build_analysis_trace_config(runtime=runtime, user=user)
    response = chain.invoke(
        {"papers": _format_papers(papers)},
        config=config,
    )
    return _extract_key_findings(response)


def analyze_topic(
    topic_id: int,
    title: str,
    papers: List[Dict[str, Any]],
    *,
    related_topics: Optional[List[Dict[str, Any]]] = None,
    generated_at: Optional[datetime] = None,
    runtime: str = "dev",
    user: Optional[str] = None,
) -> TopicDocument:
    """토픽 전체를 문서 형태로 생성합니다."""
    return TopicDocument(
        topic_id=topic_id,
        title=title,
        overview=build_topic_overview(papers, runtime=runtime, user=user),
        key_findings=build_topic_key_findings(papers, runtime=runtime, user=user),
        papers=_build_paper_refs(papers),
        related_topics=_build_related_topics(related_topics),
        generated_at=generated_at or datetime.now(timezone.utc),
    )
