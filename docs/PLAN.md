# ArXplore 계획

## 1. 목표

본 프로젝트는 최신 AI 논문을 수집하고, 이를 토픽 문서와 RAG 질의응답으로 재구성해 사용자가 더 빠르게 이해할 수 있도록 돕는 플랫폼을 만드는 것을 목표로 한다. 단순한 논문 링크 모음이 아니라, 토픽 단위 문서와 검색 기반 질문응답을 결합한 탐색 시스템을 지향한다.

AI 논문은 표와 그림도 중요하지만, 최신 연구를 발견하고 핵심 내용을 요약하며 토픽 흐름을 탐색하는 사용자 경험은 텍스트 정보만으로도 충분히 유의미하게 구성할 수 있다. ArXplore는 이 지점에 집중해 텍스트 기반 논문 탐색과 질의응답을 우선적인 제품 가치로 삼는다.

ArXplore가 해결하려는 핵심 문제는 다음과 같다.

- 최신 AI 논문은 빠르게 쏟아지지만, 사용자가 직접 골라 읽고 맥락을 연결하기 어렵다.
- 논문 abstract만으로는 연구 흐름과 차이를 빠르게 파악하기 어렵다.
- 영어 논문을 한국어로 빠르게 이해하고 다시 질문할 수 있는 도구가 부족하다.
- 검색 기반 Q&A와 문서형 탐색이 따로 존재해 사용 경험이 끊긴다.

따라서 본 서비스는 두 가지 경험을 하나로 결합한다.

1. 사용자가 질문을 입력하면 관련 논문 청크와 토픽 문서를 검색해 근거 기반으로 답변하는 검색 중심 경험
2. 사용자가 질문 없이도 토픽 카드와 상세 문서를 따라 최신 AI 연구 흐름을 읽는 탐색 중심 경험

이 프로젝트의 핵심 가치는 다음과 같다.

- `발견 비용 감소`: HF Daily Papers를 이용해 최신 AI 논문 후보군을 먼저 좁힌다.
- `이해 비용 감소`: 여러 논문을 하나의 토픽 문서로 재구성해 맥락을 빠르게 파악하게 한다.
- `한국어 접근성`: 최신 AI 연구를 한국어 기반 요약과 Q&A로 소비할 수 있게 한다.
- `근거가 있는 응답`: 답변과 함께 관련 논문과 토픽을 제시한다.
- `검색과 탐색의 결합`: 검색창 중심 사용성과 문서형 탐색 사용성을 하나의 UI 흐름으로 묶는다.

## 2. 도메인 범위

ArXplore는 전체 학술 논문 플랫폼이 아니라, 최신 AI 연구 탐색 플랫폼을 지향한다. 즉, 처음부터 전 분야 논문을 다루지 않고 AI 관련 논문에 초점을 맞춘다.

초기 포함 범위는 다음과 같다.

- `cs.AI`
- `cs.CL`
- `cs.CV`
- `cs.LG`
- `cs.RO`
- 필요 시 `stat.ML`

초기 제외 또는 보수 처리 범위는 다음과 같다.

- 일반 수학, 물리, 바이오 전반
- AI와 직접 관련성이 낮은 시스템 논문
- 카테고리는 AI여도 제품 목적과 거리가 큰 논문

이 범위 제한은 단점이 아니라 품질 확보 전략이다. AI 논문만 깊게 다루는 편이 토픽화, 프롬프트, UI 문구, 검색 품질을 모두 안정화하기 쉽다.

## 3. 데이터 소스 해석

ArXplore는 다음 세 층의 소스를 구분한다.

- `1차 큐레이션 소스`: Hugging Face Daily Papers
- `원본 메타데이터 기준`: arXiv API
- `선택적 보조 지표`: HF upvotes, GitHub repo / stars, optional citation count

핵심 해석은 다음과 같다.

