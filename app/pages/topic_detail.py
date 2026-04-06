"""토픽 상세 페이지 렌더링을 담당하는 모듈"""

from __future__ import annotations

import streamlit as st

from app.components.section_renderer import render_topic_sections
from src.core import TopicDocument


def render_topic_detail(topic: TopicDocument) -> None:
    st.title(topic.title)
    st.caption(f"문서 갱신 시각: {topic.generated_at.strftime('%Y-%m-%d %H:%M')}")
    render_topic_sections(topic)
