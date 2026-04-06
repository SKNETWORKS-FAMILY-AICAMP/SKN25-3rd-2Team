"""ArXplore 공용 문서 계약 모델을 담당하는 모듈

이 파일의 모델은 UI, pipeline, 저장 계층, LLM 체인이 함께 의존하는 공용 계약입니다
특히 `TopicDocument`의 필드 이름, 타입, 의미는 팀 합의 없이 임의로 변경하면 안 됩니다

변경이 필요한 경우에는 아래 항목을 함께 검토해야 합니다
1. docs/AGENTS.md
2. docs/PLAN.md
3. docs/ARCHITECTURE.md
4. docs/ROLES.md
5. docs/WORKFLOW.md
6. app/, src/pipeline/, 저장 계층 코드
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


class RelatedTopic(BaseModel):
    topic_id: int
    title: str


class TopicDocument(BaseModel):
    """토픽 문서 공용 계약.

    이 모델은 팀 전체의 고정 인터페이스입니다.
    AI 도구를 활용한 구현 과정에서도 임의로 필드를 추가, 삭제, 이름 변경하지 않도록 유지합니다.
    """

    topic_id: int
    title: str
    overview: str
    key_findings: list[str] = Field(default_factory=list)
    papers: list[PaperRef] = Field(default_factory=list)
    related_topics: list[RelatedTopic] = Field(default_factory=list)
    generated_at: datetime


class PaperDetailDocument(BaseModel):
    """단일 논문 상세 문서 계약.

    TopicDocument와 별도로 유지되는 단일 논문 설명용 문서 타입입니다.
    토픽 문서와 목적이 다르므로 상호 대체하지 않고 분리해서 사용합니다.
    """

    arxiv_id: str
    title: str
    overview: str
    key_findings: list[str] = Field(default_factory=list)
    generated_at: datetime
