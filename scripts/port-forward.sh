#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${REPO_ROOT}/.env"

SERVER_IP="${TAILSCALE_SERVER_IP:-100.106.29.101}"
AIRFLOW_PORT="${SERVER_AIRFLOW_PORT:-18080}"
POSTGRES_PORT="${SERVER_POSTGRES_PORT:-15432}"
MONGO_PORT="${SERVER_MONGO_PORT:-17017}"

echo "[port-forward] ArXplore 서버(${SERVER_IP})로 포트 포워딩"
echo "  Airflow:    localhost:${AIRFLOW_PORT}"
echo "  PostgreSQL: localhost:${POSTGRES_PORT}"
echo "  MongoDB:    localhost:${MONGO_PORT}"
echo ""

ssh -N \
  -L ${AIRFLOW_PORT}:${SERVER_IP}:${AIRFLOW_PORT} \
  -L ${POSTGRES_PORT}:${SERVER_IP}:${POSTGRES_PORT} \
  -L ${MONGO_PORT}:${SERVER_IP}:${MONGO_PORT} \
  localhost &

SSH_PID=$!
echo ""
echo "[port-forward] 포워딩 활성화 (PID: ${SSH_PID})"

trap "kill ${SSH_PID} 2>/dev/null; echo ''; echo '[port-forward] 종료'; exit 0" INT TERM
wait ${SSH_PID}
