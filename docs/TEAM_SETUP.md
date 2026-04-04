# ArXplore 개발 환경 설정 가이드

## 1. 문서 목적

이 문서는 ArXplore 프로젝트 구성원이 로컬 개발 환경과 서버 연결 환경을 준비할 때 따라야 하는 절차를 정리한다. 현재 운영 구조는 `서버 DB + 서버 Airflow + 로컬 dev 컨테이너 + 로컬 parser + 로컬 prepare-worker`를 기준으로 한다. 즉, 서버는 수집 자동화와 저장소를 담당하고, 무거운 파싱과 임베딩은 팀원 각자의 개발용 PC에서 수행한다.

## 2. 전체 흐름

```text
1. WSL 또는 로컬 개발 환경 준비
2. Tailscale 연결
3. 저장소 clone
4. .env 배치
5. dev 컨테이너 실행
6. parser 컨테이너 실행
7. prepare-worker 실행
8. 필요 시 서버 Airflow와 DB 접근을 위한 포트 포워딩
```

## 3. 준비 사항

- Git
- Docker Desktop 또는 Docker Engine
- 전달받은 `.env`
- 전달받은 Tailscale Auth Key

설치 확인:

```bash
docker --version
docker compose version
```

## 4. Tailscale 설치

개발 컨테이너에서 서버의 MongoDB, PostgreSQL, Airflow에 접근하려면 Tailscale 연결이 필요하다.

### WSL 사용자

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up --auth-key=<전달받은 Auth Key>
tailscale status
```

### macOS 사용자

```bash
brew install --cask tailscale
sudo tailscale up --auth-key=<전달받은 Auth Key>
```

### 연결 확인

```bash
tailscale ping 100.106.29.101
```

`pong`이 오면 서버 연결이 정상이다.

## 5. 저장소 가져오기

```bash
git clone -b dev <repository-url>
cd ArXplore
```

## 6. `.env` 배치

전달받은 `.env`를 프로젝트 루트에 둔다. 현재 `.env`에는 MongoDB, PostgreSQL, LangSmith, parser, worker가 사용할 접속 정보가 포함된다.

환경 변수 변경을 반영해야 할 때는 컨테이너를 재생성하는 편이 안전하다.

```bash
docker compose -p arxplore_dev -f docker-compose.dev.yml up -d --force-recreate dev
```

현재 구조에서 중요한 값은 다음과 같다.

- `MONGO_DB=arxplore_source`
- `POSTGRES_DB=arxplore_meta`
- `APP_POSTGRES_DB=arxplore_app`
- `SERVER_MONGO_PORT`
- `SERVER_POSTGRES_PORT`
- `LAYOUT_PARSER_BASE_URL`

접속 값은 아래 규칙을 유지한다.

- `MONGO_HOST`, `POSTGRES_HOST`에는 호스트만 넣는다
- 포트는 `SERVER_MONGO_PORT`, `SERVER_POSTGRES_PORT`에서 따로 관리한다

개인별로 바꿔야 하는 값은 최소한 아래다.

| 항목 | 설명 |
|------|------|
| `LANGSMITH_TRACE_USER` | 개인 trace 식별자 |

## 7. dev 컨테이너 실행

```bash
bash scripts/setup-dev.sh
docker compose -p arxplore_dev -f docker-compose.dev.yml ps
```

기본 컨테이너:

- `arxplore-dev`

기본 접속:

- Jupyter: `http://127.0.0.1:18888`
- Streamlit: `http://127.0.0.1:18501`

dev 컨테이너 접속:

```bash
docker compose -p arxplore_dev -f docker-compose.dev.yml exec dev bash
```

이 환경에서 할 수 있는 작업:

- Python 스크립트 실행
- notebook 실험
- retrieval / prompt / chain 검증
- Streamlit 실행
- 간단한 DB 점검

### Streamlit 실행

```bash
streamlit run app/main.py --server.address=0.0.0.0
```

## 8. 로컬 parser 컨테이너 실행

PDF 파싱 품질 검증과 실제 prepare는 HURIDOCS 기반 parser 컨테이너를 함께 쓰는 것을 기준으로 한다.

```bash
docker compose -f docker-compose.parser.yml up -d --build
docker logs -f arxplore-layout-parser
```

parser 컨테이너 원칙:

- 공용 서버 스택에 올리지 않는다
- 로컬 개발용 PC에서 실행한다
- 가능하면 GPU를 사용하고, 없으면 CPU fallback을 허용한다
- parser가 없어도 `pypdf` fallback은 동작하지만 품질 기준은 parser 실행 상태를 기본으로 본다

## 9. prepare-worker 실행

현재 공식 prepare 진입점은 `scripts/prepare-worker.sh`다. 이 스크립트는 WSL 또는 로컬 쉘에서 실행하지만, 실제 Python worker는 `arxplore-dev` 컨테이너 안에서 동작한다.

