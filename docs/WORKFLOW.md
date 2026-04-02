# ArXplore 개발 및 운영 워크플로우

## 1. 문서 목적

이 문서는 ArXplore를 5인 팀이 병렬로 구현하고 통합할 때 따를 작업 흐름을 정리한 운영 기준 문서이다. 환경 설정 자체는 [TEAM_SETUP.md](./TEAM_SETUP.md)를 기준으로 하고, 본 문서는 "어떤 순서로 구현하고, 어떤 시점에 통합하며, 어떤 기준으로 완료를 판단할 것인가"를 설명한다.

이번 워크플로우의 핵심은 **1번 역할의 선행 완료 범위를 명확히 하고, 이후 2~5번 역할이 동시에 움직일 수 있게 만드는 것**이다.

## 2. 기본 원칙

프로젝트는 현재 초안 스캐폴드까지 준비되어 있으므로, 이후 작업은 "큰 구조를 계속 바꾸는 것"보다 "정해진 계층에 실제 기능을 채워 넣는 것"에 집중해야 한다. 각 팀원은 자신의 담당 영역에서 독립적으로 개발하되, 다음 원칙을 지켜야 한다.

- 제품 기준 문서는 항상 [PLAN.md](./PLAN.md)를 우선한다.
- 구조와 계층 설명은 [ARCHITECTURE.md](./ARCHITECTURE.md)를 기준으로 맞춘다.
- 역할 경계는 [ROLES.md](./ROLES.md)를 기준으로 유지한다.
- 공통 용어는 `TopicDocument`, `paper_fulltext`, `paper_chunks`, `minimum retrieval`, `vector retrieval`를 사용한다.
- DAG 파일은 가볍게 유지하고, 실제 로직은 `src/pipeline` 이하에 둔다.
- `TopicDocument`는 공용 계약이므로 팀 합의 없이 필드 구조를 바꾸지 않는다.
- 표, 그림, 캡션, 수식 구조화보다 텍스트 기반 탐색 경험을 우선한다.
- 1번이 제공하는 최소 retrieval과 2번이 제공하는 vector retrieval은 가능하면 같은 응답 shape를 유지한다.

## 3. 작업 시작 전 공통 확인

작업 시작 전에는 아래 항목을 먼저 확인한다.

- `.env` 파일이 최신 버전인지
- Docker가 실행 중인지
- 본인이 사용하는 작업 모드가 무엇인지
- 필요한 컨테이너가 올라와 있는지
- 자신의 작업이 어느 계층에 속하는지
- 1번 역할의 선행 완료 범위가 어디까지 진행됐는지

상태 확인 명령은 다음과 같다.

```bash
docker compose -p arxplore_dev ps
docker compose -p arxplore_server -f docker-compose.server.yml ps
```

## 4. 작업 모드

### 개발자 기본 모드

대부분의 개발자는 `dev` 컨테이너만 사용하면 된다.

```bash
bash scripts/setup-dev.sh
docker compose -p arxplore_dev exec dev bash
```

이 모드에서는 다음 작업을 수행한다.

- Python 코드 작성
- Jupyter 실험
- 프롬프트 테스트
- Streamlit UI 확인
- retrieval 결과 shape 검증

### 서버 통합 모드

인프라, Airflow, DB, 통합 테스트 담당자는 서버 스택을 함께 사용한다.

```bash
bash scripts/setup-server.sh
```

현재 서버 스택의 핵심 컨테이너는 다음과 같다.

- `arxplore-postgres`
- `arxplore-mongodb`
- `arxplore-airflow-init`
- `arxplore-airflow-web`
- `arxplore-airflow-scheduler`
- `arxplore-airflow-dag-processor`

여기서 `arxplore-airflow-init`은 1회성 초기화 컨테이너이므로 `Exited` 상태가 정상이다.

현재 운영 기준은 `collect`와 `prepare`를 분리해서 본다.