- HF Daily Papers는 "최신 AI 논문 후보를 이미 한 번 큐레이션한 feed"다.
- 이는 제품 관점의 1차 필터링 의미를 가지지만, 논문이 학술적으로 완전히 검증됐다는 뜻은 아니다.
- arXiv는 메타데이터 정규화 기준으로 사용한다.
- citation count는 메인 가치가 아니라 후순위 보조 지표로 취급한다.

즉, ArXplore는 "검증 완료 논문 저장소"가 아니라 "큐레이션된 최신 AI 연구 탐색 도구"로 정의해야 한다.

## 4. 실제 확인한 수집 구조

계획은 추상 아이디어가 아니라 실제 API 형태를 기준으로 세워야 한다. 현재 확인한 내용은 다음과 같다.

### HF Daily Papers

- 날짜 기준 feed를 조회할 수 있다.
- 응답은 검색 API처럼 단일 객체가 아니라 `list` 형태의 항목 배열이다.
- 각 항목에는 논문 정보, 저자, 발행 시각, HF upvotes, GitHub 정보 등이 포함될 수 있다.
- 제품적으로는 "이미 한 번 큐레이션된 AI 논문 후보 목록"으로 해석할 수 있다.

### arXiv API

- `id_list` 기반 조회가 가능하다.
- 초록, 카테고리, primary category, PDF 링크, 발행일을 보강할 수 있다.
- 논문 메타데이터 정규화에 적합하다.
- 연속 호출 시 딜레이를 두는 것이 권장된다.

### Citation Count

- 외부 메타데이터 API를 붙이면 추가할 수는 있다.
- 하지만 신규 arXiv preprint는 즉시 안정적으로 매칭되지 않을 수 있다.
- 따라서 계약에는 optional 필드로 열어 두되, 핵심 파이프라인의 성공 조건으로 두지 않는다.

결론적으로 `HF Daily Papers -> arXiv -> PostgreSQL / MongoDB` 수집 구조는 실현 가능하다. 리스크는 API 접근성보다도 계약 설계, natural key 선택, 후속 메타데이터 갱신 전략에 있다.

## 5. 제품 산출물

본 프로젝트의 주요 산출물은 다음과 같다.

1. 수집 및 전처리 파이프라인
2. 논문과 토픽을 저장하는 데이터 계층
3. `TopicDocument`를 생성하는 LLM 체인
4. 논문 청크 기반 RAG 질의응답
5. Streamlit 기반 검색/탐색 UI
6. 아키텍처, 역할, 운영 규칙 문서
7. Airflow 기반 배치 실행 구조

## 6. 현재 우선 범위

### 현재 단계에서 이미 반영된 것

- HF Daily Papers 수집 경로
- HF Daily Papers 과거 raw 백필 경로
- arXiv 메타데이터 후속 보강 경로
- MongoDB 원본 저장
- PostgreSQL `papers`, `paper_fulltexts`, `paper_chunks` 적재
- HURIDOCS + `pypdf` fallback 기반 PDF 본문 텍스트 파싱
- 최종 청크 분할과 품질 메트릭 계산
- `paper_fulltexts.artifacts`, `parser_metadata` 저장
- 로컬 parser 컨테이너와 로컬 `prepare_papers` 실행 경로

### 현재 범위에서 이어서 구현할 것

- 최소 retrieval 경로 고도화
- 임베딩 생성 및 벡터 검색
- 토픽 그룹핑
- `TopicDocument` 생성
- 검색창 기반 RAG 질문응답
- 토픽 카드와 상세 문서 UI

### 현재 범위에서 보수적으로 두는 것

- citation count 정교한 반영
- GitHub activity 변화량 추적
- 장기 토픽 변화 히스토리
- 문서 버전 비교
- 고급 랭킹 로직

즉, 현재 범위는 "텍스트 기반으로도 가치를 드러낼 수 있는 최소 완성 구조"를 우선 목표로 하고, 메트릭 고도화나 장기 관찰 기능은 이후 단계로 미룬다.

## 7. 현재 저장소 상태

현재 저장소는 도메인 전환만 끝낸 스캐폴드 상태를 이미 넘어서 있으며, 다음이 ArXplore 기준으로 실제 구현되어 있다.

