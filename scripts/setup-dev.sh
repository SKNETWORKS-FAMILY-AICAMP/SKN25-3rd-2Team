#!/usr/bin/env bash
set -euo pipefail

PROJECT_NAME="arxplore_dev"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

if [[ ! -f .env ]]; then
  echo ".env 파일이 없습니다. 루트에 .env를 만든 뒤 다시 실행하세요."
  exit 1
fi

docker compose -p "${PROJECT_NAME}" -f docker-compose.dev.yml up -d --build

echo
echo "[dev] 컨테이너 상태"
docker compose -p "${PROJECT_NAME}" -f docker-compose.dev.yml ps

echo
echo "[dev] 접속 정보"
echo "Jupyter: http://127.0.0.1:${JUPYTER_PORT:-18888}"
echo "Streamlit: 컨테이너 접속 후 수동 실행"
echo "접속 명령: docker compose -p ${PROJECT_NAME} -f docker-compose.dev.yml exec dev bash"
