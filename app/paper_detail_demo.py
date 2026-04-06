"""논문 상세 출력 흐름을 점검하는 Streamlit 데모"""

from __future__ import annotations

from datetime import datetime
import os

import streamlit as st

from src.core import PaperDetailDocument, analyze_paper_detail, build_detailed_summary, has_paper_detail_context, translate_chunk
from src.integrations import PaperRepository

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


@st.cache_resource(show_spinner=False)
def _get_paper_repository() -> PaperRepository:
    return PaperRepository()


@st.cache_data(show_spinner=False, ttl=300)
def _list_recent_paper_cards(limit: int = 12) -> list[dict]:
    return _get_paper_repository().list_recent_paper_cards(limit=limit)


@st.cache_data(show_spinner=False, ttl=300)
def _load_paper_from_db(arxiv_id: str) -> dict | None:
    repository = _get_paper_repository()
    paper = repository.get_paper(arxiv_id)
    if not paper:
        return None

    fulltext = repository.get_paper_fulltext(arxiv_id) or {}
    chunks = repository.list_paper_chunks(arxiv_id, limit=20)

    merged = dict(paper)
    if fulltext:
        merged["fulltext"] = fulltext
        merged["text"] = fulltext.get("text") or ""
        merged["sections"] = fulltext.get("sections") or []
    else:
        merged["text"] = ""
        merged["sections"] = []
    merged["chunks"] = chunks
    return merged


def _chunk_label(chunk: dict) -> str:
    section = str(chunk.get("section_title") or "Untitled").strip() or "Untitled"
    index = chunk.get("chunk_index")
    preview = " ".join(str(chunk.get("chunk_text") or "").split())[:72]
    return f"c{index} · {section} · {preview}"


def _render_paper_detail(document: PaperDetailDocument) -> None:
    st.subheader(document.title)
    st.caption(f"arXiv {document.arxiv_id} · generated_at {document.generated_at.strftime('%Y-%m-%d %H:%M')}")

    st.markdown("### AI-Generated Summary")
    st.write(document.overview)

    st.markdown("### Key Findings")
    if document.key_findings:
        for finding in document.key_findings:
            st.markdown(f"- {finding}")
    else:
        st.caption("핵심 포인트가 아직 없습니다.")


st.title("Paper Detail Demo")
st.caption("논문 상세 페이지 출력 흐름을 확인하는 테스트용 데모")

sample_paper = _build_sample_paper()

db_error: str | None = None
db_papers: list[dict] = []
selected_paper = sample_paper

with st.sidebar:
    st.markdown("### Demo Controls")
    use_live_llm = st.toggle("LLM 호출 실행", value=False)
    st.caption("OPENAI_API_KEY가 설정된 경우에만 실행하세요.")
    use_db_source = st.toggle("DB에서 논문 불러오기", value=False)

    if use_db_source:
        try:
            db_papers = _list_recent_paper_cards()
        except Exception as exc:
            db_error = f"{type(exc).__name__}: {exc}"
        if db_error:
            st.warning(f"DB 연결 실패: {db_error}")
        elif db_papers:
            st.caption("메인 목록 성능을 위해 최근 논문 카드 12개만 먼저 불러옵니다.")

    if use_db_source and db_papers:
        paper_options = {
            f"{paper['arxiv_id']} · {paper['title']}": paper["arxiv_id"]
            for paper in db_papers
        }
        selected_label = st.selectbox("논문 선택", list(paper_options.keys()))
        selected_arxiv_id = paper_options[selected_label]
        loaded_paper = _load_paper_from_db(selected_arxiv_id)
        if loaded_paper:
            selected_paper = loaded_paper
        else:
            st.warning("선택한 논문을 DB에서 읽지 못해 샘플 논문으로 대체합니다.")

    st.markdown("### Selected Paper")
    st.write(selected_paper["title"])
    st.write(f"context ready: {has_paper_detail_context(selected_paper)}")
    st.write(f"OPENAI_API_KEY set: {bool(os.environ.get('OPENAI_API_KEY'))}")
    if use_db_source and db_papers:
        st.write(f"sections: {len(selected_paper.get('sections') or [])}")
        st.write(f"chunks: {len(selected_paper.get('chunks') or [])}")

current_paper_id = str(selected_paper.get("arxiv_id") or "unknown")
if st.session_state.get("_paper_detail_demo_active_paper_id") != current_paper_id:
    st.session_state["_paper_detail_demo_active_paper_id"] = current_paper_id
    st.session_state.pop("_paper_detail_demo_top_summary", None)
    st.session_state.pop("_paper_detail_demo_detailed_summary", None)
    st.session_state.pop("_paper_detail_demo_translation", None)

