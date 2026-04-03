# ArXplore 역할 분담

## 1. 문서 목적

이 문서는 ArXplore를 5인 팀이 병렬로 구현할 때 각자의 책임 범위, 소유 파일, 구현 대상, 협업 인터페이스, 산출물, 완료 기준을 구체적으로 정리한다. 현재 저장소는 도메인 계약과 실행 환경이 정리된 스캐폴드 상태이며, 실제 구현 단계에서는 "누가 무엇을 먼저 끝내야 다른 역할이 막히지 않는가"를 기준으로 역할을 재구성해야 한다.

이번 역할 분담의 핵심 원칙은 두 가지다.

- **텍스트 중심 논문 서비스**라는 제품 방향에 맞춰 역할을 나눈다.
- **1번 역할이 선행 완료한 뒤 2~5번 역할이 병렬로 작업할 수 있는 구조**를 만든다.

따라서 역할 분담의 목적은 단순한 파일 분배가 아니라, 초기 병목을 줄이고 병렬 개발 효율을 최대화하는 데 있다.

## 2. 기본 원칙

각 담당자는 자신의 영역에서 설계 결정을 주도할 수 있어야 한다. 하지만 다른 역할이 의존하는 입력과 출력 계약은 임의로 바꿔서는 안 된다. ArXplore는 특히 `TopicDocument` 계약, retrieval 결과 shape, pipeline 단계 이름이 여러 계층에 동시에 영향을 주므로 변경 시 문서와 코드를 함께 맞춰야 한다.

공통 원칙은 다음과 같다.

- 제품 방향과 범위는 [PLAN.md](./PLAN.md)를 따른다.
- 계층 구조와 런타임 토폴로지는 [ARCHITECTURE.md](./ARCHITECTURE.md)를 따른다.
- 구현 순서와 handoff 방식은 [WORKFLOW.md](./WORKFLOW.md)를 따른다.
- 공용 데이터 계약은 `src/core/models.py`의 `TopicDocument`, `PaperRef`, `RelatedTopic`를 기준으로 한다.
- `TopicDocument` 계약은 전원 합의 없이 변경하지 않는다.
- DAG 정의는 가볍게 유지하고, 실제 비즈니스 로직은 `src/pipeline` 이하에 둔다.
- UI는 저장 계층이나 외부 API를 직접 호출하지 않고, 합의된 조회 경로만 사용한다.
- retrieval은 "최소 retrieval"과 "고도화 retrieval" 두 단계가 있을 수 있지만, 반환 형태는 가능한 한 동일하게 유지한다.

## 3. 공통 용어

ArXplore에서는 다음 용어를 공통으로 사용한다.

- `paper`: 단일 논문 메타데이터
- `paper fulltext`: PDF에서 추출한 본문 텍스트와 섹션 정보
- `paper chunk`: RAG 검색을 위한 텍스트 단위
- `minimum retrieval`: 1번 역할이 먼저 제공하는 최소 검색 경로
- `vector retrieval`: 2번 역할이 고도화하는 임베딩 기반 검색 경로
- `topic`: 유사 논문 묶음
- `topic document`: 토픽을 설명하는 구조화 문서
- `RAG answer`: 검색 결과 범위 안에서 생성한 응답

## 4. 5인 팀 기준 역할 구성

| 역할 | 권장 인원 | 주 책임 |
|------|-----------|--------|
| **1. 인프라 · 데이터 파이프라인 · 적재 담당** | 1명 | Docker, Compose, Airflow, 논문 수집, MongoDB 원본 저장, PDF 본문 텍스트 파싱, PostgreSQL 적재, 최종 청크, 최소 retrieval |
| **2. 임베딩 · 벡터 검색 · 토픽 그룹핑 담당** | 1명 | 임베딩 생성, pgvector 저장, vector retrieval, retrieval 품질 개선, 토픽 그룹핑 |
| **3. 토픽 문서 생성 담당** | 1명 | `TopicDocument` 생성 프롬프트, 체인, 문서 생성 품질 |
| **4. RAG 응답 담당** | 1명 | 검색 결과 조합, 응답 프롬프트, 근거 노출 정책, 검색 응답 품질 |
| **5. UI · 문서 소비 계층 담당** | 1명 | Streamlit 검색 화면, 카드, 상세 문서, 상태 처리 |

