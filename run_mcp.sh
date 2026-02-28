#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="${ROOT_DIR}/.run"
LOG_DIR="${ROOT_DIR}/logs"

BACKEND_HOST="${GOVERNOR_BACKEND_HOST:-0.0.0.0}"
BACKEND_PORT="${GOVERNOR_BACKEND_PORT:-8000}"
BACKEND_WORKERS="${GOVERNOR_BACKEND_WORKERS:-1}"
BACKEND_LOG_LEVEL="${GOVERNOR_BACKEND_LOG_LEVEL:-info}"
BACKEND_HEALTH_PATH="${GOVERNOR_BACKEND_HEALTH_PATH:-/healthz}"

UI_MODE="${GOVERNOR_UI_MODE:-preview}" # preview | dev | none
UI_HOST="${GOVERNOR_UI_HOST:-0.0.0.0}"
UI_PORT="${GOVERNOR_UI_PORT:-5173}"
UI_BUILD_ON_START="${GOVERNOR_UI_BUILD_ON_START:-1}"

PYTHON_BIN="${GOVERNOR_PYTHON_BIN:-python3}"
BACKEND_PID_FILE="${RUN_DIR}/backend.pid"
FRONTEND_PID_FILE="${RUN_DIR}/frontend.pid"
BACKEND_LOG_FILE="${LOG_DIR}/backend.log"
FRONTEND_LOG_FILE="${LOG_DIR}/frontend.log"

START_TIMEOUT_SECONDS="${GOVERNOR_START_TIMEOUT_SECONDS:-30}"

usage() {
  cat <<'EOF'
Usage:
  ./run_mcp.sh start
  ./run_mcp.sh stop
  ./run_mcp.sh restart
  ./run_mcp.sh status
  ./run_mcp.sh logs [backend|frontend]

Environment overrides:
  GOVERNOR_PYTHON_BIN              Python executable (default: python3)
  GOVERNOR_BACKEND_HOST            Backend bind host (default: 0.0.0.0)
  GOVERNOR_BACKEND_PORT            Backend port (default: 8000)
  GOVERNOR_BACKEND_WORKERS         Uvicorn worker count (default: 1)
  GOVERNOR_BACKEND_LOG_LEVEL       Uvicorn log level (default: info)
  GOVERNOR_UI_MODE                 preview|dev|none (default: preview)
  GOVERNOR_UI_HOST                 Frontend bind host (default: 0.0.0.0)
  GOVERNOR_UI_PORT                 Frontend port (default: 5173)
  GOVERNOR_UI_BUILD_ON_START       Build UI before preview start (default: 1)
  GOVERNOR_START_TIMEOUT_SECONDS   Health check timeout in seconds (default: 30)
EOF
}

need_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1" >&2
    exit 1
  fi
}

is_pid_running() {
  local pid="$1"
  kill -0 "$pid" >/dev/null 2>&1
}

read_pid() {
  local file="$1"
  if [[ -f "$file" ]]; then
    cat "$file"
  fi
}

ensure_dirs() {
  mkdir -p "$RUN_DIR" "$LOG_DIR"
}

port_in_use() {
  local port="$1"
  lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
}

wait_for_url() {
  local url="$1"
  local timeout="$2"
  local elapsed=0
  while (( elapsed < timeout )); do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
    ((elapsed+=1))
  done
  return 1
}

start_backend() {
  local existing_pid
  existing_pid="$(read_pid "$BACKEND_PID_FILE")"
  if [[ -n "${existing_pid:-}" ]] && is_pid_running "$existing_pid"; then
    echo "Backend already running (pid: $existing_pid)"
    return 0
  fi

  if port_in_use "$BACKEND_PORT"; then
    echo "Backend port $BACKEND_PORT is already in use. Refusing to start." >&2
    exit 1
  fi

  echo "Starting backend API..."
  (
    cd "$ROOT_DIR"
    nohup "$PYTHON_BIN" -m uvicorn backend.main:app \
      --host "$BACKEND_HOST" \
      --port "$BACKEND_PORT" \
      --workers "$BACKEND_WORKERS" \
      --log-level "$BACKEND_LOG_LEVEL" \
      >>"$BACKEND_LOG_FILE" 2>&1 &
    echo $! > "$BACKEND_PID_FILE"
  )

  if ! wait_for_url "http://127.0.0.1:${BACKEND_PORT}${BACKEND_HEALTH_PATH}" "$START_TIMEOUT_SECONDS"; then
    echo "Backend failed health check. Recent logs:" >&2
    tail -n 40 "$BACKEND_LOG_FILE" >&2 || true
    exit 1
  fi
}