- `arxplore_collect_papers`: 매일 `16:10 UTC`에 자동 실행되어 HF Daily Papers 원본을 MongoDB에 저장한다.
- `arxplore_prepare_papers`: 파싱 품질이 아직 조정 중이므로 `schedule=None`으로 유지하고, 수동 실행이나 날짜 범위 배치 실행으로만 사용한다.

즉, 원본 수집은 자동화하고, PostgreSQL 본문/청크 적재는 품질이 충분히 안정될 때까지 통제된 방식으로 돌리는 것이 현재 기준이다.

## 5. 구현 순서

프로젝트는 아래 순서로 진행할 때 충돌이 가장 적다.

### 1단계: 공통 기준 고정

먼저 다음 항목을 고정한다.

- `TopicDocument` 계약
- retrieval 결과 반환 구조
- 환경 변수 이름
- DAG 이름과 단계 이름
- 저장할 핵심 테이블 목록
- 역할 분담

이 단계에서 구조가 흔들리면 이후 병렬 개발의 이점이 크게 줄어든다.

### 2단계: 1번 선행 완료

1번 역할은 아래 범위를 먼저 끝낸다.

1. HF Daily Papers 수집
2. MongoDB 원본 저장
3. arXiv 메타데이터 보강
4. PDF 본문 텍스트 파싱
5. PostgreSQL 적재
6. 최종 청크 생성
7. 최소 retrieval 제공

이 단계가 완료되면 나머지 역할은 같은 데이터 기준 위에서 동시에 움직일 수 있다.

### 3단계: 2~5 병렬 구현

1번 선행 범위가 완료되면 다음 병렬 구조로 이동한다.

- 2번: 임베딩, vector retrieval, 토픽 그룹핑
- 3번: `TopicDocument` 생성 체인
- 4번: 최소 retrieval 기반 RAG 응답
- 5번: 카드, 상세 문서, 검색 응답 UI

핵심은 4번이 2번 완료를 기다리지 않도록, 1번이 최소 retrieval을 먼저 제공하는 것이다.

### 4단계: 고도화 및 교체

병렬 구현이 어느 정도 진행되면 아래 순서로 연결한다.

1. 2번이 vector retrieval을 완성한다.
2. 4번은 최소 retrieval에서 vector retrieval로 검색 경로를 교체한다.
3. 3번은 토픽 그룹핑 결과와 문서 생성 품질을 맞춘다.
4. 5번은 검색 결과, 카드, 상세 문서를 실데이터로 고정한다.

이 단계의 핵심은 구현을 새로 만드는 것이 아니라, 초기 최소 기능을 최종 품질 구조로 바꾸는 것이다.

## 6. 역할별 일상 작업 흐름

### 1번: 인프라 · 데이터 파이프라인 · 적재 담당

1번 역할은 다른 역할이 붙을 수 있는 입력 데이터를 준비하는 책임을 가진다. 따라서 다음 순서를 반복적으로 수행한다.

1. Compose와 Docker 이미지를 확인한다.
2. Airflow DAG 등록 상태를 확인한다.
3. HF Daily Papers 수집 결과를 저장한다.
4. arXiv 보강 결과를 검증한다.
5. PDF 본문 텍스트 파싱 결과를 검증한다.
6. PostgreSQL에 적재된 논문, 본문, 청크를 확인한다.
7. 최소 retrieval 응답 shape를 고정한다.

### 2번: 임베딩 · 벡터 검색 · 토픽 그룹핑 담당

2번 역할은 1번이 준비한 청크를 기준으로 검색 품질을 끌어올리는 일을 한다.

1. 저장된 청크를 읽는다.
2. 임베딩을 생성하고 저장한다.
3. vector retrieval을 구현한다.
4. 최소 retrieval과 같은 반환 구조를 유지하는지 확인한다.
5. 토픽 그룹핑 결과를 생성한다.

### 3번: 토픽 문서 생성 담당

3번 역할은 적재된 논문과 텍스트를 바탕으로 `TopicDocument` 품질을 높인다.

