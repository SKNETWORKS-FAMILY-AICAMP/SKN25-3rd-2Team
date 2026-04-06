# ArXplore 역할 분담

## 1. 문서 목적

이 문서는 ArXplore를 5인 팀이 병렬로 구현하고 통합할 때 각 역할의 책임 범위, 소유 모듈, 입력 계약, 출력 계약, handoff 기준, 완료 조건을 정리하는 기준 문서다. 현재 코드베이스는 더 이상 "수집과 적재 기반을 처음부터 만드는 단계"가 아니라, `수집 -> 파싱 -> 적재 -> 임베딩`까지의 기반이 이미 준비된 상태를 전제로 한다. 따라서 역할 분담 역시 초기 파이프라인 구축 중심이 아니라, 그 위에 올라가는 retrieval, answer chain, 한국어 요약, topic document, UI 통합 중심으로 다시 정의해야 한다.

이번 역할 재편의 핵심은 다음과 같다.

- 역할은 파일 분배가 아니라 제품 책임 단위로 나눈다
- 현재 운영 기반은 공용 전제로 두고, 남은 구현 병목을 기준으로 역할을 나눈다
- retrieval, answer, prompt, topic document, UI의 경계를 분명하게 유지한다
- 공용 계약은 바꾸지 않고, 각 계층은 합의된 입력과 출력 위에서 병렬 개발한다

이 문서는 개인 이름이나 현재 작업자 정보를 기록하지 않는다. 역할 번호와 책임, handoff만을 남겨 팀 교체나 추가 합류가 있더라도 문서만으로 구조를 복원할 수 있게 한다.

## 2. 현재 기준선

현재 ArXplore는 아래 기반이 이미 구현된 상태를 기준으로 움직인다.

- HF Daily Papers 원본 수집과 MongoDB raw 저장
- PostgreSQL `prepare_jobs` 기반 prepare queue
- 로컬 `prepare-worker` 기반 `prepare -> embed` 실행 경로
- HURIDOCS 우선, `pypdf` fallback, abstract fallback 기반 PDF 파싱
- PostgreSQL `papers`, `paper_fulltexts`, `paper_chunks`, `paper_embeddings` 적재
- lexical retrieval, vector retrieval, rerank, content role penalty를 포함한 기본 검색 계층
- Airflow DAG 2개 운영 구조
  - `arxplore_daily_collect`
  - `arxplore_maintenance`

즉 현재 남은 구현은 "데이터가 없어서 아무도 시작할 수 없는 상태"가 아니라, 이미 적재된 데이터를 기반으로 검색 품질과 응답 품질, 한국어 산출물, 문서 생성, UI를 정교화하는 단계다.

## 3. 공통 원칙

모든 역할은 아래 기준을 공유한다.

- 제품 방향과 현재 우선순위는 [PLAN.md](./PLAN.md)를 따른다
- 구조와 런타임 토폴로지는 [ARCHITECTURE.md](./ARCHITECTURE.md)를 따른다
- 개발 흐름과 통합 순서는 [WORKFLOW.md](./WORKFLOW.md)를 따른다
- 로컬 실행 환경과 운영 절차는 [TEAM_SETUP.md](./TEAM_SETUP.md)를 따른다
- AI 작업 규칙은 [AGENTS.md](./AGENTS.md)를 따른다
- 공용 데이터 계약은 `src/core/models.py`의 `TopicDocument`, `PaperRef`, `RelatedTopic`을 기준으로 한다
- UI는 읽기 전용 소비 계층으로 유지하며 저장 구조나 검색 계약을 직접 바꾸지 않는다
- 검색 계층은 구현을 바꿀 수 있어도 반환 shape는 가능한 한 안정적으로 유지한다
- DAG 파일은 얇게 유지하고 실제 로직은 `src/pipeline`과 `src/integrations`에 둔다

현재 운영 기반 자체는 공용 자산으로 취급한다. 다만 기반이 이미 존재한다는 사실이, retrieval 반환 shape, answer payload, `TopicDocument` 계약을 각자 편의에 따라 바꿔도 된다는 뜻은 아니다. 오히려 지금 단계에서는 상위 계층 병렬 개발이 시작되기 때문에 계약 안정성이 더 중요하다.

