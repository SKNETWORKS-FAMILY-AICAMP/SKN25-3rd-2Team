"""역할 3/4 결과물을 한 화면에서 점검하는 Streamlit 데모"""

from __future__ import annotations

from datetime import datetime
import os

import streamlit as st

from src.core import PaperDetailDocument, analyze_paper_detail, build_detailed_summary, has_paper_detail_context, translate_chunk

st.set_page_config(page_title="ArXplore Paper Detail Demo", layout="wide")


def _build_sample_paper() -> dict:
    return {
        "arxiv_id": "2603.27027",
        "title": "TAPS: Task Aware Proposal Distributions for Speculative Sampling",
        "authors": [
            "Mohamad Zbib",
            "Mohamad Bazzi",
            "Ammar Mohanna",
            "Hasan Abed Al Kader Hammoud",
            "Bernard Ghanem",
        ],
        "abstract": (
            "Speculative decoding quality depends on draft-model training distribution and "
            "improves when specialized drafters are combined with confidence-based routing."
        ),
        "pdf_url": "https://arxiv.org/pdf/2603.27027v1",
        "published_at": datetime(2026, 3, 27, 22, 34).isoformat(),
        "sections": [
            {
                "title": "Abstract",
                "text": (
                    "Speculative decoding improves inference efficiency, but its quality depends heavily on the "
                    "proposal distribution induced by the draft model."
                ),
            },
            {
                "title": "Introduction",
                "text": (
                    "Existing speculative sampling methods typically rely on a single generic draft model. "
                    "This creates a mismatch when downstream tasks have heterogeneous verification behavior."
                ),
            },
            {
                "title": "Method",
                "text": (
                    "TAPS introduces task-aware proposal distributions and an inference-time routing strategy "
                    "that selects specialized draft behavior based on task signals and confidence patterns."
                ),
            },
            {
                "title": "Experiments",
                "text": (
                    "The paper evaluates MT-Bench, GSM8K, and MATH-500 settings and reports improved verification "
                    "efficiency relative to generic drafting baselines under mixed workloads."
                ),
            },
            {
                "title": "Limitations",
                "text": (
                    "The method assumes task cues are observable at inference time and may degrade when routing "
                    "signals are weak or when draft specialization data is scarce."
                ),
            },
        ],
    }


def _render_paper_detail(document: PaperDetailDocument) -> None:
    st.subheader(document.title)
    st.caption(f"arXiv {document.arxiv_id} · generated_at {document.generated_at.strftime('%Y-%m-%d %H:%M')}")

    st.markdown("### Overview")
    st.write(document.overview)

    st.markdown("### Key Findings")
    if document.key_findings:
        for finding in document.key_findings:
            st.markdown(f"- {finding}")
    else:
        st.caption("핵심 포인트가 아직 없습니다.")


def _build_mock_paper_detail(sample_paper: dict) -> PaperDetailDocument:
    return PaperDetailDocument(
        arxiv_id=sample_paper["arxiv_id"],
        title=sample_paper["title"],
        overview=(
            "이 논문은 speculative decoding의 효율이 draft model 하나의 평균 성능보다 작업별 proposal 분포에 "
            "더 민감하다는 점을 전제로 출발한다. 단일 범용 draft를 고정해 쓰는 대신, 작업 신호와 confidence 패턴에 "
            "맞춰 proposal behavior를 조정하는 task-aware routing 구조를 제안한다. 실험에서는 MT-Bench, GSM8K, "
            "MATH-500 같은 혼합 작업 환경에서 generic drafting 대비 verification 효율이 더 안정적으로 개선되는 경향을 보인다. "
            "다만 inference-time task cue가 약하거나 draft specialization 데이터가 부족한 경우에는 이점이 줄어들 수 있다."
        ),
        key_findings=[
            "효율 향상은 단일 draft의 평균 품질보다 작업별 proposal 분포 정합성에 더 크게 좌우된다.",
            "task-aware routing은 heterogeneous workload에서 generic draft 대비 verification 부담을 더 안정적으로 줄인다.",
            "평가 벤치마크 조합에 따라 이점의 크기가 달라지므로 mixed-task 기준 비교가 중요하다.",
            "routing signal이 약하거나 specialization 데이터가 부족하면 성능 이점이 줄어들 수 있다.",
        ],
        generated_at=datetime.now(),
    )


st.title("Paper Detail Demo")
st.caption("역할 3 언어 레이어와 역할 4 paper detail 출력을 함께 점검하는 테스트용 데모")

