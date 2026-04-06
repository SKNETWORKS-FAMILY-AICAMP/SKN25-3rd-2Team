import json
from src.integrations.paper_retriever import PaperRetriever
from src.core.rag import answer_question
from src.shared.settings import get_settings

def test_rag_integration():
    print("\n" + "🚀" * 3 + " ArXplore RAG 통합 테스트 " + "🚀" * 3)
    
    # 0. 설정 확인
    settings = get_settings()
    print(f"\n[STEP 0: 환경 설정 점검]")
    print(f"  - API KEY 로드 여부: {bool(settings.openai_api_key)}")
    print(f"  - 사용 모델: {settings.openai_model}")

    # 1. 리트리버 초기화
    retriever = PaperRetriever()
    
    # 2. 실제 DB에서 논문 검색
    test_query = "Long-context modeling에 대해 알려줘"
    print(f"\n[STEP 1: 검색 수행]")
    print(f"  - 사용자 질문: '{test_query}'")
    
    # 하이브리드 검색 수행
    context_papers = retriever.search_paper_contexts_by_hybrid(test_query, limit=3)
    
    print(f"  - 검색된 청크 수: {len(context_papers)}개")
    for i, p in enumerate(context_papers):
        print(f"    {i+1}. [{p.get('arxiv_id')}] 점수: {p.get('score'):.4f} | 섹션: {p.get('section_title')}")

    if not context_papers:
        print("\n⚠️  경고: 검색 결과가 없습니다. DB에 관련 논문이 있는지 확인하세요.")

    # 3. RAG 답변 생성 함수 호출
    print("\n[STEP 2: LLM 응답 및 번역 근거 생성]")
    print("  - answer_question() 호출 중 (Role 2 & 3 엔진 가동)...")
    
    result = answer_question(
        question=test_query,
        context_papers=context_papers,
        context_documents=[], 
        runtime="dev"
    )
    
    # 4. 결과 출력
    print("\n" + "━" * 60)
    print(f"✅ 테스트 완료 - 최종 결과 리포트")
    print("━" * 60)
    
    print(f"📍 1. 쿼리 최적화")
    print(f"   - 재작성: {result.get('rewritten_query')}")

    print(f"\n📍 2. 시스템 상태")
    status = result.get('status')
    status_emoji = "🟢" if status == "success" else "🔴"
    print(f"   - 상태 코드: {status_emoji} {status}")

    print(f"\n📍 3. 생성 답변 (Role 3 페르소나 적용)")
    print("-" * 30)
    print(result.get('answer'))
    print("-" * 30)

    # 핵심 디버깅 포인트: 번역된 근거 확인
    print(f"\n📍 4. 번역된 근거 (Role 3 번역 엔진 결과)")
    evidences = result.get('evidences', [])
    print(f"   - 생성된 근거 수: {len(evidences)}개")
    
    if evidences:
        for i, ev in enumerate(evidences):
            print(f"     {i+1}. [{ev['arxiv_id']}] {ev['section']}")
            # 앞부분 150자만 출력하여 확인
            short_text = ev['translated_text'].replace('\n', ' ')[:150]
            print(f"        번역: {short_text}...")
    else:
        print("     ❌ 생성된 번역 근거가 없습니다. (status 확인 필요)")

    print(f"\n📍 5. 참조 논문 메타데이터 (Mapping)")
    source_papers = result.get('source_papers', [])
    for paper in source_papers:
        print(f"     ✅ [{paper.arxiv_id}] {paper.title[:50]}...")

    print("\n" + "━" * 60 + "\n")

if __name__ == "__main__":
    test_rag_integration()