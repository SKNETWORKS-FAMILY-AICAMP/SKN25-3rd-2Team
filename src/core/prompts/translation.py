"""논문 청크(chunk) 단위 한국어 번역 프롬프트"""

from langchain_core.prompts import ChatPromptTemplate

from src.core.prompt_rules import FORBIDDEN_PHRASES, KOREAN_OUTPUT_RULES

TRANSLATION_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "당신은 AI 논문을 한국어로 번역하는 전문가입니다. "
        "질문에 답하기 위해 관련 논문 구절을 한국어로 정확하게 옮깁니다.\n\n"
        + KOREAN_OUTPUT_RULES
        + "\n"
        + FORBIDDEN_PHRASES,
    ),
    (
        "human",
        "아래는 논문에서 가져온 구절입니다.\n\n"
        "{chunk_text}\n\n"
        "위 내용을 한국어로 번역해주세요.\n"
        "- 논문 원문의 의미를 바꾸지 않는다.\n"
        "- AI/ML 전문 용어(예: attention, embedding, fine-tuning, transformer 등)는 영어 원문을 유지하고 괄호에 한국어를 병기한다. 예: attention(주의), embedding(임베딩).\n"
        "- 'features'는 '특징'으로 번역한다.\n"
        "- 그림·표 캡션(Figure N:, Table N: 으로 시작하는 문장)은 핵심만 간결하게 번역한다. 부연 설명을 붙이지 않는다.\n"
        "- 번역문만 출력한다. 설명이나 주석을 추가하지 않는다.",
    ),
])
