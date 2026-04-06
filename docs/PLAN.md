# ArXplore 계획

## 1. 목표

ArXplore는 최신 AI 논문을 수집하고, 이를 구조화된 논문 상세 문서와 RAG 기반 질의응답으로 재구성해 사용자가 더 빠르게 이해할 수 있도록 돕는 플랫폼을 만드는 것을 목표로 한다. 단순 논문 링크 모음이나 abstract 뷰어가 아니라, `검색`, `논문 상세 탐색`, `한국어 요약`, `근거 기반 응답`을 한 제품 흐름으로 묶는 것이 핵심이다.

ArXplore가 해결하려는 문제는 다음과 같다.

- 최신 AI 논문은 빠르게 쏟아지지만 직접 골라 읽고 맥락을 연결하기 어렵다
- abstract만으로는 연구 흐름과 기여 차이를 충분히 파악하기 어렵다
- 영어 논문을 한국어로 빠르게 이해하고 다시 질문할 수 있는 도구가 부족하다
- 검색과 문서형 탐색이 분리돼 있어 사용 흐름이 끊긴다

따라서 본 서비스는 두 가지 경험을 결합한다.

1. 사용자가 질문을 입력하면 관련 논문 청크를 검색해 근거 기반으로 답변하는 검색 중심 경험
2. 사용자가 질문 없이도 논문 목록과 상세 문서를 따라 최신 AI 연구 흐름을 읽는 탐색 중심 경험

## 2. 도메인 범위

ArXplore는 전체 학술 논문 플랫폼이 아니라 최신 AI 연구 탐색 플랫폼을 지향한다. 초기 범위는 다음 카테고리를 중심으로 본다.

- `cs.AI`
- `cs.CL`
- `cs.CV`
- `cs.LG`
- `cs.RO`
- 필요 시 `stat.ML`

이 범위 제한은 품질 확보 전략이다. 최신 AI 논문만 깊게 다루는 편이 논문 상세 구성, retrieval, prompt, UI 전반을 안정화하기 쉽다.

## 3. 데이터 소스 해석

ArXplore는 세 층의 소스를 구분한다.

- `1차 큐레이션 소스`: Hugging Face Daily Papers
- `원본 메타데이터 기준`: arXiv API
- `선택적 보조 지표`: HF upvotes, GitHub 정보, optional citation count

핵심 해석은 다음과 같다.

- HF Daily Papers는 "최신 AI 논문 후보를 한 번 큐레이션한 feed"다
- arXiv는 canonical 메타데이터 보강 기준이다
- citation count는 핵심 파이프라인의 성공 조건이 아니라 후순위 지표다

즉 ArXplore는 학술 검증 시스템이 아니라, 큐레이션된 최신 AI 연구 탐색 도구로 정의하는 것이 맞다.

## 4. 제품 산출물

본 프로젝트의 주요 산출물은 다음과 같다.

1. 수집 및 전처리 파이프라인
2. 논문을 저장하는 데이터 계층
3. retrieval 계층
4. 논문 상세 문서(`PaperDetailDocument`) 생성 체인
5. 한국어 상세 요약 및 근거 번역 체인
6. RAG 기반 질의응답 계층
7. Streamlit 기반 검색/탐색 UI
8. 운영 문서와 역할 문서

## 5. 현재 단계에서 이미 반영된 것

현재 코드 기준으로 이미 반영된 것은 다음과 같다.

- HF Daily Papers 최신 수집 경로
- HF Daily Papers 과거 raw 백필 경로
- arXiv 메타데이터 후속 보강 경로
- MongoDB raw 저장
- PostgreSQL `prepare_jobs` 기반 prepare queue
- 로컬 `prepare-worker` 기반 `prepare -> embed` 실행 경로
- HURIDOCS + `pypdf` fallback + abstract fallback 기반 PDF 파싱
- PostgreSQL `papers`, `paper_fulltexts`, `paper_chunks`, `paper_embeddings` 적재
- `paper_fulltexts.artifacts`, `parser_metadata`, `quality_metrics` 저장
- lexical retrieval, vector retrieval, rerank, content role penalty 기반 검색 기본형
- 로컬 parser 컨테이너와 retrieval 점검 notebook

즉 현재 단계는 "수집과 적재 파이프라인이 실제로 동작하고, 그 위에 retrieval과 생성 계층을 정교화하는 단계"로 보는 것이 정확하다.

## 6. 현재 범위에서 이어서 구현할 것

