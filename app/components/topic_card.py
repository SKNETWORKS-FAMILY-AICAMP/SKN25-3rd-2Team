"""토픽 카드 UI 렌더링을 담당하는 모듈"""

from __future__ import annotations

import streamlit as st

from src.core import TopicDocument


def render_topic_card(topic: TopicDocument) -> None:
    st.subheader(topic.title)
    st.caption(
        f"최근 갱신: {topic.generated_at.strftime('%Y-%m-%d %H:%M')} · "
        f"논문 {len(topic.papers)}편"
    )
    st.write(topic.overview)