## 4. 공통 용어

ArXplore에서는 아래 표현을 표준 용어로 사용한다.

- `paper`: 단일 논문 메타데이터 단위
- `paper fulltext`: 파싱된 본문 텍스트와 섹션, artifact, parser metadata를 포함하는 단위
- `paper chunk`: retrieval과 grounding에 사용하는 텍스트 단위
- `lexical retrieval`: FTS와 문자열 기반 점수로 후보를 찾는 검색 계층
- `vector retrieval`: 임베딩과 pgvector 유사도로 후보를 찾는 검색 계층
- `hybrid retrieval`: lexical과 vector 결과를 결합하고 rerank를 적용하는 검색 계층
- `answer payload`: RAG 응답 계층이 UI에 넘기는 최종 응답 구조
- `topic`: 유사 논문 묶음
- `topic document`: 토픽 수준의 구조화 문서
- `prepare job`: 날짜 단위 prepare 작업 큐 항목

## 5. 역할 구성

| 역할 | 권장 인원 | 주 책임 |
|------|-----------|--------|
| **1. Retrieval · 검색 품질 담당** | 1명 | lexical/vector/hybrid retrieval, rerank, chunk selection, 검색 평가 |
| **2. RAG 응답 · 근거 제어 담당** | 1명 | query 해석, context 조합, answer chain, citation 정책, answer payload |
| **3. 한국어 번역 · 상세 요약 프롬프트 담당** | 1명 | 한국어 번역, 상세 요약 구조, prompt 규칙, 용어 일관성 |
| **4. 토픽 문서 · 프롬프트 평가 담당** | 1명 | `TopicDocument` 생성 chain, topic prompt, 평가 루프 |
| **5. UI · 문서 소비 계층 담당** | 1명 | Streamlit 검색 화면, 토픽 카드, 상세 문서, 상태 처리 |

이 구조에서 역할 1과 2는 모두 RAG 계열이지만 책임을 분리한다. 역할 1은 "무엇을 가져올 것인가"를, 역할 2는 "가져온 것으로 어떻게 답할 것인가"를 책임진다. 역할 3과 4는 모두 프롬프트 계열이지만, 역할 3은 단일 논문 또는 chunk 기반의 한국어 산출물에, 역할 4는 topic 단위 구조화 문서 생성에 집중한다. 역할 5는 이 결과를 읽는 소비 계층으로 유지한다.

## 6. 역할 간 핵심 의존 관계

### 역할 1 → 역할 2

- 역할 1은 retrieval 결과 shape, score 필드, chunk selection 규칙을 고정한다
- 역할 2는 이를 입력으로 answer chain과 citation 정책을 설계한다

### 역할 1 → 역할 5

- 역할 1은 검색 결과가 UI에 바로 들어갈 수 있는 최소 반환 shape를 유지한다
- 역할 5는 검색 결과 렌더링을 retrieval 내부 구현과 분리된 상태로 설계한다

### 역할 2 → 역할 5

- 역할 2는 answer payload와 근거 표시 구조를 고정한다
- 역할 5는 이를 그대로 표시하는 소비 계층을 구현한다

### 역할 3 → 역할 2, 역할 4

- 역할 3은 한국어 번역과 상세 요약 규칙을 정리해 역할 2의 answer prompt와 역할 4의 topic document prompt가 재사용할 수 있게 한다
- 역할 2와 역할 4는 출력 목적에 맞게 이를 조합한다

### 역할 4 → 역할 5

- 역할 4는 `TopicDocument`를 생성하고 품질 기준을 유지한다
- 역할 5는 카드와 상세 문서 UI를 `TopicDocument` 계약에 직접 맞춘다

## 7. 보호 대상과 공용 계약

다음은 전 역할 공통 보호 대상이다.

- `src/core/models.py`
- `src/core/__init__.py`
- `src/shared/settings.py`
- retrieval 결과 shape
- answer payload shape
- `TopicDocument` 계약

특히 `TopicDocument`는 다음 계층이 동시에 사용한다.

