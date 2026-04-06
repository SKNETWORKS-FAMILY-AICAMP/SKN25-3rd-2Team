"""토픽 상세 화면의 섹션 렌더링을 담당하는 모듈"""

from __future__ import annotations

import streamlit as st

from src.core import TopicDocument


def render_topic_sections(topic: TopicDocument) -> None:
    st.markdown("## 목차")
    st.markdown("- [개요](#개요)")
    st.markdown("- [핵심 발견](#핵심-발견)")
    st.markdown("- [논문](#논문)")
    st.markdown("- [관련 토픽](#관련-토픽)")

    st.markdown("## 개요")
    st.write(topic.overview)

    st.markdown("## 핵심 발견")
    if topic.key_findings:
        for finding in topic.key_findings:
            st.markdown(f"- {finding}")
    else:
        st.caption("공통으로 확인된 핵심 발견이 아직 충분하지 않습니다.")

    st.markdown("## 논문")
    for paper in topic.papers:
        published_at = paper.published_at.strftime("%Y-%m-%d %H:%M") if paper.published_at else "발행일 미상"
        authors = ", ".join(paper.authors) if paper.authors else "저자 미상"
        metrics: list[str] = []
        if paper.upvotes:
            metrics.append(f"HF upvotes {paper.upvotes}")
        if paper.github_stars is not None:
            metrics.append(f"GitHub stars {paper.github_stars}")
        if paper.citation_count is not None:
            metrics.append(f"Citations {paper.citation_count}")
        st.markdown(
            f"- [{paper.title}]({paper.pdf_url}) · {authors} · {published_at}"
        )
        st.caption(
            f"arXiv {paper.arxiv_id}"
            + (f" · {' · '.join(metrics)}" if metrics else "")
        )

    st.markdown("## 관련 토픽")
    if topic.related_topics:
        for related in topic.related_topics:
            st.markdown(f"- {related.title} (`topic_id={related.topic_id}`)")
    else:
        st.caption("연결된 관련 토픽이 아직 없습니다.")
