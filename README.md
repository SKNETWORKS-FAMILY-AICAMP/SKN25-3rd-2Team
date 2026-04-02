# ArXplore

ArXplore는 Hugging Face Daily Papers와 arXiv를 바탕으로 최신 AI 논문을 수집하고, 이를 한국어 `TopicDocument`와 RAG 질의응답으로 탐색할 수 있게 만드는 AI 논문 기반 RAG 플랫폼입니다. 상단 검색창에서는 논문 근거 기반 질문응답을 제공하고, 하단 토픽 카드와 상세 문서에서는 최신 연구 흐름을 문서형으로 탐색할 수 있게 하는 것이 목표입니다.

AI 논문은 표와 그림도 중요하지만, 최신 연구를 발견하고 핵심 내용을 요약하며 토픽 흐름을 탐색하는 경험은 텍스트 정보만으로도 충분히 유의미하게 구성할 수 있습니다. ArXplore는 이 지점에 집중해 텍스트 기반 논문 탐색과 질의응답을 먼저 잘 작동하게 만드는 방향을 취합니다.

현재 저장소는 실서비스 완성본이 아니라, 팀이 병렬 구현을 시작할 수 있도록 계약, 디렉토리 구조, Airflow DAG 진입점, Streamlit 데모 UI, Docker 기반 실행 환경, 운영 문서를 ArXplore 기준으로 정리한 상태입니다. 실제 수집·저장·임베딩·검색·응답 로직은 역할 분담에 따라 이어서 채워 넣는 구조입니다.

## 1. 왜 ArXplore인가

최신 AI 논문은 이미 많이 공개되고 있지만, 사용자가 매일 직접 찾아 읽고 맥락을 연결하기에는 비용이 큽니다. ArXplore는 이 문제를 다음 방식으로 줄이려 합니다.

- `발견 비용 감소`: HF Daily Papers를 1차 큐레이션 소스로 사용해 최신 AI 논문 후보군을 먼저 좁힙니다.
- `이해 비용 감소`: 개별 초록을 나열하는 대신 토픽 단위로 묶어 개요와 핵심 발견을 제공합니다.
- `텍스트 중심 탐색`: 표와 그림 중심 정밀 분석보다, 텍스트 기반 발견·요약·탐색 경험을 우선 완성합니다.
- `한국어 접근성 확보`: 최신 AI 연구 흐름을 한국어 문서와 한국어 질문응답으로 소비할 수 있게 합니다.
- `근거 기반 응답`: 답변과 함께 관련 논문과 토픽 문서를 함께 제시해 출처를 확인할 수 있게 합니다.
- `검색과 탐색 결합`: 검색창으로 질문할 수도 있고, 카드와 관련 토픽 링크를 따라 문서처럼 탐색할 수도 있게 합니다.

이 프로젝트의 핵심 가치는 "논문을 다시 모아 보여 주는 것"이 아니라, "큐레이션된 최신 AI 연구를 토픽 단위로 빠르게 이해하고 다시 질문할 수 있게 만드는 것"에 있습니다.

## 2. 데이터 소스 원칙

ArXplore는 다음 세 층의 소스를 구분합니다.

- `HF Daily Papers`: 1차 큐레이션 소스
- `arXiv API`: 원본 메타데이터 정규화 소스
- `선택적 보조 지표`: HF upvotes, GitHub repo / stars, optional citation count

여기서 중요한 해석은 다음과 같습니다.

- HF Daily Papers는 "최신 AI 논문 후보를 큐레이션한 feed"이지, 학술적으로 완전히 검증된 논문 목록을 뜻하지 않습니다.
- arXiv는 주로 preprint 성격의 원문 메타데이터 소스이므로, ArXplore는 이를 "최신 연구 탐색용"으로 다룹니다.
- citation count는 메인 가치가 아니라 후순위 보조 지표입니다. 계약에는 optional 필드로 열어 두되, 초기 구현에서 없어도 서비스 가치가 무너지지 않도록 설계합니다.