- topic document 생성 chain의 최종 출력
- `topic_documents` 저장 구조
- Streamlit 카드 및 상세 문서의 입력
- RAG 응답 계층이 참조할 수 있는 topic 메타데이터

retrieval 결과 shape 역시 공용 계약으로 취급한다. lexical, vector, hybrid 구현이 달라지더라도 역할 2와 역할 5가 매번 상위 계층을 다시 고칠 필요가 없도록 최소 공용 필드를 유지해야 한다.

현재 retrieval 공용 필드는 다음을 포함해야 한다.

- `chunk_id`
- `arxiv_id`
- `chunk_text`
- `section_title`
- `content_role`
- `score`

answer payload는 최소한 아래 정보를 포함해야 한다.

- 질문 원문
- 정규화된 답변 텍스트
- 근거 chunk 또는 citation 목록
- 관련 논문 메타데이터
- 실패 또는 부족 응답 상태

## 8. 역할별 상세

### 8-1. Retrieval · 검색 품질 담당

이 역할은 "이미 적재된 논문과 청크를 실제로 검색 가능한 인터페이스로 정리하고, 그 품질을 객관적으로 끌어올리는 것"을 책임진다. 핵심은 retrieval 자체를 만드는 것보다, 상위 answer 계층과 UI가 신뢰할 수 있는 검색 결과를 일관되게 제공하는 데 있다.

#### 소유 모듈

- `src/integrations/paper_repository.py`
- `src/integrations/vector_repository.py`
- `src/integrations/paper_retriever.py`
- 필요 시 추가
  - `src/integrations/retrieval_reranker.py`
  - `src/integrations/retrieval_eval.py`

#### 책임 범위

- lexical retrieval 규칙 정리
- vector retrieval 규칙 정리
- hybrid retrieval 결합 방식 정의
- rerank, section prior, content role penalty, chunk selection 전략 정교화
- retrieval 평가셋과 top-k 기준 문서화
- 역할 2와 역할 5가 사용할 수 있는 검색 반환 shape 유지

#### 입력 계약

- `paper_chunks`
- `paper_embeddings`
- 질문 문자열
- optional `arxiv_id`, `topic_id`, `limit` 같은 검색 범위 제약

#### 출력 계약

- 검색 후보 목록
- 각 후보의 점수와 score 출처
- section title, content role, snippet, 논문 식별자
- 상위 계층이 그대로 사용할 수 있는 정규화된 결과 shape

#### handoff

- 역할 2에 answer chain 입력용 retrieval 인터페이스를 제공한다
- 역할 5에 검색 결과 렌더링을 위한 필드 목록을 제공한다
- 검색 실패 기준과 fallback 정책도 함께 제공한다

#### 완료 기준

- lexical, vector, hybrid 중 어떤 경로를 쓰더라도 반환 shape가 안정적이다
- 대표 질의셋 기준 top-k 결과가 section, role, score 관점에서 설명 가능하다
- reference contamination, appendix 과상위 노출, front matter 과노출 같은 오류 사례를 문서화하고 제어한다

### 8-2. RAG 응답 · 근거 제어 담당

이 역할은 retrieval이 찾아온 후보를 실제 사용자 응답으로 바꾸는 계층을 책임진다. retrieval이 "무엇을 가져왔는가"를 다룬다면, 이 역할은 "어떻게 답하고, 어떤 근거를 노출하며, 부족할 때 어떻게 멈출 것인가"를 다룬다.

#### 소유 모듈

- `src/core/rag.py`
- 필요 시 추가
  - `src/core/prompts/answer.py`
  - `src/core/retrievers.py`
  - `src/core/answer_payloads.py`

#### 책임 범위

- query 해석과 optional query rewrite
- retrieval 결과 조합
- context window 구성
- answer formatting
- citation, evidence, insufficient context 정책
- 실패 응답 규칙과 hallucination 억제 규칙

#### 입력 계약

- 역할 1이 제공하는 retrieval 결과
- 질문 원문
- optional topic 문맥
- 역할 3이 정리한 한국어 표현 규칙

#### 출력 계약

