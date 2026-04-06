from __future__ import annotations

import json
from pprint import pprint

import src.core.paper_chains as pc


SAMPLE_PAPER = {
    "arxiv_id": "2604.00042",
    "title": "Adaptive Verification for Efficient Large-Scale Decoding",
    "authors": [
        {"name": "ArXplore Demo Author"},
        {"name": "Demo Collaborator"},
    ],
    "abstract": (
        "The paper studies how verification depth can be adjusted dynamically "
        "instead of using a fixed verification policy."
    ),
    "pdf_url": "https://arxiv.org/pdf/2604.00042v1",
    "published_at": "2026-04-01T09:00:00+00:00",
    "categories": ["cs.LG"],
    "sections": [
        {
            "title": "Introduction",
            "text": (
                "The core question is whether speculative decoding pipelines can avoid "
                "spending equal verification effort on all drafted tokens. "
                "The authors note that high-confidence regions and low-confidence regions "
                "should not be treated identically if the goal is overall efficiency."
            ),
        },
        {
            "title": "Approach",
            "text": (
                "The proposed framework monitors local uncertainty and adjusts verification "
                "behavior accordingly. Instead of a fixed verification schedule, it uses "
                "lightweight signals to escalate verification only when the draft behavior "
                "looks unreliable."
            ),
        },
        {
            "title": "Experiments",
            "text": (
                "Benchmarks cover heterogeneous tasks where verification cost varies "
                "significantly by prompt and answer style. The evaluation reports latency "
                "reduction, verification frequency, and output quality compared with "
                "static verification baselines."
            ),
        },
        {
            "title": "Discussion",
            "text": (
                "The paper highlights that adaptive verification introduces another "
                "calibration problem: under-verification can silently harm reliability."
            ),
        },
    ],
}


def print_section(title: str) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def main() -> None:
    print_section("1. _normalize_paper_detail_input")
    normalized = pc._normalize_paper_detail_input(SAMPLE_PAPER)
    print(json.dumps(normalized, ensure_ascii=False, indent=2))

    print_section("2. _extract_author_names")
    pprint(pc._extract_author_names(SAMPLE_PAPER["authors"]))

    print_section("3. _format_paper_metadata")
    print(pc._format_paper_metadata(normalized))

    print_section("4. _select_sections")
    pprint(pc._select_sections(normalized["sections"]))

    print_section("5. _format_paper_sections")
    print(pc._format_paper_sections(normalized))

    print_section("6. has_paper_detail_context")
    print(pc.has_paper_detail_context(SAMPLE_PAPER))

    print_section("7. _extract_key_findings (LLM 없이 후처리만 확인)")
    mock_llm_output = """
    - 적응형 검증은 고정 검증 정책보다 검증 비용을 더 유연하게 배분합니다
    - 지역적 불확실성 신호를 활용해 어려운 구간에서만 검증을 강화합니다
    - 작업 난이도 편차가 큰 워크로드에서 효과가 더 크게 나타납니다
    """
    pprint(pc._extract_key_findings(mock_llm_output))

    print_section("8. build_paper_overview (LLM 호출)")
    try:
        overview = pc.build_paper_overview(
            SAMPLE_PAPER,
            runtime="dev",
            user="local_debug",
        )
        print(overview)
    except Exception as exc:
        print(f"overview 생성 실패: {exc}")

    print_section("9. build_paper_key_findings (LLM 호출)")
    try:
        findings = pc.build_paper_key_findings(
            SAMPLE_PAPER,
            runtime="dev",
            user="local_debug",
        )
        pprint(findings)
    except Exception as exc:
        print(f"key findings 생성 실패: {exc}")

    print_section("10. analyze_paper_detail (최종 문서)")
    try:
        document = pc.analyze_paper_detail(
            SAMPLE_PAPER,
            runtime="dev",
            user="local_debug",
        )
        print(document.model_dump_json(indent=2))
    except Exception as exc:
        print(f"PaperDetailDocument 생성 실패: {exc}")


if __name__ == "__main__":
    main()