이 배치는 "1번이 데이터를 준비해 놓으면 나머지가 같은 기준 데이터 위에서 병렬로 일한다"는 운영 방식을 기준으로 구성했다.

## 5. 역할 간 핵심 의존 관계

### 1번 → 2번

- 1번은 논문 메타데이터, 본문 텍스트, 최종 청크, 최소 retrieval 경로를 준비한다.
- 2번은 이 결과를 읽어 임베딩 저장, vector retrieval, 토픽 그룹핑을 구현한다.

### 1번 → 3번

- 1번은 `papers`, `paper_fulltexts`, `paper_chunks` 읽기 가능한 상태를 만든다.
- 3번은 이 데이터를 바탕으로 `TopicDocument` 생성 품질을 개선한다.

### 1번 + 2번 → 4번

- 1번은 최소 retrieval을 제공한다.
- 2번은 나중에 동일 반환 형태의 vector retrieval로 이를 고도화한다.
- 4번은 먼저 최소 retrieval 위에서 응답 흐름을 구현하고, 이후 2번이 만든 vector retrieval로 같은 인터페이스를 유지한 채 교체한다.

### 1번 + 3번 + 4번 → 5번

- 1번은 읽을 수 있는 실데이터를 준비한다.
- 3번은 `TopicDocument`를 제공한다.
- 4번은 검색 응답 구조를 제공한다.
- 5번은 카드, 상세 문서, 검색 응답 UI를 렌더링한다.

## 6. 공통 계약과 보호 대상

다음 요소는 모든 역할이 의존하는 보호 대상이다.

- `src/core/models.py`
- `src/core/__init__.py`
- `src/core/prompts/__init__.py`
- `src/shared/settings.py`

특히 `TopicDocument`는 다음 역할을 동시에 수행한다.

- 문서 생성 체인의 최종 출력
- PostgreSQL `topic_documents` 저장 대상
- Streamlit 상세 문서 렌더링 입력
- RAG 응답에서 참조하는 문서 메타데이터 구조

또한 retrieval 인터페이스도 공용 계약으로 취급한다. 최소 retrieval과 vector retrieval이 서로 다른 구현을 갖더라도, 가능한 한 같은 반환 형태를 유지해야 4번과 5번이 중간에 다시 흔들리지 않는다.

최소 공용 반환 형태는 다음을 기준으로 한다.

- `chunk_id`
- `arxiv_id`
- `chunk_text`
- `similarity_score`

## 7. 역할별 상세

### 7-1. 인프라 · 데이터 파이프라인 · 적재 담당

이 역할은 "다른 팀원이 즉시 붙을 수 있는 텍스트 기반 논문 데이터와 실행 환경"을 준비한다. 단순히 Docker와 Airflow를 띄우는 역할이 아니라, 논문 수집부터 PostgreSQL 적재, 최종 청크 생성, 최소 retrieval까지를 하나의 선행 완료 범위로 책임진다.

#### 소유 파일

**Docker · Compose · 스크립트**

- `docker-compose.dev.yml`
- `docker-compose.server.yml`
- `docker-compose.parser.yml`
- `docker/airflow/Dockerfile`
- `docker/dev/Dockerfile`
- `docker/parser/Dockerfile`
- `docker/mongo/Dockerfile`
- `docker/postgres/Dockerfile`
- `docker/postgres/init/01-create-app-db.sh`
- `scripts/setup-dev.sh`
- `scripts/setup-server.sh`
- `scripts/port-forward.sh`

**Airflow DAG 정의**

- `dags/daily_collect.py`
- `dags/maintenance.py`

**파이프라인 진입점**

- `src/pipeline/__init__.py`
- `src/pipeline/collect_papers.py`
- `src/pipeline/enrich_papers_metadata.py`
- `src/pipeline/prepare_papers.py`
- `src/pipeline/embed_papers.py`
- `src/pipeline/analyze_topics.py`
- `src/pipeline/tracing.py`