실제 확인 결과, HF Daily Papers API는 `date` 기준으로 논문 목록을 반환하며, 각 항목에는 논문 ID, 제목, 저자, 발행 시각, upvotes, GitHub 정보 등이 포함될 수 있습니다. arXiv API는 `id_list` 조회를 통해 초록, 카테고리, 발행일, PDF 링크를 보강할 수 있습니다.

## 3. 제품 목표

본 프로젝트는 다음 목표를 기준으로 진행합니다.

- 환각을 최소화하면서 팀이 수집한 논문 범위 안에서만 답변하는 RAG 질의응답 시스템을 구현합니다.
- 최신 AI 논문을 토픽 단위로 묶어 `TopicDocument` 형태의 구조화 문서를 생성합니다.
- PostgreSQL + pgvector를 사용해 논문 청크 검색과 토픽 기반 탐색을 동시에 지원합니다.
- LangChain 기반 Retriever + LLM 체인을 통해 검색 결과와 응답을 연결합니다.
- Streamlit UI에서 검색 중심 경험과 문서형 탐색 경험을 한 화면 흐름으로 제공합니다.

## 4. 현재 저장소 상태

현재 저장소에는 다음이 반영되어 있습니다.

- `TopicDocument`, `PaperRef`, `RelatedTopic` 공용 계약
- `collect_papers`, `prepare_papers`, `embed_papers`, `analyze_topics` 4단계 Airflow 스캐폴드
- `paper_search`, `paper_repository`, `topic_repository`, `vector_repository` 중심 통합 계층 뼈대
- MongoDB, PostgreSQL + pgvector, Airflow, dev 컨테이너용 Docker 설정
- Streamlit 기반 데모 UI
- 역할, 계획, 아키텍처, 워크플로우, 팀 환경 설정 문서

현재 기준에서 아직 구현이 필요한 영역은 다음과 같습니다.

- HF Daily Papers 실제 호출과 원본 저장
- arXiv 메타데이터 보강
- PDF 본문 텍스트 파싱과 PostgreSQL 적재
- 최종 청크 분할, 임베딩 생성, 최소 retrieval / vector retrieval
- 토픽 그룹핑
- LangChain 기반 Retriever + LLM 응답
- 실데이터 기반 카드/상세/질의응답 UI

즉, 지금 저장소는 "실행 가능한 스캐폴드와 계약"까지 준비된 상태이며, 텍스트 중심 기능 완성을 위한 각 역할별 구현이 뒤따라야 합니다.

## 5. 목표 사용자 경험

ArXplore의 목표 사용자 경험은 다음 흐름으로 정의합니다.

1. 사용자가 메인 화면 최상단 검색창에 자연어 질문을 입력합니다.
2. 시스템이 관련 논문 청크와 토픽 문서를 검색합니다.
3. LLM이 검색 결과 범위 안에서 답변을 생성합니다.
4. 답변 아래에는 근거 논문과 관련 토픽이 함께 표시됩니다.
5. 사용자는 질문 없이도 하단 카드 영역에서 최신 AI 연구 토픽을 훑어볼 수 있습니다.
6. 카드를 선택하면 토픽 상세 문서 페이지로 이동합니다.
7. 상세 페이지에서는 개요, 핵심 발견, 논문 목록, 관련 토픽을 따라 계속 탐색할 수 있습니다.

현재 Streamlit UI는 이 전체 흐름을 데모 데이터로 먼저 검증하는 단계입니다. 실데이터 연결은 저장 계층, 임베딩, RAG 구현이 들어오면 이어서 연결합니다.

## 6. 핵심 데이터 계약

ArXplore의 공용 도메인 계약은 `src/core/models.py`에 정의되어 있으며, 핵심 구조는 다음과 같습니다.

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

이 계약은 다음 계층이 모두 공유합니다.