상시 대기 모드:

```bash
bash scripts/prepare-worker.sh
```

1회 실행 모드:

```bash
bash scripts/prepare-worker.sh once
```

동작 방식:

- `arxplore_daily_collect`가 `prepare_jobs`에 날짜를 넣는다
- `prepare-worker`가 새 job을 기다린다
- job을 claim하면 `prepare -> embed`를 수행한다
- 결과는 서버 PostgreSQL에 직접 적재된다

`prepare-worker`는 auto 모드에서 `LISTEN/NOTIFY`로 대기하며, 새 작업이 없을 때는 polling보다 가벼운 형태로 쉬고 있다가 job이 생기면 거의 즉시 반응한다.

### backfill prepare가 필요할 때

과거 raw를 다시 파싱해 적재할 때만 backfill 모드를 수동으로 사용한다.

```bash
docker compose -p arxplore_dev -f docker-compose.dev.yml exec dev bash -lc \
  'cd /workspace && python3 -m src.pipeline.prepare_worker --mode backfill --batch-days 3 --loop --sleep-seconds 120'
```

## 10. 서버 스택 실행

서버 스택은 수집 자동화와 DB 운영을 담당한다.

```bash
bash scripts/setup-server.sh
docker compose -p arxplore_server -f docker-compose.server.yml ps
```

핵심 컨테이너:

- `arxplore-postgres`
- `arxplore-mongodb`
- `arxplore-airflow-init`
- `arxplore-airflow-web`
- `arxplore-airflow-scheduler`
- `arxplore-airflow-dag-processor`

현재 Airflow에서 중요하게 보는 DAG는 2개다.

- `arxplore_daily_collect`
- `arxplore_maintenance`

## 11. Airflow 운영 기준

현재 운영 모델은 다음과 같다.

- `arxplore_daily_collect`
  - 최신 HF Daily Papers raw 수집
  - `prepare_jobs` enqueue
- `arxplore_maintenance`
  - backfill
  - metadata enrichment
- 로컬 `prepare-worker`
  - prepare
  - embed

즉 서버 Airflow만 켜 둔다고 prepare와 embed가 자동으로 실행되는 구조가 아니다. 로컬 worker도 함께 떠 있어야 최신 수집분이 실제 `paper_fulltexts`, `paper_chunks`, `paper_embeddings`까지 이어진다.

## 12. 적재 상태 점검

적재 상태와 retrieval 결과는 아래 notebook으로 확인한다.

- `notebooks/retrieval_inspection.ipynb`

이 notebook에서는 다음을 점검할 수 있다.

- 적재된 `papers`, `paper_fulltexts`, `paper_chunks`, `paper_embeddings` 수
- `prepare_jobs` 최근 상태
- 최근 적재 논문 목록
- lexical / vector retrieval 결과

운영상 가장 먼저 확인할 것은 아래 네 가지다.

1. raw가 MongoDB에 들어가는지
2. `prepare_jobs`가 생성되는지
3. `prepare-worker`가 이를 소비하는지
4. embedding backlog가 남아 있지 않은지

## 13. Windows 브라우저에서 서버 접근

WSL에만 Tailscale이 설치되어 있으면 Windows 브라우저에서 Airflow와 DB를 직접 보기 어렵다. 이 경우 `scripts/port-forward.sh`로 포트 포워딩을 사용한다.

사전 준비:

```bash
sudo apt install openssh-server -y
sudo service ssh start
```

그 다음 실행:

```bash
bash scripts/port-forward.sh
```

제어 명령:

```bash
bash scripts/port-forward.sh status
bash scripts/port-forward.sh stop
bash scripts/port-forward.sh restart
```

포워딩 주소:

| 서비스 | Windows 브라우저 주소 |
|--------|----------------------|
| Airflow | `http://127.0.0.1:18080` |
| PostgreSQL | `127.0.0.1:15432` |
| MongoDB | `127.0.0.1:17017` |

## 14. 접속 정보 요약

### dev 컨테이너 / 코드 기준

| 서비스 | 주소 |
|--------|------|
| PostgreSQL | `100.106.29.101:15432` |
| MongoDB | `100.106.29.101:17017` |
| Airflow API | `http://100.106.29.101:18080` |
| Layout Parser | `http://172.17.0.1:5060` 또는 로컬 parser 주소 |

### Windows 브라우저 / DB 클라이언트 기준

| 서비스 | 주소 |
|--------|------|
| Airflow | `http://127.0.0.1:18080` |
| PostgreSQL | `127.0.0.1:15432` |
| MongoDB | `127.0.0.1:17017` |

## 15. LangSmith 설정

LangSmith는 별도 컨테이너 없이 Python 실행 환경에서 사용한다. 공용 프로젝트 이름은 유지하고, 각자 `LANGSMITH_TRACE_USER`만 개인 식별자로 맞춘다.

```env
LANGSMITH_TRACE_USER=홍길동
```