**수집 · 파싱 · 적재**

- `src/integrations/paper_search.py`
- `src/integrations/raw_store.py`
- `src/integrations/paper_repository.py`
- `src/integrations/topic_repository.py`
- `src/integrations/fulltext_parser.py`
- `src/integrations/layout_parser_client.py`
- `src/integrations/paper_retriever.py`

**공용 설정**

- `src/shared/__init__.py`
- `src/shared/settings.py`
- `src/shared/langsmith.py`

#### 구현 대상

**개발 환경과 서버 환경 안정화**

- dev 컨테이너와 server stack이 모두 정상 기동해야 한다.
- PostgreSQL + pgvector, MongoDB, Airflow 웹/스케줄러/프로세서가 정상 연결되어야 한다.
- `.env` 기준 설정명이 프로젝트 계약과 일치해야 한다.

**HF Daily Papers 수집과 원본 저장**

- `PaperSearchClient.fetch_daily_papers(date)`를 구현한다.
- 응답이 `list` 형태라는 점을 반영해 처리한다.
- `RawPaperStore.save_daily_papers_response(date, payload)`로 MongoDB에 원본을 저장한다.
- 과거 원본을 장기적으로 채우기 위해 cursor 기반 `backfill_collect_papers` 경로를 운영한다.
- backfill은 하루 최대 30일 단위로 진행하고, 이미 저장된 날짜는 skip하며, MongoDB pipeline state에 진행 상태를 남긴다.

**arXiv 메타데이터 후속 보강**

- `prepare_papers`는 HF raw 기반 최소 메타데이터만으로도 적재를 진행할 수 있어야 한다.
- `enrich_papers_metadata`는 PostgreSQL에 저장된 논문 중 `primary_category`, `categories`, canonical `pdf_url` 등이 비어 있는 항목을 대상으로 arXiv 메타데이터를 후속 보강한다.
- 이 단계는 서버에서 천천히 돌아가는 보조 워크플로우로 운영한다.

**arXiv 메타데이터 보강**

- `fetch_arxiv_metadata(arxiv_ids)`를 구현한다.
- 초록, primary category, PDF 링크, 발행일을 보강한다.
- 재시도와 지연 정책을 반영한다.

**PDF 본문 텍스트 파싱**

- HURIDOCS 레이아웃 파서를 우선 사용하고, 실패 시 `pypdf` fallback으로 본문을 추출한다.
- PDF에서 본문 텍스트와 섹션 정보를 추출한다.
- 표, 그림, 캡션은 semantic enrichment까지는 하지 않지만, `artifacts` 메타데이터로 함께 저장한다.
- 추출 결과는 `paper_fulltexts`에 `text`, `sections`, `quality_metrics`, `artifacts`, `parser_metadata` 형태로 저장할 수 있도록 정리한다.

**PostgreSQL 적재와 최종 청크 생성**

- 논문 메타데이터, 본문 텍스트, 최종 청크를 PostgreSQL에 적재한다.
- 이 역할이 쓰기 경로를 책임진다.
- 청크 전략은 이 단계에서 확정한다. 2번은 청크를 새로 자르는 역할이 아니라, 이미 저장된 청크를 기반으로 임베딩과 검색을 고도화하는 역할이다.
- 파싱 기준이 크게 바뀌면 MongoDB raw를 유지한 채 PostgreSQL 정제층을 초기화하고 다시 적재하는 운영 경로도 이 역할이 관리한다.

**최소 retrieval 제공**

- vector retrieval이 완성되기 전에도 4번과 5번이 작업할 수 있도록, `paper_chunks` 기반 최소 retrieval 경로를 제공한다.
- 구현은 키워드 검색, FTS, 단순 chunk lookup 중 가장 안정적인 방식으로 시작할 수 있다.
- 반환 형태는 최종 vector retrieval과 최대한 맞춘다.

**DAG 오케스트레이션**

- DAG 파일은 얇게 유지한다.
- 실제 비즈니스 로직은 `src/pipeline`에서 실행한다.
- `collect -> prepare -> embed -> analyze` 흐름을 문서와 코드 모두에서 일관되게 유지한다.