현재 우선 범위는 다음과 같다.

- hybrid retrieval 고도화와 평가셋 정리
- answer chain과 citation 정책
- 한국어 번역과 상세 요약 규칙
- 논문 상세 문서(`PaperDetailDocument`) 생성 품질과 평가 루프
- Streamlit 논문 목록/상세 소비 계층 완성

현재 범위에서 보수적으로 두는 것은 다음과 같다.

- citation count 정교한 반영
- GitHub activity 변화량 추적
- 고급 랭킹과 추천 시스템
- 표, 그림, 수식의 full semantic enrichment

## 7. 현재 저장소 상태

현재 저장소는 스캐폴드를 넘어 실제 운영 구조를 갖춘 상태다. 중요한 구현 요소는 아래와 같다.

- 코어 모델
  - `PaperRef`, `PaperDetailDocument`
- 파싱 계층
  - `src/integrations/layout_parser_client.py`
  - `src/integrations/fulltext_parser.py`
- queue 계층
  - `src/integrations/prepare_job_repository.py`
  - `src/pipeline/prepare_worker.py`
  - `scripts/prepare-worker.sh`
- retrieval 계층
  - `src/integrations/paper_repository.py`
  - `src/integrations/vector_repository.py`
  - `src/integrations/paper_retriever.py`
  - `src/integrations/embedding_client.py`
- 파이프라인 계층
  - `src/pipeline/collect_papers.py`
  - `src/pipeline/prepare_papers.py`
  - `src/pipeline/embed_papers.py`
  - `src/pipeline/enrich_papers_metadata.py`
- DAG
  - `dags/daily_collect.py`
  - `dags/maintenance.py`
- 운영 보조
  - `docker-compose.parser.yml`
  - `notebooks/retrieval_inspection.ipynb`

## 8. 핵심 사용자 경험

### 8-1. 검색 중심 경험

메인 화면 상단에 자연어 질문 입력창을 두고, 시스템은 관련 논문 청크를 검색한 뒤 근거 기반 답변을 생성한다. 답변에는 citation과 관련 논문을 함께 표시한다.

### 8-2. 논문 목록 탐색 경험

사용자가 질문 없이 메인 화면에 진입해도 HF-style 논문 목록만으로 현재 어떤 AI 연구가 올라오는지 파악할 수 있어야 한다.

### 8-3. 논문 상세 경험

논문 상세 페이지는 단순 게시글이 아니라 구조화된 문서다. 최소한 아래를 포함해야 한다.

- overview (논문 개요)
- key findings (핵심 포인트)
- detailed summary (상세 요약 — 메인 본문)
- translation (근거 chunk 번역)

## 9. 데이터 계약

시스템 전체가 공유하는 핵심 도메인 계약은 `PaperRef`와 `PaperDetailDocument`다.

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

class PaperDetailDocument(BaseModel):
    arxiv_id: str
    title: str
    overview: str
    key_findings: list[str]
    generated_at: datetime
