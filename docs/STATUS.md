# ArXplore 현재 구현 상태

이 문서는 2026-04-06 기준으로 프로젝트 전반의 구현 상태를 정리한 것이다. 팀원이 자기 담당 영역의 현재 상태와 의존 관계를 빠르게 파악하는 것이 목적이다.

현재 제품 우선순위는 `RAG 기반 답변 + 논문 상세 요약`이다. 제품 흐름은 `HF-style 논문 목록 → 논문 상세 → 상세 요약 / 근거 번역 / Q&A`로 확정됐다.

## 1. 모듈 상태 요약

### 실운영 (17개 모듈) — 수집, 파싱, 적재, 임베딩, 기본 retrieval

| 모듈 | 핵심 역할 |
|------|-----------|
| `fulltext_parser.py` | HURIDOCS→pypdf→abstract fallback, section/chunk/quality 전부 구현 |
| `paper_repository.py` | papers/fulltexts/chunks CRUD, FTS 4층 스코어링, chunk window |
| `paper_search.py` | HF Daily Papers fetch, arXiv metadata 보강, retry/rate-limit |
| `raw_store.py` | MongoDB raw 저장, backfill cursor, pipeline state |
| `prepare_job_repository.py` | PostgreSQL prepare_jobs queue, LISTEN/NOTIFY, stale recovery |
| `paper_retriever.py` | lexical/vector retrieval + rerank + context window |
| `vector_repository.py` | pgvector upsert/search, content_role/section boost |
| `embedding_client.py` | OpenAI text-embedding-3-large, batch 처리 |
| `layout_parser_client.py` | HURIDOCS POST 호출, segment 검증 |
| `collect_papers.py` | daily collect + backfill + prepare job enqueue |
| `prepare_papers.py` | raw→parse→chunk→PostgreSQL (3개 진입점) |
| `prepare_worker.py` | auto/backfill 모드, embed 자동 연계, loop |
| `embed_papers.py` | missing chunk→embed→upsert |
| `enrich_papers_metadata.py` | arXiv 후속 보강, rate-limit soft-fail |
| `daily_collect.py` | 매일 KST 18:00 수집 DAG |
| `maintenance.py` | 3시간 주기 backfill→enrich DAG |
| `settings.py` / `langsmith.py` | 전체 환경설정, LangSmith trace |

### 프로토타입/초안 (6개) — 동작하지만 품질 미검증

| 모듈 | 현재 상태 |
|------|-----------|
| `paper_chains.py` | `analyze_paper_detail()` 동작함. 단일 논문 입력 → PaperDetailDocument 생성 |
| `prompts/overview.py` | 단일 논문 상세 overview 프롬프트 |
| `prompts/key_findings.py` | 단일 논문 핵심 포인트 프롬프트 |
| `translation_chains.py` | `translate_chunk()`, `build_detailed_summary()` 호출 가능 |
| `prompts/translation.py` | 한국어 번역 프롬프트 |
| `prompts/detailed_summary.py` | 상세 요약 프롬프트. helper chain은 연결됐지만 상위 소비 계층은 아직 미연결 |

### 스캐폴드 (1개) — NotImplementedError

| 모듈 | 현재 상태 | 구현 시 참고 |
|------|-----------|-------------|
| `rag.py` | `answer_question()` 시그니처만 존재 | 입력: question, context_papers → 출력: answer, source_papers |

### 데모 (2개)

| 모듈 | 현재 상태 |
|------|-----------|
| `app/main.py` | 최소 플레이스홀더. 메인 화면 준비 중 안내만 표시 |
| `app/paper_detail_demo.py` | 논문 상세 데모. overview/key_findings/detailed_summary/translation 검증용 |

### 미존재 (코드 자체가 없음)

| 영역 | 설명 |
|------|------|
| 논문 상세 저장/소비 경로 | `PaperDetailDocument` 생성 체인은 있으나 저장소 CRUD, 파이프라인 진입점, UI 소비 경로는 아직 없음 |