#### 다른 역할에 제공해야 할 것

- 날짜 기준 원본 feed 수집 함수
- 과거 날짜 raw 백필 함수와 cursor 상태 저장 경로
- 저장된 논문에 대한 arXiv 메타데이터 후속 보강 함수
- arXiv 메타데이터 보강 함수
- MongoDB 저장 함수
- PostgreSQL 적재 결과
- 최종 청크가 적재된 데이터셋
- parser runtime 구성과 로컬 실행 경로
- 최소 retrieval 인터페이스
- `run_collect_papers()`, `run_prepare_papers()`, `run_embed_papers()`, `run_analyze_topics()` 진입점
- 통합 테스트에 사용할 최소 실데이터

#### 완료 기준

- `setup-dev.sh`, `setup-server.sh`가 실패 없이 실행된다.
- `docker-compose.parser.yml`로 로컬 parser를 실행할 수 있다.
- Airflow UI에서 `arxplore_*` 4개 DAG가 확인된다.
- 특정 날짜 기준 HF Daily Papers를 MongoDB에 저장할 수 있다.
- arXiv 보강과 PDF 본문 텍스트 파싱이 된다.
- PostgreSQL에 메타데이터, 본문 텍스트, 청크가 적재되고 `artifacts`, `parser_metadata`가 함께 저장된다.
- 최소 retrieval이 동작한다.
- 2~5번 역할이 같은 데이터셋 위에서 바로 시작할 수 있다.

### 7-2. 임베딩 · 벡터 검색 · 토픽 그룹핑 담당

이 역할의 책임은 "이미 적재된 청크를 검색 가능한 벡터 구조로 바꾸고, 최소 retrieval을 최종 검색 품질로 고도화하는 것"이다. 1번이 시스템을 먼저 움직이게 만드는 역할이라면, 2번은 검색 품질과 토픽 구성 품질을 책임지는 역할이다.

#### 소유 파일

- `src/integrations/embedding_client.py`
- `src/integrations/vector_repository.py`

필요에 따라 다음 파일을 새로 추가할 수 있다.

- `src/integrations/clustering.py`
- `src/integrations/retrieval_reranker.py`

#### 구현 대상

**임베딩 생성**

- `EmbeddingClient.embed_texts(texts)`를 구현한다.
- 배치 처리, 재시도, 모델 선택 기준을 정한다.

**pgvector 저장**

- `paper_embeddings` 테이블 구조를 설계하고 저장 경로를 구현한다.
- `VectorRepository.upsert_paper_embeddings()`를 제공한다.

**vector retrieval**

- `VectorRepository.search_paper_chunks(query_embedding, limit=5)`를 구현한다.
- 최소 retrieval과 동일한 반환 형태를 유지하도록 설계한다.
- 최종적으로 4번이 검색 구현을 바꿔 끼우더라도 응답 계층은 그대로 유지되게 한다.

**retrieval 품질 개선**

- top-k, score 기준, 검색 실패 시 fallback 전략을 검토한다.
- 필요 시 reranking이나 추가 검색 조건을 붙인다.

**토픽 그룹핑**

- 임베딩된 논문 또는 청크를 기준으로 유사 논문을 토픽 단위로 묶는다.
- 결과는 `topic_id -> arxiv_ids` 매핑 형태로 제공한다.
- 이 결과는 3번의 문서 생성 입력과 1번의 topic 저장 경로에 연결된다.

#### 다른 역할에 제공해야 할 것

- 임베딩 생성 함수
- vector retrieval 함수
- 토픽 그룹핑 결과 구조
- 최소 retrieval과의 교체 기준

#### 완료 기준

- 저장된 청크를 임베딩할 수 있다.
- vector retrieval이 동작한다.
- 반환 형태가 최소 retrieval과 호환된다.
- 토픽 그룹핑 결과를 1번과 3번이 사용할 수 있다.

### 7-3. 토픽 문서 생성 담당

