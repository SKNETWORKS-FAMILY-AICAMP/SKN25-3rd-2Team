"""ArXplore Streamlit 메인 화면 진입을 담당하는 모듈"""

from __future__ import annotations

import os
from datetime import datetime
import streamlit as st

from src.core import PaperDetailDocument, analyze_paper_detail, build_detailed_summary
from src.integrations import PaperRepository


st.set_page_config(page_title="ArXplore", layout="wide")


@st.cache_resource(show_spinner=False)
def _get_paper_repository() -> PaperRepository:
    return PaperRepository()


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


def go_detail(arxiv_id: str):
    st.session_state.view_mode = "detail"
    st.session_state.selected_arxiv_id = arxiv_id


def go_list():
    st.session_state.view_mode = "list"
    st.session_state.selected_arxiv_id = None
    if "top_summary" in st.session_state:
        del st.session_state["top_summary"]
    if "detailed_summary" in st.session_state:
        del st.session_state["detailed_summary"]


def show_list_view():
    # 1. 헤더 중앙 정렬
    st.markdown("<h1 style='text-align: center; margin-bottom: 0;'>ArXplore Papers</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: gray; margin-bottom: 2.5rem;'>HF Daily Papers & arXiv 기반 최신 AI 논문 탐색 플랫폼</p>", unsafe_allow_html=True)

    # 2. 검색창 중앙 정렬
    _, col_search, _ = st.columns([1, 2, 1])
    with col_search:
        search_query = st.text_input(
            "Search or Ask AI", 
            placeholder="논문에 대해 AI에게 질문하거나 검색해보세요...", 
            label_visibility="collapsed"
        )
        if search_query:
             st.info(f"검색어 '{search_query}'가 입력되었습니다. (RAG 연동 로직 대기중)")

    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # 3. 정렬 기준 Row
    col_title, col_sort = st.columns([6, 1])
    with col_title:
        st.subheader("Explore Papers")
    with col_sort:
        sort_by = st.selectbox(
            "Sort by", 
            ["최신순 (Latest)", "추천순 (Upvotes)"], 
            label_visibility="collapsed"
        )
    
    repo = _get_paper_repository()
    try:
        # 추천순 정렬 등을 위해 넉넉히 가져오기 (60개)
        papers = repo.list_recent_papers(limit=60)
    except Exception as e:
        st.error(f"데이터베이스 연결 실패: {e}")
        return

    if not papers:
        st.info("저장된 논문이 없습니다. 데이터 수집기를 실행해주세요.")
        return

    # Python단 정렬 지원
    if sort_by == "추천순 (Upvotes)":
        papers.sort(key=lambda x: x.get("upvotes", 0) or 0, reverse=True)
        
    display_papers = papers[:21] # 3열이므로 21개가 화면 구성상 비율이 맞음

    # 4. 카드 그리드 구조 (가로 3열) 적용
    cols = st.columns(3)
    for idx, paper in enumerate(display_papers):
        # 3으로 나눈 나머지로 해당 컬럼에 할당
        with cols[idx % 3]:
            # 높이(height)를 명시적으로 고정하여 모든 카드의 세로 크기를 통일
            with st.container(border=True, height=280):
                pdf_link = paper.get("pdf_url") or f"https://arxiv.org/abs/{paper['arxiv_id']}"
                
                # 제목이 너무 길어 줄바꿈이 달라지는 현상 방지
                short_title = paper['title'][:65] + "..." if len(paper['title']) > 65 else paper['title']
                st.markdown(f"**[{short_title}]({pdf_link})**")
                
                abstract = paper.get("abstract", "")
                preview = abstract[:150] + "..." if len(abstract) > 150 else abstract
                
                # 가독성을 위해 abstract 구역 폰트 크기 조절
                st.markdown(f"<p style='font-size: 0.9em; color: #555; height: 70px; overflow: hidden; margin-bottom: 5px;'>{preview}</p>", unsafe_allow_html=True)
                
                authors_str = ", ".join(paper.get("authors", []))
                if len(authors_str) > 40:
                    authors_str = authors_str[:37] + "..."
                    
                pub_date = paper.get("published_at", "Unknown date")
                if "T" in str(pub_date):
                    pub_date = str(pub_date).split("T")[0]
                
                upvotes = paper.get("upvotes", 0) or 0
                
                st.markdown(f"<div style='font-size: 0.85em; color: gray; margin-bottom: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>{authors_str}<br>📅 {pub_date} &nbsp;•&nbsp; ❤️ {upvotes}</div>", unsafe_allow_html=True)
                
                st.button(
                    "상세 보기", 
                    key=f"btn_{paper['arxiv_id']}", 
                    on_click=go_detail, 
                    args=(paper["arxiv_id"],), 
                    use_container_width=True
                )