- LLM 체인의 최종 출력
- PostgreSQL `topic_documents` 저장 구조
- Streamlit 카드/상세 문서 입력
- RAG 답변에서 노출할 토픽 문서 구조

따라서 이 구조를 바꿀 때는 코드 한 파일만 수정하면 안 되고, 코어 모델, 체인, 저장 계층, UI, 문서를 함께 갱신해야 합니다.

## 7. 파이프라인 개요

ArXplore는 4단계 파이프라인을 기준으로 설계합니다.

### `collect_papers`

- HF Daily Papers에서 날짜 기준 논문 feed를 가져옵니다.
- 원본 응답을 MongoDB에 저장합니다.
- 수집 시각과 날짜 단위 상태를 함께 기록합니다.

### `prepare_papers`

- HF 항목에서 arXiv ID를 추출합니다.
- arXiv API로 초록, 카테고리, PDF 링크, 발행일을 보강합니다.
- PDF에서 본문 텍스트와 섹션 정보를 파싱합니다.
- AI 관련 카테고리 기준으로 필터링하고 PostgreSQL `papers`, `paper_fulltexts`, `paper_chunks`에 저장합니다.

### `embed_papers`

- 임베딩을 생성합니다.
- `paper_embeddings`에 저장합니다.
- 최소 retrieval을 보완할 수 있는 vector retrieval 경로를 준비합니다.
- 유사 논문을 토픽 단위로 묶습니다.

### `analyze_topics`

- 토픽별 논문 묶음을 읽어 LLM으로 `TopicDocument`를 생성합니다.
- 생성 결과를 `topic_documents`에 저장합니다.
- 카드와 상세 문서에서 소비할 구조를 만듭니다.

## 8. 저장 구조

MongoDB와 PostgreSQL을 분리하는 이유는 저장 목적이 다르기 때문입니다.

### MongoDB

- HF Daily Papers 원본 응답 저장
- 재처리를 위한 payload 보존
- 수집 시점 상태 추적

### PostgreSQL + pgvector

- `papers`: 정제된 논문 메타데이터
- `paper_fulltexts`: PDF에서 추출한 본문 텍스트와 섹션 정보
- `paper_chunks`: RAG 검색용 최종 청크
- `paper_embeddings`: 임베딩 벡터
- `topics`: 토픽 그룹 메타데이터
- `topic_documents`: 생성된 토픽 문서 JSONB

초기 계획에서는 문서 하위 테이블을 많이 두는 방식도 가능했지만, 현재 ArXplore는 `TopicDocument` 계약을 JSONB로 저장하는 단순한 구조를 우선 사용합니다. 이 방식은 현재 스캐폴드 단계와 잘 맞고, UI와 체인 계약을 그대로 유지하기 쉽습니다. 또한 `paper_fulltexts`와 `paper_chunks`를 분리해 두면, 텍스트 파싱 단계와 retrieval 단계의 책임을 분명히 나누면서도 후속 검색 품질 개선을 유연하게 진행할 수 있습니다.

## 9. 빠른 시작

### 개발 컨테이너

대부분의 개발자는 아래 순서로 로컬 개발 컨테이너를 사용하면 됩니다.

```bash
bash scripts/setup-dev.sh
docker compose -p arxplore_dev exec dev bash
streamlit run app/main.py --server.address=0.0.0.0
```

접속 주소:

- Jupyter: `http://127.0.0.1:18888`
- Streamlit: `http://127.0.0.1:18501`

### 서버 스택

Airflow, MongoDB, PostgreSQL이 필요한 통합 작업은 아래 명령으로 서버 스택을 올립니다.

```bash
bash scripts/setup-server.sh
```

기본 컨테이너:

- `arxplore-postgres`
- `arxplore-mongodb`
- `arxplore-airflow-init`
- `arxplore-airflow-web`
- `arxplore-airflow-scheduler`
- `arxplore-airflow-dag-processor`

접속 주소:

- Airflow: `http://localhost:18080`
- MongoDB: `localhost:17017`
- PostgreSQL: `localhost:15432`