이 역할은 "논문 묶음이 읽을 수 있는 토픽 문서로 바뀌는 품질"을 책임진다. 이 역할은 검색 응답 자체보다 `TopicDocument`라는 제품 핵심 산출물을 안정적으로 만드는 데 집중한다.

#### 소유 파일

- `src/core/prompts/overview.py`
- `src/core/prompts/key_findings.py`
- `src/core/chains.py`
- `src/core/tracing.py`

`src/core/models.py`는 직접 소유 파일이 아니다. 계약 변경이 필요하면 문서와 함께 전원 합의를 거쳐야 한다.

#### 구현 대상

**프롬프트 정교화**

- `overview`는 토픽 흐름을 3~5문장으로 설명해야 한다.
- `key_findings`는 연구 기여, 공통 경향, 차이를 항목형으로 정리해야 한다.
- 추측형 문장, 과장된 평가, 근거 없는 전망을 줄인다.

**체인 안정화**

- `_format_papers()`가 논문 메타데이터와 텍스트를 적절히 LLM 입력으로 전달하는지 점검한다.
- `_build_paper_refs()`와 `_build_related_topics()`가 결정적으로 조합되는지 확인한다.
- `analyze_topic()`이 항상 `TopicDocument` 구조를 반환하도록 안정화한다.

**문서 생성 품질 검토**

- 샘플 토픽 묶음으로 출력 품질을 반복 확인한다.
- 문서가 "토픽 수준 요약"인지 "개별 논문 설명 모음"인지 경계가 흐려지지 않게 조정한다.

#### 다른 역할에 제공해야 할 것

- `analyze_topic()` 진입점
- `TopicDocument` 샘플 출력
- 문서 생성 품질 기준과 trace 태그

#### 완료 기준

- 샘플 논문 묶음에서 `TopicDocument`를 안정적으로 생성할 수 있다.
- 개요와 핵심 발견이 역할별로 분리되어 있다.
- 저장 가능한 형태의 문서 출력이 준비된다.

### 7-4. RAG 응답 담당

이 역할은 "검색 결과가 사용자에게 신뢰 가능한 응답으로 바뀌는 품질"을 책임진다. 3번이 문서를 생성하는 역할이라면, 4번은 검색 결과를 근거로 질문에 답하는 역할이다.

#### 소유 파일

- `src/core/rag.py`

필요 시 다음 파일을 새로 추가할 수 있다.

- `src/core/prompts/answer.py`
- `src/core/retrievers.py`

#### 구현 대상

**응답 흐름 구현**

- `answer_question()`을 구현한다.
- 먼저 1번의 최소 retrieval 위에서 응답 흐름을 만든다.
- 이후 2번의 vector retrieval로 같은 인터페이스를 유지한 채 교체 가능해야 한다.

**응답 정책 정리**

- 검색 결과 범위 안에서만 답변한다.
- 검색 결과가 부족하면 부족하다고 말한다.
- 근거 논문과 관련 토픽을 함께 반환한다.

**retrieval 연동 정리**

- 1번과 2번이 제공하는 retrieval 구현체를 같은 입력/출력 형태로 소비한다.
- retrieval이 바뀌더라도 응답 계층이 크게 흔들리지 않도록 설계한다.

**LangSmith 평가**

- 응답 품질과 근거 노출 품질을 trace로 점검한다.
- 검색 결과 부족 시 동작, 과도한 일반화 여부, 근거 노출 형식 등을 검토한다.

#### 다른 역할에 제공해야 할 것

- `answer_question()` 진입점
- 응답 포맷 계약
- 근거 논문/관련 토픽 반환 예시

#### 완료 기준

- 최소 retrieval 기준으로도 응답 흐름이 동작한다.
- vector retrieval 교체 후에도 반환 형태가 유지된다.
- 검색 결과 부족 상황에서도 과도한 환각 없이 응답한다.

### 7-5. UI · 문서 소비 계층 담당

이 역할은 "현재 저장소가 사용자에게 어떤 경험으로 보이는가"를 책임진다. 텍스트 중심 제품 방향에 맞게 카드, 문서, 검색 결과를 구조적으로 보여 주는 것이 핵심이다.