available_chunks = selected_paper.get("chunks") or []
default_chunk = (
    available_chunks[0]["chunk_text"]
    if available_chunks
    else (
        (selected_paper.get("sections") or [{}])[0].get("text")
        or selected_paper.get("abstract")
        or ""
    )
)
default_fulltext = (
    selected_paper.get("text")
    or "\n\n".join(f"[{section['title']}]\n{section['text']}" for section in selected_paper["sections"])
)

st.markdown("## 입력 데이터")
col1, col2 = st.columns(2)

with col1:
    st.markdown("### Chunk Translation Input")
    if available_chunks:
        chunk_labels = [_chunk_label(chunk) for chunk in available_chunks]
        selected_chunk_label = st.selectbox("근거 청크 선택", chunk_labels)
        selected_chunk = available_chunks[chunk_labels.index(selected_chunk_label)]
        chunk_text = st.text_area("chunk_text", value=selected_chunk["chunk_text"], height=180)
    else:
        chunk_text = st.text_area("chunk_text", value=default_chunk, height=180)

with col2:
    st.markdown("### Detailed Summary Input")
    summary_text = st.text_area("paper text", value=default_fulltext, height=180)

st.divider()
st.markdown("## 논문 상세")
st.caption("상단 요약을 먼저 두고, 상세 요약과 근거 번역은 각각 버튼을 눌러 생성합니다.")

if st.button("상단 요약 생성", use_container_width=True, key="generate_top_summary"):
    if use_live_llm:
        try:
            st.session_state["_paper_detail_demo_top_summary"] = analyze_paper_detail(selected_paper)
        except Exception as exc:
            st.error(f"요약 생성 실패: {type(exc).__name__}: {exc}")
    else:
        st.info("LLM 호출 실행을 켜야 실제 상단 요약을 생성할 수 있습니다.")

top_summary_document = st.session_state.get("_paper_detail_demo_top_summary")
if isinstance(top_summary_document, PaperDetailDocument):
    _render_paper_detail(top_summary_document)
else:
    st.caption("상단 요약이 아직 생성되지 않았습니다.")

st.divider()
st.markdown("## 상세 요약 보기")
st.caption("논문을 더 길게 설명하는 본문형 요약입니다. 버튼을 눌러서만 생성합니다.")

if st.button("상세 요약 생성", use_container_width=True, key="generate_detailed_summary"):
    if use_live_llm:
        try:
            st.session_state["_paper_detail_demo_detailed_summary"] = build_detailed_summary(
                title=selected_paper["title"],
                authors=selected_paper["authors"],
                text=summary_text,
                sections=selected_paper.get("sections"),
            )
        except Exception as exc:
            st.error(f"상세 요약 실패: {type(exc).__name__}: {exc}")
    else:
        st.info("LLM 호출 실행을 켜야 실제 상세 요약을 생성할 수 있습니다.")

detailed_summary_text = st.session_state.get("_paper_detail_demo_detailed_summary")
if detailed_summary_text:
    st.write(detailed_summary_text)
else:
    st.caption("상세 요약이 아직 생성되지 않았습니다.")

st.divider()
st.markdown("## 근거 문장 번역")
st.caption("상세 요약이나 답변의 근거가 되는 영어 원문 청크를 한국어로 확인합니다. 버튼을 눌러서만 생성합니다.")

if st.button("근거 번역 생성", use_container_width=True, key="generate_translation"):
    if use_live_llm:
        try:
            st.session_state["_paper_detail_demo_translation"] = translate_chunk(chunk_text)
        except Exception as exc:
            st.error(f"번역 실패: {type(exc).__name__}: {exc}")
    else:
        st.info("LLM 호출 실행을 켜야 실제 근거 번역을 생성할 수 있습니다.")

translated_chunk = st.session_state.get("_paper_detail_demo_translation")
if translated_chunk:
    st.write(translated_chunk)
else:
    st.caption("근거 번역이 아직 생성되지 않았습니다.")

st.divider()
st.markdown("## 현재 흐름")
st.write("상단 요약을 먼저 보고, 사용자가 원할 때 상세 요약과 근거 번역을 각각 생성하는 흐름입니다.")

st.divider()
st.markdown("## 실행 방법")
st.code("streamlit run app/paper_detail_demo.py", language="bash")
