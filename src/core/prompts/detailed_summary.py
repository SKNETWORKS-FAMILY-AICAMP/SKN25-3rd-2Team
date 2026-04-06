"""논문 단위 상세 요약 프롬프트"""

from langchain_core.prompts import ChatPromptTemplate

from src.core.prompt_rules import (
    FORBIDDEN_PHRASES,
    KOREAN_OUTPUT_RULES,
    SUMMARY_SECTION_STRUCTURE,
)

DETAILED_SUMMARY_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "당신은 AI 논문을 한국어로 구조화해 요약하는 전문가입니다. "
        "단순 번역이나 abstract 재서술이 아니라, "
        "논문의 문제 · 접근 · 실험 · 한계 · 가치를 분리해서 전달합니다.\n\n"
        + KOREAN_OUTPUT_RULES
        + "\n"
        + FORBIDDEN_PHRASES
        + "\n"
        + SUMMARY_SECTION_STRUCTURE,
    ),
    (
        "human",
        "아래 논문을 상세 요약해주세요.\n\n"
        "제목: {title}\n"
        "저자: {authors}\n"
        "본문:\n{text}\n\n"
        "위 섹션 구조(문제 정의 → 접근 방법 → 실험 및 결과 → 한계 → 핵심 가치) 순서로 작성하세요.\n"
        "- 각 섹션은 2~4문장으로 작성한다.\n"
        "- 수치 결과는 논문 원문 그대로 표기한다.\n"
        "- 논문에 해당 내용이 없는 섹션은 '명시되지 않음' 한 줄로만 표기한다. 부연 설명을 붙이지 않는다.\n"
        "- 핵심 가치 섹션: '새로운 접근 방식을 제시한다', '기여한다'로 끝내지 않는다. "
        "기존 방법이 의존하던 가정이나 구조적 한계를 구체적으로 지목하고, 이 연구가 그것을 어떻게 깼는지를 쓴다.",
    ),
])