#### 소유 파일

- `app/main.py`
- `app/components/topic_card.py`
- `app/components/section_renderer.py`
- `app/pages/topic_detail.py`

필요 시 UI 보조 컴포넌트를 추가할 수 있다.

#### 구현 대상

**메인 화면 흐름**

- 검색 입력
- 답변 결과 영역
- 토픽 카드 영역
- 빈 상태와 오류 상태

**카드 렌더링**

- 토픽 제목
- 짧은 개요
- 논문 수
- 생성 시각 또는 최근성 힌트

**상세 문서 렌더링**

- 개요
- 핵심 발견
- 논문 목록
- 관련 토픽
- 목차 기반 이동

**실데이터 연결 대비**

- 데모 데이터와 실데이터가 같은 렌더링 경로를 타도록 구조를 정리한다.
- 최소 retrieval과 최종 retrieval이 같은 응답 형태를 유지하도록 UI 의존성을 최소화한다.
- DB 조회 실패, 문서 없음, 검색 결과 부족 상태를 화면에서 처리한다.

#### 다른 역할에 제공해야 할 것

- 카드/상세 페이지가 기대하는 데이터 형태
- 검색 응답이 UI에서 어떻게 소비되는지에 대한 요구사항
- 오류 상태와 로딩 상태 정책

#### 완료 기준

- 데모 데이터 기준으로 메인/카드/상세 흐름이 안정적으로 동작한다.
- 실데이터로 바꿔도 같은 컴포넌트 구조를 유지할 수 있다.
- 카드와 상세 문서가 `TopicDocument` 계약에 직접 의존하도록 정리되어 있다.

## 8. 역할 간 handoff 체크리스트

### 1번이 넘겨야 하는 것

- 샘플 HF Daily Papers 원본 payload
- arXiv 보강 후 paper dict 예시
- PDF 본문 텍스트 예시
- `artifacts`와 `parser_metadata` 예시
- 최종 청크 예시
- 최소 retrieval 입력/출력 예시
- `.env` 기준 환경 변수 설명
- Airflow 실행 방법

### 2번이 넘겨야 하는 것

- 임베딩 저장 구조
- vector retrieval 입력/출력 예시
- 최소 retrieval과의 호환 여부
- 토픽 그룹핑 결과 구조

### 3번이 넘겨야 하는 것

- `TopicDocument` 샘플 출력
- 문서 생성 품질 기준
- analyze trace 예시

### 4번이 넘겨야 하는 것

- 질문 입력과 응답 포맷 예시
- 근거 논문/관련 토픽 반환 예시
- 검색 결과 부족 시 응답 예시

### 5번이 넘겨야 하는 것

- 화면 상태 정의
- 필요한 조회 함수 목록
- 카드/상세/검색 응답 렌더링 요구사항

## 9. 변경 금지 또는 협의 필수 항목

다음 항목은 개인 판단으로 바꾸지 않는다.

- `TopicDocument` 필드 구조
- 공용 import 경로
- DAG 이름
- Compose 서비스명
- `.env`의 핵심 설정 키
- 저장소 전역 용어
- 최소 retrieval과 vector retrieval의 공용 반환 형태

이 항목을 바꿔야 하면 관련 담당자와 문서부터 같이 업데이트해야 한다.

## 10. 최종 완료 조건

역할별 구현이 끝났다고 보기 위한 최종 기준은 다음과 같다.

- 1번이 텍스트 기반 데이터 준비, 적재, 최소 retrieval까지 완료한다.
- 2번이 vector retrieval과 토픽 그룹핑을 붙인다.
- 3번이 `TopicDocument`를 안정적으로 생성한다.
- 4번이 최소 retrieval과 vector retrieval 모두에서 응답 흐름을 유지한다.
- 5번이 검색, 카드, 상세 문서를 실데이터로 렌더링한다.
- 역할 간 임시 코드가 아니라 공용 계약 기반으로 통합돼 있다.

이 문서는 구현이 진행되면서 구체화될 수 있지만, 책임 경계 자체를 흐리는 방향으로 바뀌어서는 안 된다.