- answer payload
- citation 또는 evidence 목록
- 답변 상태 필드
- UI가 그대로 표시 가능한 구조

#### handoff

- 역할 5에 answer payload 규격을 제공한다
- 역할 3에 한국어 표현이 필요한 answer prompt 컨텍스트를 제공한다
- 역할 1과는 retrieval 결과 shape 변경이 answer 계층에 미치는 영향을 함께 검토한다

#### 완료 기준

- 검색 결과가 충분한 경우 근거 기반 답변을 안정적으로 생성한다
- 검색 결과가 부족한 경우 부족하다고 명시하는 응답을 유지한다
- citation과 evidence 노출 형식이 일관되고 UI에 바로 연결된다

### 8-3. 한국어 번역 · 상세 요약 프롬프트 담당

이 역할은 영어 논문을 한국어로 어떻게 전달할지를 결정하는 계층이다. 단순 번역이 아니라, 논문의 핵심을 한국어로 구조화해 전달하는 기준을 만든다. 역할 2와 역할 4가 이 규칙을 재사용할 수 있어야 한다는 점에서 공용 프롬프트 레이어 성격을 가진다.

#### 소유 모듈

- `src/core/prompts/` 하위의 한국어 응답 관련 프롬프트 파일
- 필요 시 추가
  - `src/core/prompts/translation.py`
  - `src/core/prompts/detailed_summary.py`

#### 책임 범위

- 논문 단위 번역 전략
- chunk 단위 번역 전략
- 상세 요약 구조 정의
- 문체, 길이, 용어 일관성 기준 수립
- 과도한 축약과 abstract 재서술 수준에 머무르는 문제 방지

#### 입력 계약

- `paper_fulltexts` 또는 `paper_chunks`
- 역할 2와 역할 4의 출력 목적
- 질문 기반 응답인지, 문서형 요약인지에 대한 호출 맥락

#### 출력 계약

- 한국어 번역 prompt 규칙
- 상세 요약 prompt 규칙
- 요약 섹션 구조
- 금지 표현과 톤 가이드

#### handoff

- 역할 2에 한국어 answer prompt 규칙을 제공한다
- 역할 4에 topic document용 한국어 작성 기준을 제공한다
- 역할 5에는 사용자에게 보이는 텍스트 톤과 길이의 기준을 제공한다

#### 완료 기준

- 한국어 출력이 abstract 재진술 수준을 넘어서 논문의 문제, 접근, 실험, 한계, 가치까지 구조화한다
- 질문응답과 문서 생성 모두에서 재사용 가능한 표현 규칙이 문서화된다
- 팀 내 다른 역할이 프롬프트를 임의로 다시 정의하지 않아도 되는 수준의 기준선이 마련된다

### 8-4. 토픽 문서 · 프롬프트 평가 담당

이 역할은 여러 논문을 토픽 단위 문서로 묶는 체인과 평가 루프를 책임진다. 단일 논문 설명을 잘 쓰는 것과 topic document를 잘 쓰는 것은 다른 문제이므로, 한국어 요약 역할과 별도로 유지한다.

#### 소유 모듈

- `src/core/chains.py`
- `src/core/prompts/overview.py`
- `src/core/prompts/key_findings.py`
- `src/core/tracing.py`

#### 책임 범위

- `TopicDocument` 생성 chain 안정화
- `overview`, `key_findings` 프롬프트 품질 개선
- topic title, related topics, paper refs 조합 기준 유지
- LangSmith 또는 샘플셋 기반 평가 루프 설계

#### 입력 계약

- 역할 1 또는 저장 계층이 제공하는 논문 묶음
- 역할 3이 제공하는 한국어 표현 규칙
- `TopicDocument` 계약

#### 출력 계약

- `TopicDocument`
- topic document 평가 기준
- trace 태그와 비교 기준

#### handoff

- 역할 5에 카드와 상세 화면 입력 구조를 제공한다
- 역할 2에 topic 문맥을 answer chain에서 활용할 경우 필요한 필드를 제공한다

#### 완료 기준

