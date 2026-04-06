"""한국어 번역 및 상세 요약 체인을 담당하는 모듈

두 체인의 용도:
- translate_chunk(): RAG 근거 chunk 단위 번역. 짧은 구절 단위 입력.
- build_detailed_summary(): 논문 단위 구조화 요약. 논문 fulltext 또는 핵심 섹션 텍스트 입력.
"""

from __future__ import annotations

from typing import Any, Optional

from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

from src.shared import get_settings

from .prompts import DETAILED_SUMMARY_PROMPT, TRANSLATION_PROMPT
from .tracing import build_detailed_summary_trace_config, build_translation_trace_config

# 상세 요약에 넣을 본문 최대 길이 (토큰 초과 방지)
_SUMMARY_TEXT_MAX_CHARS = 12000

# chunk 번역에 넣을 텍스트 최대 길이
_CHUNK_TEXT_MAX_CHARS = 2000


def _build_llm(temperature: float = 0.1) -> ChatOpenAI:
    settings = get_settings()
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY가 설정되지 않아 한국어 번역/요약 체인을 실행할 수 없습니다.")

    return ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
        temperature=temperature,
    )


def _format_authors(authors: Any) -> str:
    if not authors:
        return "저자 미상"
    if isinstance(authors, str):
        return authors.strip() or "저자 미상"

    names: list[str] = []
    if isinstance(authors, list):
        for author in authors:
            if isinstance(author, str):
                author_name = author.strip()
                if author_name:
                    names.append(author_name)
                continue
            if isinstance(author, dict):
                author_name = str(author.get("name") or "").strip()
                if author_name:
                    names.append(author_name)
    return ", ".join(names) or "저자 미상"


def _truncate(text: str, max_chars: int) -> str:
    """텍스트를 max_chars 이하로 자른다. 잘린 경우 끝에 표시를 추가한다."""
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[이하 생략]"


def translate_chunk(
    chunk_text: str,
    *,
    runtime: str = "dev",
    user: Optional[str] = None,
    quality_score: float | None = None,
) -> str:
    """RAG 근거 chunk를 한국어로 번역한다.

    Args:
        chunk_text: 번역할 논문 구절. 단일 chunk 단위로 입력한다.
        runtime: 트레이싱 태그용 런타임 구분값.
        user: 트레이싱 태그용 사용자 식별값.
        quality_score: 트레이싱에 기록할 chunk 품질 점수.

    Returns:
        번역된 한국어 텍스트.
    """
    text = _truncate(str(chunk_text or "").strip(), _CHUNK_TEXT_MAX_CHARS)
    if not text:
        return ""

    chain = TRANSLATION_PROMPT | _build_llm(temperature=0) | StrOutputParser()
    config = build_translation_trace_config(
        runtime=runtime,
        user=user,
        quality_score=quality_score,
    )
    return chain.invoke({"chunk_text": text}, config=config)


def build_detailed_summary(
    *,
    title: str,
    authors: Any,
    text: str,
    runtime: str = "dev",
    user: Optional[str] = None,
    quality_score: float | None = None,
) -> str:
    """논문 전체 본문을 입력받아 한국어 구조화 요약을 생성한다.

    Args:
        title: 논문 제목.
        authors: 저자 목록. str, list[str], list[dict] 모두 허용.
        text: 논문 본문 텍스트. paper_fulltexts.text 또는 핵심 섹션 텍스트.
              _SUMMARY_TEXT_MAX_CHARS를 초과하면 앞부분만 사용한다.
        runtime: 트레이싱 태그용 런타임 구분값.
        user: 트레이싱 태그용 사용자 식별값.
        quality_score: 트레이싱에 기록할 품질 점수.

    Returns:
        ## 섹션 구조로 작성된 한국어 요약 텍스트.
    """
    truncated_text = _truncate(str(text or "").strip(), _SUMMARY_TEXT_MAX_CHARS)
    if not truncated_text:
        return ""

    chain = DETAILED_SUMMARY_PROMPT | _build_llm(temperature=0.2) | StrOutputParser()
    config = build_detailed_summary_trace_config(
        runtime=runtime,
        user=user,
        quality_score=quality_score,
    )
    return chain.invoke(
        {
            "title": title or "제목 없음",
            "authors": _format_authors(authors),
            "text": truncated_text,
        },
        config=config,
    )