- 코어 모델: `TopicDocument`, `PaperRef`, `RelatedTopic`
- 프롬프트: 논문 토픽 요약 기준으로 재정의
- 체인: `analyze_topic()` 중심 구조
- 통합 계층: `paper_search`, `paper_repository`, `topic_repository`
- PDF 파싱: `fulltext_parser`, `layout_parser_client`
- 파이프라인: `collect_papers`, `backfill_collect_papers`, `prepare_papers`, `enrich_papers_metadata`, `embed_papers`, `analyze_topics`
- Airflow DAG: `arxplore_*` 네이밍과 raw backfill DAG
- UI: 토픽 카드, 토픽 상세, ArXplore 데모 데이터
- Docker / Compose / scripts / docs: ArXplore 기준 명칭과 구조로 전환

즉, 현재 단계는 "수집과 전처리 파이프라인은 실제로 동작하고, 그 위에 검색·생성 계층을 이어 붙이는 단계"라고 보는 것이 정확하다.

## 8. 핵심 사용자 경험

### 8-1. 검색 중심 경험

메인 화면 상단에는 검색엔진 스타일의 큰 입력창을 배치한다. 사용자는 자연어 질문을 입력하고, 시스템은 관련 논문 청크와 토픽 문서를 검색한 뒤 LLM이 그 범위 안에서 답변한다.

질문 예시는 다음과 같다.

- 최근 speculative decoding 연구 흐름이 뭐야?
- 최신 vision-language agent 논문을 토픽별로 정리해줘
- 이 토픽과 관련된 다른 논문은 뭐가 있어?

이때 답변은 검색 없이 생성되면 안 된다. 검색 결과가 부족하면 답변도 이를 드러내야 한다.

### 8-2. 탐색 중심 경험

검색창 아래에는 토픽 카드 영역을 둔다. 사용자는 질문 없이도 현재 어떤 AI 연구 흐름이 있는지 토픽 카드만으로 빠르게 훑어볼 수 있어야 한다.

카드를 선택하면 토픽 상세 페이지로 이동한다. 상세 페이지는 게시글이 아니라 문서처럼 읽히는 구조를 가져야 한다.

### 8-3. 문서형 상세 경험

상세 페이지는 다음 요소를 포함한다.

- 개요
- 핵심 발견
- 논문 목록
- 관련 토픽
- 문서 내부 목차

이 구조는 나무위키식 문서 탐색 경험의 일부를 참고하되, 협업 편집이 아니라 "구조화된 읽기와 관련 토픽 이동"에 초점을 둔다.

## 9. 데이터 계약

시스템 전체가 공유하는 핵심 도메인 계약은 다음과 같다.

```python
class PaperRef(BaseModel):
    arxiv_id: str
    title: str
    authors: list[str]
    abstract: str
    pdf_url: str
    published_at: datetime | None = None
    upvotes: int = 0
    github_url: str | None = None
    github_stars: int | None = None
    citation_count: int | None = None

class RelatedTopic(BaseModel):
    topic_id: int
    title: str

class TopicDocument(BaseModel):
    topic_id: int
    title: str
    overview: str
    key_findings: list[str]
    papers: list[PaperRef]
    related_topics: list[RelatedTopic]
    generated_at: datetime
```

이 모델은 다음 계층이 모두 공유한다.

- LLM 분석 체인의 최종 출력
- PostgreSQL `topic_documents` 저장 구조
- Streamlit 카드/상세 페이지 렌더링 입력
- RAG 답변에서 참조할 토픽 문서 데이터

따라서 계약 변경은 코어 모델만의 문제가 아니라 체인, 저장, UI, 문서를 함께 움직이는 작업이다.

## 10. 저장 구조

### MongoDB

MongoDB는 HF Daily Papers 원본 응답을 그대로 저장한다. 날짜, 수집 시각, payload 전체를 함께 보존해 추후 재처리와 디버깅에 사용한다.