1. 샘플 논문 묶음을 준비한다.
2. overview와 key_findings 프롬프트를 조정한다.
3. `analyze_topic()` 출력을 안정화한다.
4. LangSmith trace로 결과를 비교한다.

### 4번: RAG 응답 담당

4번 역할은 먼저 최소 retrieval 위에서 응답 흐름을 만든다.

1. 질문 입력과 검색 결과 연결 구조를 정리한다.
2. 최소 retrieval 기준으로 응답 흐름을 구현한다.
3. 근거 논문과 관련 토픽 노출 구조를 맞춘다.
4. 이후 vector retrieval로 교체해도 응답 계층이 흔들리지 않는지 확인한다.

### 5번: UI 담당

5번 역할은 "현재 저장소가 어떤 제품 경험으로 보이는가"를 책임진다.

1. 검색 영역, 카드 영역, 상세 문서 영역 흐름을 먼저 고정한다.
2. `TopicDocument`와 검색 응답 렌더링 경로를 분리해 정리한다.
3. 데모 데이터와 실데이터가 같은 컴포넌트 구조를 타도록 맞춘다.
4. 빈 상태와 오류 상태를 보완한다.

## 7. LangSmith 운영 방식

LangSmith는 개인 API 키를 사용하되, 공용 프로젝트 기준으로 trace를 축적한다. 이렇게 하면 각자 로컬에서 실험하더라도 동일 프로젝트 안에서 결과를 비교할 수 있다.

trace 구분 기준은 다음과 같다.

- `collect_papers`: HF Daily Papers 수집
- `prepare_papers`: arXiv 메타데이터 보강, PDF 파싱, 적재
- `embed_papers`: 임베딩 및 토픽 그룹핑
- `analyze_topics`: 토픽 문서 생성
- `rag_answer`: 검색 결과 기반 응답

문서 생성 품질 검토는 `stage=analyze_topics`, 응답 품질 검토는 `stage=rag_answer`를 중심으로 수행한다.

## 8. 통합 확인 순서

기능을 붙일 때는 아래 순서로 점검한다.

1. MongoDB에 원본 수집 결과가 저장되는지 확인한다.
2. PostgreSQL에 정제 논문과 본문 텍스트가 저장되는지 확인한다.
3. PostgreSQL에 최종 청크가 저장되는지 확인한다.
4. 최소 retrieval이 동작하는지 확인한다.
5. `TopicDocument`가 생성되는지 확인한다.
6. vector retrieval이 최소 retrieval과 같은 결과 shape를 반환하는지 확인한다.
7. 검색 응답이 근거 논문과 함께 노출되는지 확인한다.
8. Streamlit에서 검색 영역, 카드 영역, 상세 문서가 정상 렌더링되는지 확인한다.
9. Airflow에서 각 단계가 실제로 실행 가능한지 확인한다.
10. LangSmith trace가 남는지 확인한다.

### 적재 상태 노트북 점검

HF Daily Papers 수집과 PostgreSQL 적재 결과는 로컬 `notebooks/inspect_ingestion.ipynb`를 열어 확인한다.

이 노트북에서는 다음을 바로 점검할 수 있다.

- 최근 적재된 `papers` 목록
- `paper_fulltexts`의 본문 길이, section 개수, `quality_metrics`
- `paper_chunks` 개수와 chunk 미리보기
- 특정 `arxiv_id` 기준 상세 점검
- minimum retrieval 결과 확인

### Airflow 수동 실행 기준

Airflow UI에서 `Trigger DAG`를 사용할 때는 `dag_run.conf`로 파라미터를 넘긴다.

`arxplore_collect_papers`

```json
{"target_date": "2026-04-01"}
```

`arxplore_prepare_papers`

```json
{"target_date": "2026-04-01", "max_papers": 2}
```

`target_date`를 비우면 오늘 날짜를 사용하고, `max_papers`를 비우면 해당 날짜 raw payload 전체를 대상으로 prepare를 수행한다.

### 한 달치 임시 적재 권장 순서

