"""핵심 발견 정리 프롬프트를 담당하는 모듈"""

from langchain_core.prompts import ChatPromptTemplate

KEY_FINDINGS_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "당신은 AI 논문 토픽 문서의 핵심 발견 목록을 작성합니다. "
        "여러 논문에 나타나는 연구 기여, 성능 결과, 방법론 차이를 간결하게 정리합니다.",
    ),
    (
        "human",
        "아래는 같은 토픽에 속하는 AI 논문들입니다.\n\n"
        "{papers}\n\n"
        "핵심 발견 섹션에 들어갈 항목을 작성해주세요.\n"
        "- 2개 이상의 논문에서 공통으로 드러나는 흐름이나 차이를 우선합니다.\n"
        "- 연구 기여, 평가 결과, 데이터셋, 추론 방식 등 검증 가능한 내용만 포함합니다.\n"
        "- 각 항목은 한 문장으로 씁니다.\n"
        "- 불릿 목록 형태로 출력합니다.\n"
        "- 추측, 과장, 투자 관점 해석은 제외합니다.",
    ),
])
