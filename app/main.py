"""ArXplore Streamlit 메인 화면 진입을 담당하는 모듈"""

from __future__ import annotations

import streamlit as st

st.set_page_config(page_title="ArXplore", layout="wide")

st.title("ArXplore")
st.caption("HF Daily Papers와 arXiv 기반 최신 AI 논문 탐색 플랫폼")

st.info("메인 화면은 준비 중입니다. 논문 상세 데모는 `streamlit run app/paper_detail_demo.py`로 확인할 수 있습니다.")
