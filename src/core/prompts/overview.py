"""토픽 개요를 생성할 때 사용하는 프롬프트 모듈."""

from langchain_core.prompts import ChatPromptTemplate

OVERVIEW_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "당신은 AI 논문 토픽 문서의 개요를 작성합니다. "
        "여러 논문의 공통 흐름과 연구 방향을 한국어로 요약합니다.",
    ),
    (
        "human",
        "아래는 같은 토픽에 속하는 AI 논문들입니다.\n\n"
        "{papers}\n\n"
        "이 토픽 문서의 개요를 3~5문장으로 작성해주세요.\n"
        "- 개별 논문 나열이 아니라 연구 흐름과 공통 주제를 먼저 설명합니다.\n"
        "- 논문에 명시된 기여, 평가 대상, 결과만 사용합니다.\n"
        "- 근거 없는 전망, 과장, 일반론은 제외합니다.",
    ),
])