start_frontend() {
  if [[ "$UI_MODE" == "none" ]]; then
    echo "UI mode is 'none'; skipping frontend."
    return 0
  fi

  local existing_pid
  existing_pid="$(read_pid "$FRONTEND_PID_FILE")"
  if [[ -n "${existing_pid:-}" ]] && is_pid_running "$existing_pid"; then
    echo "Frontend already running (pid: $existing_pid)"
    return 0
  fi

  if port_in_use "$UI_PORT"; then
    echo "Frontend port $UI_PORT is already in use. Refusing to start." >&2
    exit 1
  fi

  need_cmd npm
  local frontend_dir="${ROOT_DIR}/frontend-react"

  if [[ "$UI_MODE" == "preview" ]]; then
    if [[ "$UI_BUILD_ON_START" == "1" || ! -f "${frontend_dir}/dist/index.html" ]]; then
      echo "Building frontend bundle..."
      (
        cd "$frontend_dir"
        npm run build >>"$FRONTEND_LOG_FILE" 2>&1
      )
    fi
    echo "Starting frontend preview server..."
    (
      cd "$frontend_dir"
      nohup npm run preview -- --host "$UI_HOST" --port "$UI_PORT" >>"$FRONTEND_LOG_FILE" 2>&1 &
      echo $! > "$FRONTEND_PID_FILE"
    )
  elif [[ "$UI_MODE" == "dev" ]]; then
    echo "Starting frontend dev server..."
    (
      cd "$frontend_dir"
      nohup npm run dev -- --host "$UI_HOST" --port "$UI_PORT" >>"$FRONTEND_LOG_FILE" 2>&1 &
      echo $! > "$FRONTEND_PID_FILE"
    )
  else
    echo "Invalid GOVERNOR_UI_MODE: $UI_MODE (expected: preview, dev, none)" >&2
    exit 1
  fi

  if ! wait_for_url "http://127.0.0.1:${UI_PORT}" "$START_TIMEOUT_SECONDS"; then
    echo "Frontend failed health check. Recent logs:" >&2
    tail -n 40 "$FRONTEND_LOG_FILE" >&2 || true
    exit 1
  fi
}

stop_process() {
  local label="$1"
  local pid_file="$2"
  local pid
  pid="$(read_pid "$pid_file")"
  if [[ -z "${pid:-}" ]]; then
    echo "$label is not running (no pid file)."
    return 0
  fi
  if ! is_pid_running "$pid"; then
    echo "$label pid file exists but process is not running. Cleaning up stale pid."
    rm -f "$pid_file"
    return 0
  fi

  echo "Stopping $label (pid: $pid)..."
  kill "$pid" >/dev/null 2>&1 || true

  local waited=0
  while is_pid_running "$pid" && (( waited < 10 )); do
    sleep 1
    ((waited+=1))
  done

  if is_pid_running "$pid"; then
    echo "$label did not stop in time; sending SIGKILL."
    kill -9 "$pid" >/dev/null 2>&1 || true
  fi

  rm -f "$pid_file"
}

show_status() {
  local backend_pid frontend_pid
  backend_pid="$(read_pid "$BACKEND_PID_FILE")"
  frontend_pid="$(read_pid "$FRONTEND_PID_FILE")"

  if [[ -n "${backend_pid:-}" ]] && is_pid_running "$backend_pid"; then
    echo "Backend: running (pid: $backend_pid) http://127.0.0.1:${BACKEND_PORT}"
  else
    echo "Backend: stopped"
  fi

  if [[ "$UI_MODE" == "none" ]]; then
    echo "Frontend: disabled (GOVERNOR_UI_MODE=none)"
  elif [[ -n "${frontend_pid:-}" ]] && is_pid_running "$frontend_pid"; then
    echo "Frontend: running (pid: $frontend_pid) http://127.0.0.1:${UI_PORT}"
  else
    echo "Frontend: stopped"
  fi
}

follow_logs() {
  local target="${1:-backend}"
  case "$target" in
    backend) tail -f "$BACKEND_LOG_FILE" ;;
    frontend) tail -f "$FRONTEND_LOG_FILE" ;;
    *)
      echo "Unknown log target: $target (expected backend|frontend)" >&2
      exit 1
      ;;
  esac
}

main() {
  ensure_dirs

  local action="${1:-start}"
  case "$action" in
    start)
      need_cmd "$PYTHON_BIN"
      need_cmd lsof
      need_cmd curl
      start_backend
      start_frontend
      show_status
      echo "MCP wrapper binary: ${ROOT_DIR}/backend/mcp_server.py"
      echo "Backend log: $BACKEND_LOG_FILE"
      if [[ "$UI_MODE" != "none" ]]; then
        echo "Frontend log: $FRONTEND_LOG_FILE"
      fi
      ;;
    stop)
      stop_process "Frontend" "$FRONTEND_PID_FILE"
      stop_process "Backend" "$BACKEND_PID_FILE"
      ;;
    restart)
      need_cmd "$PYTHON_BIN"
      need_cmd lsof
      need_cmd curl
      stop_process "Frontend" "$FRONTEND_PID_FILE"
      stop_process "Backend" "$BACKEND_PID_FILE"
      start_backend
      start_frontend
      show_status
      ;;
    status)
      show_status
      ;;
    logs)
      follow_logs "${2:-backend}"
      ;;
    help|-h|--help)
      usage
      ;;
    *)
      echo "Unknown action: $action" >&2
      usage
      exit 1
      ;;
  esac
}

main "$@"