sample_paper = _build_sample_paper()
default_chunk = sample_paper["sections"][2]["text"]
default_fulltext = "\n\n".join(f"[{section['title']}]\n{section['text']}" for section in sample_paper["sections"])

with st.sidebar:
    st.markdown("### Demo Controls")
    use_live_llm = st.toggle("LLM 호출 실행", value=False)
    st.caption("OPENAI_API_KEY가 설정된 경우에만 실행하세요.")
    st.markdown("### Sample Paper")
    st.write(sample_paper["title"])
    st.write(f"context ready: {has_paper_detail_context(sample_paper)}")
    st.write(f"OPENAI_API_KEY set: {bool(os.environ.get('OPENAI_API_KEY'))}")

st.markdown("## 입력 데이터")
col1, col2 = st.columns(2)

with col1:
    st.markdown("### Chunk Translation Input")
    chunk_text = st.text_area("chunk_text", value=default_chunk, height=180)

with col2:
    st.markdown("### Detailed Summary Input")
    summary_text = st.text_area("paper text", value=default_fulltext, height=180)

st.divider()
st.markdown("## 통합 미리보기")
st.caption("메인 방향은 paper detail 최종 출력이다. 역할 4 결과는 보조 구조로 보고, 역할 3 출력과 함께 확인한다.")

connected_col1, connected_col2 = st.columns(2)

with connected_col1:
    st.markdown("### 사용자에게 보여줄 상세 설명")
    if use_live_llm and st.button("Build Connected Detailed Summary", use_container_width=True):
        try:
            detailed_summary = build_detailed_summary(
                title=sample_paper["title"],
                authors=sample_paper["authors"],
                text=summary_text,
            )
            st.write(detailed_summary)
        except Exception as exc:
            st.error(f"상세 요약 실패: {type(exc).__name__}: {exc}")
    else:
        st.write(
            "문제 정의: 기존 speculative decoding은 단일 범용 draft에 의존해 작업별 verification 특성을 충분히 반영하지 못한다.\n\n"
            "접근 방법: 이 논문은 task-aware proposal distribution과 inference-time routing을 결합해 draft behavior를 작업별로 조정한다.\n\n"
            "실험 및 결과: MT-Bench, GSM8K, MATH-500 기반 평가에서 generic drafting 대비 verification 효율 개선 경향을 보인다.\n\n"
            "한계: routing signal이 약하거나 draft specialization 데이터가 부족하면 효과가 줄어들 수 있다.\n\n"
            "핵심 가치: 단일 평균 성능 좋은 draft보다 작업별 proposal 정합성이 더 중요하다는 점을 구조적으로 드러낸다."
        )

with connected_col2:
    st.markdown("### 근거 청크 번역")
    if use_live_llm and st.button("Translate Support Chunk", use_container_width=True):
        try:
            translated = translate_chunk(chunk_text)
            st.write(translated)
        except Exception as exc:
            st.error(f"번역 실패: {type(exc).__name__}: {exc}")
    else:
        st.write(
            "TAPS는 task 신호와 confidence 패턴을 바탕으로 specialized draft behavior를 선택하는 "
            "inference-time routing 전략을 도입한다."
        )

st.divider()
st.markdown("## 역할 4 보조 출력")
st.caption("overview / key findings는 구조화 보조 정보로 확인한다. 메인 최종 출력보다 후순위다.")

if use_live_llm:
    if st.button("Generate Paper Detail Support Output", use_container_width=True):
        try:
            detail_document = analyze_paper_detail(sample_paper)
            _render_paper_detail(detail_document)
        except Exception as exc:
            st.error(f"Paper detail 생성 실패: {type(exc).__name__}: {exc}")
else:
    mock_document = _build_mock_paper_detail(sample_paper)
    _render_paper_detail(mock_document)
    st.info("현재는 mock preview입니다. 사이드바에서 `LLM 호출 실행`을 켜면 실제 체인을 호출합니다.")

st.divider()
st.markdown("## 해석")
st.write(
    "현재 데모에서 메인 최종 출력은 역할 3의 상세 요약과 청크 번역이다. "
    "역할 4의 overview와 key findings는 보조 설명 구조로 남겨두고, 최종 사용자 경험에서는 후순위로 본다."
)

st.divider()
st.markdown("## 실행 방법")
st.code("streamlit run app/paper_detail_demo.py", language="bash")
