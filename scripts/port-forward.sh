#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

source "${REPO_ROOT}/.env"

SERVER_IP="${TAILSCALE_SERVER_IP:-100.106.29.101}"
AIRFLOW_PORT="${SERVER_AIRFLOW_PORT:-18080}"
POSTGRES_PORT="${SERVER_POSTGRES_PORT:-15432}"
MONGO_PORT="${SERVER_MONGO_PORT:-17017}"
ACTION="${1:-start}"

get_running_pids() {
  pgrep -f "ssh -N .*${AIRFLOW_PORT}:${SERVER_IP}:${AIRFLOW_PORT}.*${POSTGRES_PORT}:${SERVER_IP}:${POSTGRES_PORT}.*${MONGO_PORT}:${SERVER_IP}:${MONGO_PORT}.*localhost" || true
}

is_running() {
  [[ -n "$(get_running_pids)" ]]
}

check_port_available() {
  local port="$1"
  python3 - <<PY
import socket
port = int("${port}")
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.bind(("127.0.0.1", port))
except OSError:
    raise SystemExit(1)
finally:
    s.close()
PY
}

stop_forward() {
  if is_running; then
    local pids
    pids="$(get_running_pids)"
    while read -r pid; do
      [[ -n "${pid}" ]] || continue
      kill "${pid}" 2>/dev/null || true
    done <<< "${pids}"
    echo "[port-forward] 종료 (PID: ${pids//$'\n'/, })"
    return 0
  fi
  echo "[port-forward] 실행 중인 포워딩 없음"
}

status_forward() {
  if is_running; then
    local pids
    pids="$(get_running_pids)"
    echo "[port-forward] 실행 중 (PID: ${pids//$'\n'/, })"
  else
    echo "[port-forward] 중지됨"
  fi
}

case "${ACTION}" in
  stop)
    stop_forward
    exit 0
    ;;
  status)
    status_forward
    exit 0
    ;;
  restart)
    stop_forward
    ;;
  start)
    ;;
  *)
    echo "사용법: bash scripts/port-forward.sh [start|stop|status|restart]"
    exit 1
    ;;
esac

if is_running; then
  pids="$(get_running_pids)"
  echo "[port-forward] 이미 실행 중 (PID: ${pids//$'\n'/, })"
  echo "필요하면: bash scripts/port-forward.sh restart"
  exit 0
fi

echo "[port-forward] ArXplore 서버(${SERVER_IP})로 포트 포워딩"
echo "  Airflow:    localhost:${AIRFLOW_PORT}"
echo "  PostgreSQL: localhost:${POSTGRES_PORT}"
echo "  MongoDB:    localhost:${MONGO_PORT}"
echo ""

for p in "${AIRFLOW_PORT}" "${POSTGRES_PORT}" "${MONGO_PORT}"; do
  if ! check_port_available "${p}"; then
    echo "[port-forward] 포트 ${p}가 이미 사용 중입니다."
    echo "현재 점유 프로세스를 먼저 정리하거나 다른 포트를 사용하세요."
    exit 1
  fi
done

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