현재는 파싱 규칙을 더 일반화하기 위해, 먼저 최근 약 한 달치 raw payload를 MongoDB에 누적한 뒤 PostgreSQL 적재 품질을 다시 평가하는 흐름을 권장한다.

1. `arxplore_collect_papers` 자동 실행으로 raw payload를 계속 누적한다.
2. 필요한 날짜 범위를 선택해 `arxplore_prepare_papers`를 수동 실행한다.
3. `notebooks/inspect_ingestion.ipynb`의 `quality_issues`와 chunk 출력 셀로 watchlist를 확인한다.
4. 반복되는 오탐 패턴만 다시 파서 규칙으로 보정한다.

## 9. 자주 쓰는 명령

```bash
bash scripts/setup-dev.sh
bash scripts/setup-server.sh
docker compose -p arxplore_dev exec dev bash
docker compose -p arxplore_dev ps
docker compose -p arxplore_server -f docker-compose.server.yml ps
streamlit run app/main.py --server.address=0.0.0.0
docker exec arxplore-airflow-web airflow dags list
python3 -c "from src.core import TopicDocument, PaperRef, RelatedTopic"
jupyter lab --ip=0.0.0.0 --port=18888 --no-browser --allow-root
```

## 10. 문제 발생 시 대응 순서

### 컨테이너가 뜨지 않는 경우

1. Docker 실행 여부를 확인한다.
2. `.env` 존재 여부를 확인한다.
3. `docker compose ... ps`로 상태를 확인한다.
4. 필요한 경우 `setup-dev.sh` 또는 `setup-server.sh`를 다시 실행한다.

### Airflow에서 DAG가 보이지 않는 경우

1. `arxplore-airflow-dag-processor`가 실행 중인지 확인한다.
2. `arxplore-airflow-web`과 `arxplore-airflow-scheduler` 상태를 확인한다.
3. `docker exec arxplore-airflow-web airflow dags list`로 등록 상태를 확인한다.
4. DAG 파일이 `src/pipeline`을 올바르게 호출하는지 확인한다.

### 문서 생성 결과가 이상한 경우

1. LangSmith trace를 확인한다.
2. 입력 논문 묶음이 정상인지 확인한다.
3. 프롬프트 변경 이력을 확인한다.
4. `TopicDocument` 계약이 깨지지 않았는지 확인한다.

### 검색 응답이 이상한 경우

1. 현재 최소 retrieval인지 vector retrieval인지 확인한다.
2. retrieval 반환 shape가 계약과 일치하는지 확인한다.
3. 검색 결과 부족인지, 응답 프롬프트 문제인지 분리한다.
4. 근거 논문이 함께 반환되는지 확인한다.

### UI에 데이터가 안 보이는 경우

1. 현재 UI가 데모 데이터 모드인지 실데이터 모드인지 확인한다.
2. 검색 영역 문제인지 카드 조회 문제인지 상세 렌더링 문제인지 먼저 분리한다.
3. retrieval 또는 문서 조회 함수가 값을 반환하는지 확인한다.
4. 렌더링 계층에서 빈 상태 처리 로직을 확인한다.

## 11. 작업 마무리 기준

작업을 마무리하기 전에는 아래 항목을 확인한다.

- 변경한 코드가 어느 계층에 속하는지 명확한가
- 다른 담당자에게 넘길 입력/출력 계약이 정리되어 있는가
- 문서와 구현이 어긋나지 않는가
- `.env`와 개인 실험 파일을 커밋하지 않았는가
- 필요 시 README, PLAN, ARCHITECTURE, ROLES, WORKFLOW, TEAM_SETUP, AGENTS 중 관련 문서를 같이 갱신했는가

현재 단계의 핵심은 "각자 맡은 기능을 빨리 만드는 것"만이 아니라, "1번 선행 완료 이후 나머지 역할이 멈추지 않고 병렬로 움직일 수 있는 구조를 유지하는 것"이다. 따라서 빠른 구현과 함께 계약 유지, 문서 반영, 실행 경로 확인을 동일한 비중으로 관리해야 한다.
