# ArXplore 개발 환경 설정 가이드

## 1. 문서 목적

이 문서는 ArXplore 프로젝트 구성원이 개발 환경을 처음 준비할 때 따라야 하는 절차를 정리한 문서이다.

서버 스택(MongoDB, PostgreSQL, Airflow)은 팀 공용 서버에서 운영되고 있으며, 각 팀원은 자신의 컴퓨터에서 `dev` 컨테이너를 기본으로 사용한다. PDF 파싱 품질 검증과 `prepare_papers` 로컬 실행이 필요할 때는 여기에 parser 컨테이너를 추가로 띄운다. 서버 접속은 Tailscale VPN을 통해 이루어진다.

## 2. 전체 흐름

```text
1. WSL 환경 준비 (Windows 사용자)
2. Tailscale 설치
3. 저장소 clone
4. .env 설정
5. dev 컨테이너 실행
6. (선택) Windows 브라우저에서 Airflow/DB 접근 시 포트 포워딩
7. (선택) 로컬 parser 컨테이너 실행
```

## 3. 준비 사항

- Git
- Docker Desktop 또는 Docker Engine
- 전달받은 `.env` 파일
- 전달받은 Tailscale Auth Key

### Docker가 설치되어 있지 않은 경우

- Windows: Docker Desktop 설치 절차를 따른다.
- macOS: Docker Desktop 또는 `brew install --cask docker`
- Linux: 배포판에 맞는 Docker Engine 설치 절차를 따른다.

설치 후 확인:

```bash
docker --version
docker compose version
```

## 4. Tailscale 설치

개발 컨테이너에서 서버의 DB/Airflow에 접속하려면 Tailscale이 필요하다.

### WSL 사용자

WSL 내부에 설치한다.

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

`pong` 응답이 오면 서버 연결이 정상이다.

## 5. 저장소 가져오기

```bash
git clone -b dev <repository-url>
cd ArXplore
```

## 6. `.env` 배치

전달받은 `.env` 파일을 프로젝트 루트에 둔다. 서버 접속 정보, DB 계정 등은 이미 설정되어 있다.

주요 값은 다음과 같다.

- `COMPOSE_PROJECT_NAME=arxplore`
- `LANGSMITH_PROJECT=ArXplore`
- `MONGO_DB=arxplore_source`
- `POSTGRES_DB=arxplore_meta`
- `APP_POSTGRES_DB=arxplore_app`

접속 관련 값은 다음 규칙으로 유지한다.

- `MONGO_HOST`, `POSTGRES_HOST`에는 호스트만 넣는다.
- 포트는 `SERVER_MONGO_PORT`, `SERVER_POSTGRES_PORT`에서 따로 관리한다.
- 즉 `MONGO_HOST=100.106.29.101`, `SERVER_MONGO_PORT=17017`처럼 분리한다.

팀원 각자 수정해야 하는 항목:

| 항목 | 설명 |
|------|------|
| `LANGSMITH_TRACE_USER` | 본인 이름 또는 식별자 |

## 7. dev 컨테이너 실행

```bash
bash scripts/setup-dev.sh
```

정상 실행 후 확인:

```bash
docker compose -p arxplore_dev ps
```

- 컨테이너 이름: `arxplore-dev`
- Jupyter: `http://127.0.0.1:18888`
- Streamlit 포트: `18501`

### dev 컨테이너 접속

```bash
docker compose -p arxplore_dev exec dev bash
```

컨테이너 안에서 할 수 있는 작업:

- Python 스크립트 실행
- Jupyter 실험
- 프롬프트 검증
- Streamlit 실행
- 테스트 및 임시 검증

### Streamlit 실행

dev 컨테이너 안에서:

```bash
streamlit run app/main.py --server.address=0.0.0.0
```

브라우저: `http://127.0.0.1:18501`

## 8. 로컬 parser 컨테이너 실행