## 2. 저장 계층 상태

### PostgreSQL

| 테이블 | 상태 | 비고 |
|--------|------|------|
| `papers` | 실운영 | PK: arxiv_id |
| `paper_fulltexts` | 실운영 | text, sections, quality_metrics, artifacts, parser_metadata |
| `paper_chunks` | 실운영 | FTS GIN 인덱스, content_role 메타데이터 |
| `paper_embeddings` | 실운영 | VECTOR(1536), content_role/section boost SQL 내장 |
| `prepare_jobs` | 실운영 | mode/target_date unique, LISTEN/NOTIFY |

### MongoDB

| 컬렉션 | 상태 |
|--------|------|
| `daily_papers_raw` | 실운영. (source, date) unique |
| `pipeline_state` | 실운영. backfill cursor, 수집 상태 |

## 3. Retrieval 현재 상태

### 사용 가능한 검색 경로

| 경로 | cross-paper | 메서드 |
|------|-------------|--------|
| lexical (FTS) | O | `paper_retriever.search_paper_contexts()` |
| vector | O | `paper_retriever.search_paper_contexts_by_vector()` |
| hybrid | O | `paper_retriever.search_paper_contexts_by_hybrid()` |

lexical은 4층 스코어링(FTS + ILIKE + content_role + section_boost)을 포함한다.
vector는 cosine similarity + content_role/section 조정 + Python rerank(lexical overlap, query intent)를 포함한다.
hybrid는 lexical/vector 후보를 reciprocal rank fusion으로 결합하고, 동일 chunk 중복을 제거한다.
세 경로 모두 adjacency_window로 주변 chunk를 묶어 context_text를 구성한다.

### 아직 없는 것

- **query rewrite**: 원문 그대로 검색
- **검색 실패 fallback**: 결과 부족 시 대응 정책 없음

## 4. 빈칸 간 의존 관계

### 경로 A: retrieval → RAG answer → UI

```
[완료] lexical/vector/hybrid retrieval (cross-paper 지원)
  → [스캐폴드] rag.py answer_question()
  → [플레이스홀더] app/main.py 검색 UI
```

현재는 lexical, vector, hybrid 중 하나를 골라 RAG answer 구현을 시작할 수 있다.

### 경로 B: paper detail → UI 상세

```
[완료] paper_fulltexts / paper_chunks / retrieval 기반 입력 데이터
  → [프로토타입] paper_chains.py (overview / key_findings)
  → [프로토타입] translation_chains.py (detailed_summary / translation)
  → [미존재] paper detail 저장/소비 경로
  → [데모] app/paper_detail_demo.py
```

`paper_chains.py`의 `analyze_paper_detail()`은 단일 논문 입력을 받으면 `PaperDetailDocument`를 생성할 수 있다. `translation_chains.py`의 `build_detailed_summary()`와 `translate_chunk()`도 독립 호출 가능하다. 현재 빠진 건 "어디서 호출할지"와 "결과를 어디에 보여줄지"다.

### 경로 C: 한국어 번역·요약 (보조 계층)

역할 3의 프롬프트와 helper chain은 독립적으로 호출 가능하다. 다만 현재는 역할 2의 answer chain이나 paper detail 소비 계층에 아직 직접 연결되지 않았다.

## 5. 운영 흐름 요약

### 서버 자동화 (Airflow 2개 DAG)

- `arxplore_daily_collect`: 매일 KST 18:00, HF Daily Papers → MongoDB + prepare_jobs enqueue
- `arxplore_maintenance`: 3시간마다, backfill → enrich

### 로컬 워커 (수동 기동)

```bash
bash scripts/prepare-worker.sh       # auto 모드 loop
bash scripts/prepare-worker.sh once   # 1회 실행
```

auto 모드는 prepare_jobs 큐를 소비해 prepare → embed를 수행한다.

### 점검 도구

- `notebooks/retrieval_inspection.ipynb`: 적재 스냅샷, prepare queue 상태, 단일 논문 품질, lexical/vector retrieval 비교
