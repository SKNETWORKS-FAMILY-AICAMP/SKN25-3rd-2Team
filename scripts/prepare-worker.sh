#!/usr/bin/env bash
set -euo pipefail

PROJECT_NAME="${PROJECT_NAME:-arxplore_dev}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.dev.yml}"
MAX_JOBS_PER_RUN="${MAX_JOBS_PER_RUN:-1}"
EMBED_MAX_CHUNKS="${EMBED_MAX_CHUNKS:-200}"
EMBED_BACKLOG_MAX_CHUNKS="${EMBED_BACKLOG_MAX_CHUNKS:-400}"
SLEEP_SECONDS="${SLEEP_SECONDS:-120}"
WAIT_TIMEOUT_SECONDS="${WAIT_TIMEOUT_SECONDS:-120}"
RUN_MODE="${1:-loop}"
EXTRA_ARGS=()
if [[ "$#" -ge 2 ]]; then
  EXTRA_ARGS=("${@:2}")
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${REPO_ROOT}"

if [[ ! -f .env ]]; then
  echo ".env 파일이 없습니다. 루트에 .env를 만든 뒤 다시 실행하세요."
  exit 1
fi

LOOP_ARGS="--loop --sleep-seconds ${SLEEP_SECONDS} --wait-timeout-seconds ${WAIT_TIMEOUT_SECONDS}"
if [[ "${RUN_MODE}" == "once" ]]; then
  LOOP_ARGS=""
fi

if [[ "${RUN_MODE}" != "loop" && "${RUN_MODE}" != "once" ]]; then
  echo "사용법: bash scripts/prepare-worker.sh [loop|once]"
  exit 1
fi

echo "[prepare-worker] mode=${RUN_MODE} project=${PROJECT_NAME} compose=${COMPOSE_FILE}"
echo "[prepare-worker] max_jobs_per_run=${MAX_JOBS_PER_RUN} embed_max_chunks=${EMBED_MAX_CHUNKS} embed_backlog_max_chunks=${EMBED_BACKLOG_MAX_CHUNKS} wait_timeout_seconds=${WAIT_TIMEOUT_SECONDS}"

docker compose -p "${PROJECT_NAME}" -f "${COMPOSE_FILE}" exec dev bash -lc \
  "cd /workspace && python3 -m src.pipeline.prepare_worker --mode auto --max-jobs-per-run ${MAX_JOBS_PER_RUN} --embed-max-chunks ${EMBED_MAX_CHUNKS} --embed-backlog-max-chunks ${EMBED_BACKLOG_MAX_CHUNKS} ${LOOP_ARGS} ${EXTRA_ARGS[*]:-}"