### PostgreSQL + pgvector

PostgreSQL과 pgvector는 정제된 논문과 검색 데이터를 저장한다. 기본 목표 테이블은 다음과 같다.

- `papers`
- `paper_fulltexts`
- `paper_chunks`
- `paper_embeddings`
- `topics`
- `topic_documents`

이 구조를 택한 이유는 다음과 같다.

- `papers`는 논문 메타데이터의 기준 테이블이다.
- `paper_fulltexts`는 PDF에서 추출한 본문 텍스트와 섹션 정보에 더해 `quality_metrics`, `artifacts`, `parser_metadata`를 저장하는 기준 테이블이다.
- `paper_chunks`와 `paper_embeddings`는 RAG 검색의 핵심 데이터다.
- `topics`와 `topic_documents`는 카드와 상세 문서의 핵심 데이터다.
- 토픽 문서는 JSONB로 저장해 공용 계약과 UI 렌더링을 단순하게 유지한다.

초기 계획에서 생각할 수 있었던 `document_sections`나 `document_source_refs` 같은 분리형 구조는 현재 우선순위가 아니다. 지금은 `TopicDocument` 단위 저장이 스캐폴드와 구현 효율 측면에서 더 적절하다.

## 11. 배치 파이프라인

전체 흐름은 6개의 Airflow DAG를 기준으로 설계한다.

### `collect_papers`

- HF Daily Papers 날짜 feed 호출
- 원본 payload MongoDB 저장
- 수집 상태 기록

### `backfill_collect_papers`

- 과거 HF Daily Papers 날짜 feed를 하루 최대 30일씩 순차 수집
- 이미 MongoDB에 저장된 날짜는 skip
- MongoDB pipeline state에 cursor를 저장해 다음 run에서 이어받기
- 목표 시점에 도달하면 no-op 상태로 종료

### `enrich_papers_metadata`

- PostgreSQL에 먼저 저장된 논문 중 `primary_category`, `categories`가 비어 있는 항목을 대상으로 arXiv 메타데이터를 후속 보강
- `pdf_url`, `published_at`, `primary_category`, `categories`를 canonical 값으로 갱신
- 원본 수집/파싱과 분리해 서버에서 느리게 돌리는 보조 DAG

### `prepare_papers`

- HF 응답에서 arXiv ID 추출
- arXiv API 보강
- HURIDOCS + `pypdf` fallback 기반 PDF 본문 텍스트 파싱
- `artifacts`, `parser_metadata`, `quality_metrics` 생성
- AI 카테고리 필터링
- 중복 제거
- PostgreSQL `papers`, `paper_fulltexts`, `paper_chunks` upsert

### `embed_papers`

- 임베딩 생성
- pgvector 저장
- 유사 논문 토픽 그룹핑

### `analyze_topics`

- 토픽별 논문 묶음 로딩
- 개요 생성
- 핵심 발견 생성
- `TopicDocument` 저장

현재 저장소에서는 이 여섯 DAG와 `src/pipeline` 진입점이 이미 존재한다. 이 중 `collect_papers`, `backfill_collect_papers`, `prepare_papers`, `enrich_papers_metadata`는 실제 수집/보강/파싱/적재 경로에 연결돼 있으며, `embed_papers`와 `analyze_topics`는 아직 스캐폴드 중심으로 남아 있다. `prepare_papers`는 parser runtime을 통제하기 위해 현재 기준으로는 수동 실행을 유지한다.

## 12. RAG 질의응답 구조

질의응답 흐름은 다음과 같다.

1. 사용자가 질문을 입력한다.
2. 먼저 최소 retrieval 또는 vector retrieval을 통해 관련 논문 청크와 토픽 문서를 조회한다.
3. 검색 결과를 응답 체인이 조합한다.
4. LLM이 검색 결과 범위 안에서 답변한다.
5. 답변과 함께 근거 논문과 관련 토픽을 표시한다.

여기서 중요한 원칙은 다음 두 가지다.