def show_detail_view():
    st.button("← 뒤로 가기", on_click=go_list)

    arxiv_id = st.session_state.get("selected_arxiv_id")
    if not arxiv_id:
        st.warning("선택된 논문이 없습니다.")
        return

    paper = _load_paper_from_db(arxiv_id)
    if not paper:
        st.error("논문 정보를 읽어올 수 없습니다.")
        return

    st.title(paper["title"])
    
    pdf_link = paper.get("pdf_url") or f"https://arxiv.org/abs/{paper['arxiv_id']}"
    authors_str = ", ".join(paper.get("authors", []))
    st.caption(f"{authors_str}  ·  [PDF 바로가기]({pdf_link})")

    st.divider()

    st.markdown("### AI Overview & Key Findings")
    
    has_api_key = bool(os.environ.get("OPENAI_API_KEY"))
    if not has_api_key:
        st.warning("OPENAI_API_KEY가 설정되어 있지 않아 분석을 생략합니다.")
        st.markdown("**Abstract**")
        st.write(paper.get("abstract"))
    else:
        if "top_summary" not in st.session_state:
            with st.spinner("AI가 실시간으로 논문을 분석하고 있습니다..."):
                try:
                    summary_doc = analyze_paper_detail(paper)
                    st.session_state["top_summary"] = summary_doc
                except Exception as e:
                    st.error(f"요약 중 에러 발생: {e}")
                    st.session_state["top_summary"] = None

        summary_doc = st.session_state.get("top_summary")
        if isinstance(summary_doc, PaperDetailDocument):
            with st.container(border=True):
                st.markdown("#### Overview")
                st.write(summary_doc.overview)
                
                if summary_doc.key_findings:
                    st.divider()
                    st.markdown("#### Key Findings")
                    for finding in summary_doc.key_findings:
                        st.markdown(f"- {finding}")
        elif st.session_state.get("top_summary") is None:
            st.info("요약을 생성하지 못했습니다.")

    st.divider()
    
    st.markdown("### Detailed Summary")
    st.caption("본문형 섹션 상세 요약")
    
    if st.button("상세 요약 생성하기", key="generate_detailed_btn"):
        if not has_api_key:
            st.error("OPENAI_API_KEY가 없어 실행할 수 없습니다.")
        else:
            summary_text = paper.get("text") or "\n\n".join(
                f"[{s['title']}]\n{s['text']}" for s in paper.get("sections", [])
            )
            
            with st.spinner("상세 요약을 생성하고 있습니다..."):
                try:
                    detailed = build_detailed_summary(
                        title=paper["title"],
                        authors=paper["authors"],
                        text=summary_text,
                        sections=paper.get("sections")
                    )
                    st.session_state["detailed_summary"] = detailed
                except Exception as e:
                    st.error(f"상세 요약 생성 실패: {e}")

    detailed_text = st.session_state.get("detailed_summary")
    if detailed_text:
        with st.container(border=True):
            st.markdown(detailed_text)


# --- Initialization & Routing ---
if "view_mode" not in st.session_state:
    st.session_state.view_mode = "list"
    st.session_state.selected_arxiv_id = None

if st.session_state.view_mode == "list":
    show_list_view()
else:
    show_detail_view()