```

이 계약은 생성 체인, 저장 계층, UI 소비 계층이 동시에 공유한다. 따라서 필드 변경은 단일 계층의 로컬 수정이 아니라 시스템 전반 변경으로 취급해야 한다.

## 10. 저장 구조

### MongoDB

MongoDB는 HF Daily Papers raw payload의 source of truth다. 날짜, 수집 시각, 원본 payload, backfill state를 저장한다.

### PostgreSQL + pgvector

PostgreSQL은 정제 데이터와 운영 queue를 함께 저장한다.

핵심 데이터 테이블:

- `papers`
- `paper_fulltexts`
- `paper_chunks`
- `paper_embeddings`

운영 테이블:

- `prepare_jobs`

`prepare_jobs`는 사용자 노출용 데이터는 아니지만 현재 운영 구조의 핵심이다. `daily_collect`와 로컬 `prepare-worker`를 연결하며, 상태 관리와 retry, stale recovery 기준을 갖는다.

## 11. 배치 파이프라인

현재 운영 모델은 2개의 서버 DAG와 1개의 로컬 worker를 기준으로 한다.

### `arxplore_daily_collect`

- HF Daily Papers 최신 날짜 feed 호출
- raw payload MongoDB 저장
- prepare 대상 날짜를 PostgreSQL `prepare_jobs`에 enqueue

### `arxplore_maintenance`

- 과거 HF Daily Papers raw를 하루 최대 30일 단위로 backfill
- 이미 저장된 날짜는 skip
- backfill 상태를 저장해 다음 run에서 이어받기
- PostgreSQL에 저장된 논문 중 metadata가 부족한 항목을 대상으로 arXiv 보강

### `prepare-worker`

- 로컬 runtime에서 `prepare_jobs`를 소비
- `prepare_papers`를 호출해 `papers`, `paper_fulltexts`, `paper_chunks`를 적재
- 성공한 논문에 대해 `embed_papers`를 이어서 수행
- 결과는 서버 PostgreSQL에 직접 적재

즉 현재 구조는 "서버가 raw를 수집하고 큐를 넣으면, 로컬 worker가 무거운 prepare와 embed를 수행하는 분리형 구조"다.

## 12. 파싱 구조

현재 PDF 파싱은 아래 순서로 동작한다.

1. HURIDOCS layout parser 호출
2. 실패 또는 무응답 시 `pypdf` fallback
3. 둘 다 실패하면 abstract fallback

파싱 결과는 단순 본문 텍스트만 저장하지 않는다. 아래 정보도 함께 저장한다.

- `sections`
- `quality_metrics`
- `artifacts`
- `parser_metadata`

이 구조를 택한 이유는 텍스트 중심 서비스를 우선하면서도, 이후 parser 품질 개선과 artifact 활용 가능성을 남기기 위해서다.

## 13. retrieval과 RAG 구조

질의응답 흐름은 다음과 같다.

1. 사용자가 질문을 입력한다
2. lexical, vector, hybrid retrieval이 관련 논문 청크를 조회한다
3. retrieval 결과를 answer chain이 조합한다
4. LLM이 검색 결과 범위 안에서 답변한다
5. 답변과 함께 citation, 관련 논문을 표시한다

현재 핵심 원칙은 다음 두 가지다.

- 검색 결과 없이 답하지 않는다
- 검색 결과가 부족하면 부족하다고 말한다

## 14. 구현 단계

현재 구현 단계는 아래 순서로 정리하는 것이 가장 안전하다.

### Phase 1. 검색 계층 정교화

- retrieval 반환 shape 고정
- rerank와 hybrid 정책 안정화
- 평가셋 정리

### Phase 2. 응답 계층 정리

- answer chain 설계
- citation 정책 고정
- answer payload 정리

### Phase 3. 한국어 산출물 정리

- 번역 규칙
- 상세 요약 구조
- 용어 및 문체 기준

### Phase 4. 논문 상세 문서 정리

- `PaperDetailDocument` 생성 chain 안정화
- overview / key findings 품질 개선
- 평가 루프 정리

### Phase 5. UI 통합

- 논문 목록 화면
- 논문 상세 화면
- 검색 + answer payload 소비
- 상세 요약 / 번역 연결

## 15. 역할 분담 전제

ArXplore는 현재 5역할 병렬 개발을 전제로 한다.

- Retrieval · 검색 품질
- RAG 응답 · 근거 제어
- 한국어 번역 · 상세 요약 프롬프트
- 논문 상세 · 프롬프트 평가
- UI · 문서 소비 계층

상세 역할 경계와 handoff는 [ROLES.md](./ROLES.md)를 기준으로 한다.

## 16. 검증 체크리스트

- `bash scripts/setup-dev.sh`
- `bash scripts/setup-server.sh`
- `docker compose -f docker-compose.parser.yml up -d --build`
- `python3 -m compileall src app dags`
- `bash scripts/prepare-worker.sh once`
- `streamlit run app/main.py --server.address=0.0.0.0`
- `streamlit run app/paper_detail_demo.py --server.address=0.0.0.0`
- Airflow DAG 목록에 `arxplore_daily_collect`, `arxplore_maintenance`가 표시되는지 확인
- `notebooks/retrieval_inspection.ipynb`로 적재 상태와 retrieval 결과를 확인

## 17. 비목표

현재 단계에서 아래 항목은 핵심 성공 조건으로 두지 않는다.

- 완전한 학술 검증 시스템
- 모든 분야 논문 지원
- 표, 그림, 수식의 정밀 semantic enrichment
- citation count 실시간 추적
- 복잡한 추천 시스템
- 고급 문서 버전 비교
- 토픽 단위 그룹핑/클러스터링

이 비목표를 분명히 해야 ArXplore가 "최신 AI 연구를 한국어로 빠르게 이해하고 질문할 수 있게 하는 탐색 도구"라는 본래 목적에 집중할 수 있다.