PDF 파싱 품질 검증과 `prepare_papers` 로컬 실행은 HURIDOCS 기반 parser 컨테이너를 함께 사용하는 것을 기준으로 한다.

```bash
docker compose -f docker-compose.parser.yml up -d --build
docker logs -f arxplore-layout-parser
```

정상 실행 후 parser는 `5060` 포트에서 응답한다. 개발 컨테이너 안에서 사용할 때는 `LAYOUT_PARSER_BASE_URL`을 이 주소로 맞춘다. 로컬 Docker 브리지 환경에서는 보통 `http://172.17.0.1:5060`을 사용한다.

기본 원칙은 다음과 같다.

- parser 컨테이너는 공용 서버 스택이 아니라 로컬 개발용 PC에서 실행한다.
- 서버는 MongoDB, PostgreSQL, Airflow 중심으로 유지한다.
- parser는 가능하면 GPU를 사용하고, GPU가 없으면 CPU로 fallback한다.
- parser가 없어도 `pypdf` fallback 경로는 동작하지만 품질 검증은 parser를 켠 상태를 기준으로 수행한다.

## 9. 서버 스택 실행

인프라, Airflow, DB, 통합 테스트 담당자는 아래 명령으로 서버 스택을 올릴 수 있다.

```bash
bash scripts/setup-server.sh
docker compose -p arxplore_server -f docker-compose.server.yml ps
```

핵심 컨테이너는 다음과 같다.

- `arxplore-postgres`
- `arxplore-mongodb`
- `arxplore-airflow-init`
- `arxplore-airflow-web`
- `arxplore-airflow-scheduler`
- `arxplore-airflow-dag-processor`

## 10. Windows 브라우저에서 서버 접근

WSL에만 Tailscale이 설치되어 있으므로, Windows 브라우저에서 Airflow 웹 UI 등을 보려면 포트 포워딩이 필요하다.

### 사전 준비

```bash
sudo apt install openssh-server -y
sudo service ssh start
```

### 포트 포워딩 실행

```bash
bash scripts/port-forward.sh
```

포워딩되는 주소:

| 서비스 | Windows 브라우저 주소 |
|--------|----------------------|
| Airflow | `http://127.0.0.1:18080` |
| PostgreSQL | `127.0.0.1:15432` |
| MongoDB | `127.0.0.1:17017` |

MongoDB Compass에서는 아래 연결 문자열 형식을 권장한다.

```text
mongodb://<MONGO_INITDB_ROOT_USERNAME>:<MONGO_INITDB_ROOT_PASSWORD>@127.0.0.1:17017/?authSource=admin&directConnection=true
```

연결이 되지 않으면 먼저 다음 상태를 다시 확인한다.

- WSL에서 `sudo service ssh start`가 실행 중인지
- `bash scripts/port-forward.sh`가 종료되지 않고 유지되고 있는지
- Compass에서 `127.0.0.1:17017`와 `authSource=admin`을 사용하고 있는지

## 11. 접속 정보 요약

### dev 컨테이너 / 코드에서

| 서비스 | 주소 |
|--------|------|
| PostgreSQL | `100.106.29.101:15432` |
| MongoDB | `100.106.29.101:17017` |
| Airflow API | `http://100.106.29.101:18080` |
| Layout Parser | `http://172.17.0.1:5060` 또는 로컬 parser 주소 |

### Windows 브라우저 / DB 클라이언트에서

| 서비스 | 주소 |
|--------|------|
| Airflow | `http://127.0.0.1:18080` |
| PostgreSQL | `127.0.0.1:15432` |
| MongoDB | `127.0.0.1:17017` |

## 12. LangSmith 설정

LangSmith는 별도 컨테이너 없이 Python 실행 환경에서 사용한다. 공용 API 키는 `.env`에 이미 설정되어 있으므로, 각자 `LANGSMITH_TRACE_USER`에 본인 이름만 넣으면 된다.

```env
LANGSMITH_TRACE_USER=홍길동
```
