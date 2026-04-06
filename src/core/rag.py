"""RAG 응답 체인의 기본 뼈대를 담당하는 모듈"""

from __future__ import annotations
import re
from typing import Any, Optional
from langchain_openai import ChatOpenAI
from src.core.models import PaperRef, TopicDocument, RelatedTopic
from src.shared.settings import get_settings 
from src.core.translation_chains import translate_chunk


settings = get_settings()
llm = ChatOpenAI(
    model=settings.openai_model, 
    openai_api_key=settings.openai_api_key, 
    temperature=0,
    streaming=False
)



def rewrite_query(query: str, runtime: str = "dev") -> str:
    """사용자 질문을 검색 효율을 높이기 위해 재작성한다."""
    # 역할 3의 스타일을 반영하여 학술적 쿼리로 변환 가이드 강화
    prompt = f"""
    당신은 AI/ML 논문 검색 전문가입니다. 사용자의 질문을 학술 데이터베이스 검색에 최적화된 키워드로 변환하세요.
    
    [User Question]: {query}
    
    [Output Rule]:
    1. 핵심 개념을 영어(한국어) 형태로 추출할 것.
    2. 검색 의도와 관련된 최신 AI 연구 트렌드 키워드를 포함할 것.
    3. 결과는 반드시 검색어 문자열만 출력할 것.
    """
    response = llm.invoke(prompt)
    return response.content

def generate_grounded_answer(question: str, context_text: str) -> str:
    """역할 3의 상세 요약 및 번역 원칙을 적용하여 근거 기반 답변을 생성한다."""
    
    # 역할 3의 Writing Principles 반영
    prompt = f"""
    당신은 AI/ML 논문을 한국어로 깊이 있게 분석해 전달하는 전문가다. 
    아래 제공된 [Context]를 바탕으로 [Question]에 답변하라.

    [Context]:
    {context_text}

    [Question]:
    {question}

    [Strict Rules - Role 2 & 3 Combined]:
    1. 논문에 명시된 내용만 사용한다. 추측이나 전망을 배제한다. (환각 금지)
    2. 전문 용어는 첫 등장 시 '한국어(영어)' 형태로 병기하고, 이후에는 한국어로 쓴다.
    3. 문체는 '~한다/~이다' 체를 사용하며, 직역투(~에 의해, ~함으로써)를 피한다.
    4. 숫자, 모델명, 데이터셋명은 원문 그대로 유지한다.
    5. 답변 중 근거가 되는 문장 끝에 반드시 [arxiv_id] 형식으로 출처를 명시하라.
    6. 정보가 부족할 경우 "제공된 논문 내에서 관련 정보를 찾을 수 없습니다"라고 명확히 밝힌다.
    """
    response = llm.invoke(prompt)
    return response.content

def validate_citations(answer: str, context_papers: list[dict]) -> list[dict]:
    """답변 내 인용을 검증하고 실제 논문 데이터와 매핑한다."""
    cited_ids = set(re.findall(r"\[(\d+\.\d+)\]", answer))
    valid_citations = []
    
    available_ids = {p.get("arxiv_id") for p in context_papers}
    for cid in cited_ids:
        if cid in available_ids:
            paper_info = next(p for p in context_papers if p["arxiv_id"] == cid)
            valid_citations.append(paper_info)
            
    return valid_citations

def determine_response_status(context_papers: list[dict], answer: str) -> str:
    """답변 품질과 근거 수준에 따른 상태 결정."""
    if not context_papers:
        return "insufficient_context"
    if "찾을 수 없습니다" in answer:
        return "no_information_found"
    return "success"

def answer_question(
    question: str,
    *,
    context_papers: list[dict[str, Any]],
    context_documents: list[TopicDocument],
    runtime: str = "dev",
    user: Optional[str] = None,
) -> dict[str, Any]:
    """RAG 답변 생성 최종 진입점."""

    if not context_papers:
        return {
            "answer": "죄송합니다. 관련 논문을 찾지 못했습니다.",
            "source_papers": [],
            "evidences": [],
            "related_topics": [],
            "status": "insufficient_context"
        }
    # 쿼리재작성
    rewritten_query = rewrite_query(question, runtime=runtime)

    combined_context = ""
    for p in context_papers:
        combined_context += f"\n--- Paper: {p.get('arxiv_id')} ---\n{p.get('context_text')}\n"


    # 답변 생성 
    answer_text = generate_grounded_answer(question, combined_context)

    # 인용 검증 및 소스 매핑
    validated_sources = validate_citations(answer_text, context_papers)

    evidences = []
    for s in validated_sources:
        translated_text = translate_chunk(
            s.get("chunk_text", ""), 
            runtime=runtime, 
            user=user,
            quality_score=s.get("score")
        )
        evidences.append({
            "arxiv_id": s.get("arxiv_id"),
            "original_text": s.get("chunk_text"),
            "translated_text": translated_text,
            "section": s.get("section_title")
        })
    
    # 응답 상태 결정
    status = determine_response_status(context_papers, answer_text)

    source_papers = [
        PaperRef(
            arxiv_id=s.get("arxiv_id"),
            title=s.get("paper_title", "Unknown"),
            authors=s.get("authors", []),
            abstract=s.get("paper_abstract", ""),
            pdf_url=s.get("pdf_url", "")
        ) for s in validated_sources
    ]

    return {
        "question": question,
        "rewritten_query": rewritten_query,
        "answer": answer_text,
        "evidences": evidences,  
        "source_papers": source_papers,
        "related_topics": [RelatedTopic(topic_id=td.topic_id, title=td.title) for td in context_documents],
        "status": status,
        "runtime": runtime,
        "user": user
    }

