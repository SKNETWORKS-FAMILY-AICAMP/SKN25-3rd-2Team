"""ArXplore 공용 문서 계약 모델을 담당하는 모듈

이 파일의 모델은 UI, pipeline, 저장 계층, LLM 체인이 함께 의존하는 공용 계약입니다
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class PaperRef(BaseModel):
    arxiv_id: str
    title: str
    authors: list[str] = Field(default_factory=list)
    abstract: str
    pdf_url: str
    published_at: datetime | None = None
    upvotes: int = 0
    github_url: str | None = None
    github_stars: int | None = None
    citation_count: int | None = None


class PaperDetailDocument(BaseModel):
    """논문 상세 문서 계약.

    논문 상세 페이지의 overview, key findings를 포함하는 문서 타입입니다.
    """

    arxiv_id: str
    title: str
    overview: str
    key_findings: list[str] = Field(default_factory=list)
    generated_at: datetime