- 샘플 topic 집합에 대해 구조가 안정적인 `TopicDocument`를 생성할 수 있다
- overview와 key findings의 역할이 섞이지 않는다
- topic document 품질을 반복 측정할 수 있는 평가 루프가 마련된다

### 8-5. UI · 문서 소비 계층 담당

이 역할은 현재 데이터 구조와 생성 결과를 사용자 경험으로 연결하는 계층을 책임진다. UI는 저장 구조를 직접 설계하는 역할이 아니라, retrieval 결과와 `TopicDocument`, answer payload를 읽기 좋게 소비하는 계층으로 유지해야 한다.

#### 소유 모듈

- `app/main.py`
- `app/components/topic_card.py`
- `app/components/section_renderer.py`
- `app/pages/topic_detail.py`

#### 책임 범위

- 메인 검색 화면
- answer payload 렌더링
- 토픽 카드 목록
- topic document 상세 화면
- 로딩, 빈 상태, 오류 상태 처리

#### 입력 계약

- 역할 1의 retrieval 결과
- 역할 2의 answer payload
- 역할 4의 `TopicDocument`

#### 출력 계약

- 사용자 화면 흐름
- 컴포넌트별 필요 필드 목록
- 오류 상태와 빈 상태의 표시 정책

#### handoff

- 역할 1, 2, 4에 UI가 기대하는 최소 필드 목록을 전달한다
- 계약 변경이 필요한 경우 코드 수정 전에 문서 기준 변경을 먼저 요청한다

#### 완료 기준

- 검색 결과, 답변, 토픽 카드, 상세 문서가 같은 UI 흐름 안에서 자연스럽게 이어진다
- 계약을 깨지 않고도 데모 데이터와 실데이터가 같은 컴포넌트 구조를 탄다
- 빈 검색 결과, 생성 실패, 데이터 누락 상태를 명확히 처리한다

## 9. 역할 간 handoff 체크리스트

### 역할 1이 넘겨야 하는 것

- retrieval 함수 진입점
- 검색 결과 예시 payload
- score와 rerank 기준 요약
- 대표 질의셋과 실패 사례

### 역할 2가 넘겨야 하는 것

- answer payload 예시
- citation 규칙
- 답변 실패 또는 부족 응답 예시

### 역할 3이 넘겨야 하는 것

- 한국어 번역 규칙
- 상세 요약 구조
- 금지 표현과 길이 기준

### 역할 4가 넘겨야 하는 것

- `TopicDocument` 샘플
- topic 문서 평가 기준
- trace 비교 기준

### 역할 5가 넘겨야 하는 것

- 화면별 필요 필드 목록
- 빈 상태와 오류 상태 정책
- 계약 변경 요청이 필요한 경우의 사유

## 10. 협의 없이 바꾸지 않는 항목

- `TopicDocument` 필드 구조
- retrieval 결과 공용 shape
- answer payload 공용 shape
- DAG ID
- Compose 서비스명
- `.env` 핵심 키 이름
- 저장소 전역 용어

이 항목은 각 역할의 작업 속도보다 통합 비용에 더 큰 영향을 준다. 변경이 필요하면 이유, 영향 범위, 수정 대상 문서를 먼저 정리한 뒤 협의해야 한다.

## 11. 최종 완료 기준

문서 기준으로 역할 분담이 완료됐다고 보려면 아래 조건을 만족해야 한다.

- 역할 1이 검색 품질 계층을 안정화한다
- 역할 2가 retrieval 결과를 기반으로 answer chain을 고정한다
- 역할 3이 한국어 번역과 상세 요약 규칙을 정리한다
- 역할 4가 `TopicDocument` 생성과 평가 루프를 안정화한다
- 역할 5가 검색, 문서, 답변 소비 흐름을 UI에 반영한다
- 역할별 산출물이 임시 구조가 아니라 공용 계약 기반으로 연결된다

이 문서는 이후 구현 진척에 따라 세부 예시는 보강할 수 있다. 다만 현재 단계의 핵심은 역할 경계를 다시 흐리는 것이 아니라, 이미 준비된 데이터 기반 위에서 남은 구현 병목을 정확히 분담하는 데 있다.
