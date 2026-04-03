"""ArXplore Streamlit 메인 화면 진입을 담당하는 모듈"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from app.components.topic_card import render_topic_card
from app.pages.topic_detail import render_topic_detail
from src.core import PaperRef, RelatedTopic, TopicDocument

st.set_page_config(page_title="ArXplore", layout="wide")


def _load_demo_topics() -> list[TopicDocument]:
    return [
        TopicDocument(
            topic_id=1,
            title="Speculative Decoding 최적화와 추론 효율화",
            overview=(
                "최근 AI 추론 효율화 연구는 speculative decoding의 draft model 품질과 "
                "verification 전략을 세분화하는 방향으로 움직이고 있다. 이 토픽의 논문들은 "
                "범용 draft 하나로 모든 작업을 처리하기보다, 작업 특화 draft와 inference-time "
                "routing을 조합하는 접근이 더 강하다는 점을 공통적으로 보여준다."
            ),
            key_findings=[
                "추론 가속 품질은 draft 모델 구조뿐 아니라 학습 데이터와 다운스트림 작업의 정합성에 크게 좌우된다.",
                "단일 범용 draft보다 작업 특화 draft를 inference 단계에서 라우팅하는 구성이 더 안정적인 향상을 보인다.",
                "성능 평가는 MT-Bench, GSM8K, MATH-500 같은 벤치마크 조합에 따라 차이가 크므로 토픽 단위 비교가 중요하다.",
            ],
            papers=[
                PaperRef(
                    arxiv_id="2603.27027",
                    title="TAPS: Task Aware Proposal Distributions for Speculative Sampling",
                    authors=[
                        "Mohamad Zbib",
                        "Mohamad Bazzi",
                        "Ammar Mohanna",
                        "Hasan Abed Al Kader Hammoud",
                        "Bernard Ghanem",
                    ],
                    abstract=(
                        "Speculative decoding quality depends on draft-model training distribution and "
                        "improves when specialized drafters are combined with confidence-based routing."
                    ),
                    pdf_url="https://arxiv.org/pdf/2603.27027v1",
                    published_at=datetime(2026, 3, 27, 22, 34),
                    upvotes=127,
                    github_url="https://github.com/Moe-Zbeeb/TAPS",
                    github_stars=4,
                ),
                PaperRef(
                    arxiv_id="2604.00042",
                    title="Adaptive Verification for Efficient Large-Scale Decoding",
                    authors=["ArXplore Demo Author"],
                    abstract=(
                        "A demo paper showing how adaptive verification policies can reduce target-model "
                        "workload under heterogeneous task mixes."
                    ),
                    pdf_url="https://arxiv.org/pdf/2604.00042v1",
                    published_at=datetime(2026, 4, 1, 9, 0),
                    upvotes=18,
                ),
            ],
            related_topics=[
                RelatedTopic(topic_id=2, title="Inference-Time Routing과 MoE 추론 최적화"),
                RelatedTopic(topic_id=3, title="Reasoning 벤치마크 중심 draft model 평가"),
            ],
            generated_at=datetime(2026, 4, 1, 12, 0),
        )
    ]


topics = _load_demo_topics()

st.title("ArXplore")
st.caption("HF Daily Papers와 arXiv 기반 최신 AI 논문을 토픽 문서와 함께 읽는 베타 UI")

topic_map = {topic.title: topic for topic in topics}
selected_title = st.sidebar.selectbox("토픽 선택", list(topic_map.keys()))
selected_topic = topic_map[selected_title]

st.markdown("## 토픽 카드")
for topic in topics:
    with st.container(border=True):
        render_topic_card(topic)

st.divider()
render_topic_detail(selected_topic)
