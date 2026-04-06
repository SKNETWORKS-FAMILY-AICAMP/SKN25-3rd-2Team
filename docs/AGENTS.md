# ArXplore AI 작업 규칙

이 문서는 ArXplore 저장소에서 AI 도구가 작업할 때 따라야 하는 공통 규칙이다. 현재 저장소는 이미 수집, 파싱, 적재, 임베딩 기반을 갖춘 상태이며, AI는 이 기반을 임의로 다시 설계하는 것이 아니라 그 위에서 retrieval, answer chain, prompt, 논문 상세 문서, UI 계층을 다듬는 방식으로 작업해야 한다.

## 1. 먼저 읽을 문서

작업을 시작하기 전에 아래 문서를 먼저 읽는다.

1. `docs/PLAN.md`
2. `docs/ARCHITECTURE.md`
3. `docs/ROLES.md`
4. `docs/WORKFLOW.md`

환경 준비와 실행 절차가 필요할 때는 `docs/TEAM_SETUP.md`도 함께 읽는다.

문서와 코드가 충돌할 경우 코드를 즉시 바꾸지 않는다. 현재 운영 사실이 무엇인지 먼저 설명하고, 문서 정합화가 필요한지 또는 코드 수정이 필요한지 구분한 뒤 진행한다.

## 2. 현재 운영 구조를 먼저 이해할 것

AI는 아래 운영 사실을 현재 기준선으로 사용한다.

- 서버 자동화 DAG는 2개다
  - `arxplore_daily_collect`
  - `arxplore_maintenance`
- 최신 수집분은 `daily_collect`가 수행한다
- 과거 raw 백필과 arXiv 메타데이터 후속 보강은 `maintenance`가 수행한다
- `prepare`와 `embed`는 서버 Airflow가 아니라 로컬 runtime에서 수행한다
- 로컬 실행 진입점은 `scripts/prepare-worker.sh`와 `src/pipeline/prepare_worker.py`다
- prepare queue는 Mongo polling이 아니라 PostgreSQL `prepare_jobs` 테이블과 `prepare_job_repository.py`를 사용한다
- parser runtime은 로컬 `docker-compose.parser.yml` 기반 HURIDOCS 컨테이너다
- PDF 파싱 경로는 `layout -> pypdf -> abstract fallback` 순서다

## 3. 절대 임의 변경하면 안 되는 것

### `PaperDetailDocument` 계약

`src/core/models.py`의 `PaperRef`, `PaperDetailDocument`는 팀 공용 데이터 계약이다. 이 모델은 생성 체인의 출력이자 UI 입력이다. 한 계층의 편의를 위해 필드를 바꾸면 다른 계층이 동시에 깨진다.

다음 변경은 팀 합의 없이 하지 않는다.

- 필드 이름 변경
- 필드 삭제
- 필드 타입 변경
- 의미가 겹치는 새 필드 추가
- `overview`와 `key_findings` 역할 혼합

### retrieval 결과 shape

retrieval 구현은 바꿀 수 있지만, 결과 shape는 쉽게 바꾸지 않는다. 역할 2와 역할 5가 이 구조를 소비하므로, `chunk_id`, `arxiv_id`, `chunk_text`, `section_title`, `content_role`, `score` 같은 핵심 필드는 안정적으로 유지해야 한다.

### answer payload shape

RAG 응답 계층이 UI에 넘기는 answer payload 역시 공용 계약이다. 답변 텍스트, citation 목록, 근거 chunk, 상태 필드를 역할 2 내부 구현 편의만으로 바꾸지 않는다.

계약 변경이 필요하면 아래 순서를 따른다.

1. 왜 변경이 필요한지 설명한다
2. 영향을 받는 계층을 정리한다
3. 관련 문서와 코드 수정 범위를 함께 제안한다

## 4. 저장소 구조 규칙

각 계층의 책임은 다음과 같다.

- `dags/`: Airflow DAG 정의만 둔다
- `src/pipeline/`: DAG와 워커가 호출하는 실행 진입점
- `src/integrations/`: 외부 서비스 연동, 저장소 접근, retrieval 구현
- `src/core/`: 도메인 모델, 프롬프트, 생성 체인, RAG 응답
- `src/shared/`: 설정과 tracing
- `app/`: Streamlit UI

아래 변경은 구조 원칙에 어긋난다.

- DAG 파일에 무거운 비즈니스 로직을 직접 넣는 것
- 외부 연동 코드를 `src/core/`나 `app/`에 넣는 것
- UI 편의를 위해 도메인 계약을 바꾸는 것
- 저장 편의를 위해 공용 모델을 바꾸는 것

## 5. 용어 규칙

AI는 아래 표준 표현을 사용한다.

| 표준 표현 | 설명 |
|---|---|
| `논문 상세 문서` | `PaperDetailDocument` 단위 구조화 문서 |
| `논문 개요` | 단일 논문의 목적, 접근, 결과를 설명하는 overview |
| `핵심 포인트` | 단일 논문의 기여와 결과를 정리한 key findings |
| `상세 요약` | 논문 본문을 한국어로 구조화한 detailed summary |
| `근거 번역` | 근거 chunk의 한국어 번역 |
| `논문 청크` | retrieval과 grounding 입력 단위 |
| `lexical retrieval` | 텍스트 기반 검색 |
| `vector retrieval` | 임베딩 기반 검색 |
| `hybrid retrieval` | lexical과 vector를 결합한 검색 |
| `RAG 응답` | retrieval 결과를 기반으로 만든 답변 |
| `prepare job` | 날짜 단위 prepare 작업 |

문맥에 맞는다는 이유로 다른 용어를 섞어 쓰지 않는다.

## 6. 작업 방식 규칙

- 현재 구조를 다시 초기화하거나 대체하기보다, 이미 존재하는 경로 위에서 문제를 푼다
- 문서 기준과 충돌하는 구조 변경은 코드 수정 전에 먼저 설명한다
- 문서에도 영향을 주는 변경이면 관련 문서를 함께 갱신한다
- 테스트나 검증 경로가 있으면 실행한다
- retrieval, answer, prompt, 논문 상세, UI 경계를 침범하는 변경은 더 보수적으로 다룬다

## 7. 현재 단계에서 AI가 우선해야 할 것

현재 단계에서 AI가 우선적으로 다뤄야 할 순서는 다음과 같다.

1. retrieval 품질과 반환 shape
2. answer chain과 citation 정책
3. 한국어 번역과 상세 요약 규칙
4. 논문 상세 문서 생성 품질
5. UI 소비 계층 연결

AI는 "파이프라인 뼈대를 새로 만드는 작업"을 기본값으로 두지 않는다. 이미 구현된 기반을 이해한 뒤, 그 위에 있는 계층을 개선하는 것이 현재 기준이다.

## 8. 금지 예시

아래와 같은 요청은 바로 반영하지 않는다.

- `"검색 결과 shape를 UI에 맞게 바꿔줘"`
- `"PaperDetailDocument 필드를 조금 단순화해줘"`
- `"prepare는 서버 Airflow에서 돌리게 다시 바꿔줘"`
- `"DAG를 예전처럼 여러 개로 다시 쪼개자"`

이런 요청은 계약, 운영 모델, 역할 경계 전체에 영향을 줄 수 있다. 먼저 이유와 영향 범위를 설명한 뒤 진행한다.