## 10. 검증에 자주 쓰는 명령

```bash
python3 -c "from src.core import TopicDocument, PaperRef, RelatedTopic"
python3 -m compileall src app dags
streamlit run app/main.py
rg "IssueDocument|news_search|article_scraper|newspedia_" src app dags docker scripts
docker compose -p arxplore_dev up
docker compose -p arxplore_server -f docker-compose.server.yml up
```

이 체크는 계약 import, 파이썬 문법, UI 실행, 주요 모듈 경로, 컨테이너 기동 상태를 빠르게 확인하는 데 사용합니다.

Jupyter에서 DB 적재 상태를 직접 확인하려면 로컬 `notebooks/inspect_ingestion.ipynb`를 사용합니다. 이 노트북은 `papers`, `paper_fulltexts`, `paper_chunks`, `quality_metrics`, minimum retrieval 결과를 SQLAlchemy와 repository helper로 함께 점검할 수 있게 구성되어 있습니다.

Airflow 수동 실행 시에는 다음 `dag_run.conf` 예시를 사용합니다.

```json
{"target_date": "2026-04-01"}
```

```json
{"target_date": "2026-04-01", "max_papers": 2}
```

현재 운영 기준은 다음과 같습니다.

- `arxplore_collect_papers`: 매일 `16:10 UTC` 자동 실행, HF Daily Papers 원본을 MongoDB에 저장
- `arxplore_prepare_papers`: 파싱 품질 검증을 위해 수동 실행 유지

첫 번째는 `arxplore_collect_papers`, 두 번째는 `arxplore_prepare_papers`용 예시입니다.

## 11. 저장소 구조

```text
app/                    Streamlit UI
dags/                   Airflow DAG 정의
docker/                 Docker 이미지와 DB 초기화 스크립트
docs/                   계획, 구조, 역할, 규칙, 팀 환경 설정 문서
notebooks/              Jupyter 점검/실험 노트북
scripts/                개발/서버 실행 스크립트
src/core/               TopicDocument, prompts, chains, rag
src/integrations/       외부 API, 저장소, 벡터 검색 연동 계층
src/pipeline/           DAG가 호출하는 실행 진입점
src/shared/             settings, tracing, LangSmith 연동
```

각 디렉토리는 단순 파일 분류가 아니라 역할 분담과 런타임 책임 경계를 반영합니다. 특히 `src/core`는 계약과 체인, `src/integrations`는 외부 연동과 저장, `src/pipeline`은 Airflow 오케스트레이션을 담당한다는 기준을 유지해야 합니다.

## 12. 문서 안내

- [docs/PLAN.md](./docs/PLAN.md): 제품 목표, 데이터 소스 해석, 현재 우선 범위, 파이프라인, 검증 기준
- [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md): 런타임 토폴로지, 계층 구조, 모듈 책임, 데이터 흐름
- [docs/ROLES.md](./docs/ROLES.md): 5인 팀 기준 역할 분담, 소유 파일, 구현 대상, 협업 인터페이스
- [docs/WORKFLOW.md](./docs/WORKFLOW.md): 구현 순서, 통합 절차, 운영 흐름
- [docs/TEAM_SETUP.md](./docs/TEAM_SETUP.md): 개발자와 인프라 담당자의 환경 준비 절차
- [docs/AGENTS.md](./docs/AGENTS.md): AI 도구 사용 시 지켜야 할 공통 계약과 금지 규칙

## 13. 현재 상태에 대한 메모

- 로컬 작업 디렉토리는 `ArXplore/` 기준으로 사용하는 것을 권장합니다.
- GitHub 저장소명 변경 여부는 별도 운영 결정으로 진행할 수 있습니다.
- 현재 ArXplore는 "AI 논문 기반 RAG 프로젝트"라는 도메인 전환과 구조 정리에 초점을 둔 상태이며, 구현 완성도보다 계약 일관성을 우선하고 있습니다.
