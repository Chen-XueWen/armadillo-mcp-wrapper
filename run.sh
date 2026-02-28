#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

BACKEND_PORT="${GOVERNOR_BACKEND_PORT:-8000}"
FRONTEND_PORT="${GOVERNOR_UI_PORT:-5173}"
PYTHON_BIN="${GOVERNOR_PYTHON_BIN:-/opt/anaconda3/envs/deepseek-ocr/bin/python}"
UVICORN_BIN="${GOVERNOR_UVICORN_BIN:-/opt/anaconda3/envs/deepseek-ocr/bin/uvicorn}"
ENABLE_NGROK="${GOVERNOR_ENABLE_NGROK:-1}"
RUN_SIMULATION="${GOVERNOR_RUN_SIMULATION:-1}"

BACKEND_LOG="${GOVERNOR_BACKEND_LOG_FILE:-backend.log}"
FRONTEND_LOG="${GOVERNOR_FRONTEND_LOG_FILE:-frontend.log}"
NGROK_FRONTEND_LOG="${GOVERNOR_NGROK_FRONTEND_LOG_FILE:-ngrok-frontend.log}"

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

kill_port() {
  local port="$1"
  local pids
  pids="$(lsof -ti:"$port" 2>/dev/null || true)"
  if [[ -n "${pids:-}" ]]; then
    kill -9 $pids 2>/dev/null || true
  fi
}

wait_for_url() {
  local url="$1"
  local timeout_seconds="${2:-30}"
  local elapsed=0
  while (( elapsed < timeout_seconds )); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    ((elapsed+=1))
  done
  return 1
}

start_ngrok_tunnel() {
  local port="$1"
  local log_file="$2"
  ngrok http "$port" --log stdout --log-format json >>"$log_file" 2>&1 &
  echo $!
}

read_ngrok_url() {
  local log_file="$1"
  local url=""
  local attempt=0

  while (( attempt < 30 )); do
    url="$(sed -n 's/.*"url":"\(https:[^"]*\)".*/\1/p' "$log_file" | tail -n 1)"

    if [[ -n "${url:-}" ]]; then
      echo "$url"
      return 0
    fi

    sleep 1
    ((attempt+=1))
  done

  return 1
}

cd "$ROOT_DIR"
need_cmd lsof
need_cmd curl
need_cmd npm
need_cmd "$PYTHON_BIN"
need_cmd "$UVICORN_BIN"

echo "Cleaning up existing backend/frontend processes on ports ${BACKEND_PORT}/${FRONTEND_PORT}..."
kill_port "$BACKEND_PORT"
kill_port "$FRONTEND_PORT"

echo "Starting Governor-MCP backend on :${BACKEND_PORT}..."
"$UVICORN_BIN" backend.main:app --host 0.0.0.0 --port "$BACKEND_PORT" --reload >>"$BACKEND_LOG" 2>&1 &

if ! wait_for_url "http://127.0.0.1:${BACKEND_PORT}/healthz" 30; then
  echo "Backend failed health check. Tail ${BACKEND_LOG} for details." >&2
  exit 1
fi

BACKEND_LOCAL_URL="http://127.0.0.1:${BACKEND_PORT}"
FRONTEND_PUBLIC_URL=""

echo "Starting Governor-MCP frontend on :${FRONTEND_PORT} (proxy target: ${BACKEND_LOCAL_URL})..."
(
  cd "$ROOT_DIR/frontend-react"
  VITE_API_BASE_URL="/" \
  VITE_DEV_PROXY_TARGET="$BACKEND_LOCAL_URL" \
  npm run dev -- --host 0.0.0.0 --port "$FRONTEND_PORT" >>"$ROOT_DIR/$FRONTEND_LOG" 2>&1 &
)

if ! wait_for_url "http://127.0.0.1:${FRONTEND_PORT}" 30; then
  echo "Frontend failed health check. Tail ${FRONTEND_LOG} for details." >&2
  exit 1
fi

if [[ "$ENABLE_NGROK" == "1" ]]; then
  if command -v ngrok >/dev/null 2>&1; then
    : >"$NGROK_FRONTEND_LOG"
    echo "Starting ngrok tunnel for frontend only..."
    start_ngrok_tunnel "$FRONTEND_PORT" "$NGROK_FRONTEND_LOG" >/dev/null
    FRONTEND_PUBLIC_URL="$(read_ngrok_url "$NGROK_FRONTEND_LOG" || true)"
    if [[ -z "${FRONTEND_PUBLIC_URL:-}" ]]; then
      echo "Could not resolve frontend ngrok URL. Check ${NGROK_FRONTEND_LOG}." >&2
    fi
  else
    echo "ngrok not found. Continuing without public tunnel." >&2
  fi
fi

echo
echo "Demo services are up:"
echo "  Backend local:  ${BACKEND_LOCAL_URL}"
echo "  Frontend local: http://127.0.0.1:${FRONTEND_PORT}"
if [[ "${FRONTEND_PUBLIC_URL:-}" == https://* ]]; then
  echo "  Frontend public: ${FRONTEND_PUBLIC_URL}"
fi
echo
echo "Remote frontend traffic proxies /api to local backend via Vite dev proxy."
echo

if [[ "$RUN_SIMULATION" == "1" ]]; then
  echo "Starting simulation..."
  "$PYTHON_BIN" "$ROOT_DIR/simulation/agent_mock.py"
fi