- 검색 결과 없이 답하지 않는다.
- 검색 결과가 부족하면 부족하다고 말한다.

현재 구조에서는 1번 역할이 먼저 최소 retrieval을 제공하고, 이후 2번 역할이 이를 vector retrieval로 고도화하는 흐름이 현실적이다. 토픽 문서는 상위 맥락 설명과 탐색 연결에 활용한다.

## 13. UI 구성

UI는 크게 세 영역으로 나뉜다.

### 상단 검색 영역

- 자연어 질문 입력
- 답변 출력
- 근거 논문, 관련 토픽 표시

### 하단 토픽 카드 영역

- 최신 토픽 목록
- 주요 토픽 탐색
- 질문 없이도 연구 흐름 파악

### 상세 문서 영역

- 개요
- 핵심 발견
- 논문 목록
- 관련 토픽
- 목차 기반 이동

즉, UI는 단순 검색 페이지가 아니라 "검색 + 문서 탐색" 혼합 인터페이스여야 한다.

## 14. 구현 단계

전체 구현은 다음 순서로 진행하는 것이 가장 안전하다.

### Phase 1. 코어 계약과 설정

- `TopicDocument`, `PaperRef`, `RelatedTopic` 확정
- 프롬프트와 체인 이름 정리
- 설정 파일과 프로젝트명 전환

이 단계는 모든 코드가 의존하는 계약을 먼저 고정하는 단계다.

### Phase 2. 통합 계층과 적재 경로

- `PaperSearchClient`
- `RawPaperStore`
- `PaperRepository`
- `TopicRepository`
- `VectorRepository`

이 단계는 실제 데이터를 수집하고, 텍스트 기반 본문과 청크까지 저장하는 경로를 만드는 단계다.

### Phase 3. 파이프라인과 인프라

- DAG 등록
- `src/pipeline` 진입점 구현
- Docker / Compose / scripts 정비

이 단계는 팀이 같은 환경에서 통합 작업을 수행할 수 있게 하는 단계다.

### Phase 4. UI와 문서

- Streamlit 메인/카드/상세 구조 정리
- 데모 데이터와 실데이터 연결
- 운영 문서 상세화

이 단계는 사용자가 제품 흐름을 실제로 볼 수 있게 하는 단계다.

## 15. 역할 분담 전제

ArXplore는 5인 병렬 개발을 전제로 한다.

- 인프라 · 데이터 파이프라인
- 임베딩 · 벡터 검색 · 토픽 그룹핑
- 토픽 문서 생성
- RAG 응답
- UI · 문서 소비 계층

역할별 상세 소유 파일과 인터페이스는 [ROLES.md](./ROLES.md)에 따로 정리한다. 본 문서에서는 제품 목표와 전체 흐름, 데이터 구조를 정의한다.

## 16. 검증 체크리스트

- `docker compose -p arxplore_dev -f docker-compose.dev.yml up`
- `docker compose -p arxplore_server -f docker-compose.server.yml up`
- `docker compose -f docker-compose.parser.yml up -d --build`
- `python3 -c "from src.core import TopicDocument, PaperRef, RelatedTopic"`
- `python3 -m compileall src app dags`
- `streamlit run app/main.py`
- `rg "IssueDocument|news_search|article_scraper|newspedia_" src app dags docker scripts`
- Airflow DAG 목록에 `arxplore_daily_collect`, `arxplore_maintenance` 표시

이 체크리스트는 코드 피봇 검증과 현재 통합 검증의 최소 기준이다.

## 17. 비목표

현재 단계에서 다음 항목은 프로젝트의 핵심 성공 조건으로 두지 않는다.

- 완전한 학술 검증 시스템
- 모든 분야 논문 지원
- 표, 그림, 캡션, 수식의 완전한 semantic enrichment
- citation count 실시간 추적
- 고급 랭킹과 추천 시스템
- 복잡한 문서 버전 비교

이 비목표를 분명히 해야, ArXplore가 "최신 AI 연구 탐색"이라는 본래 목적에 집중할 수 있다.
