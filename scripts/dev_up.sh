#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8000}"
WEB_HOST="${WEB_HOST:-127.0.0.1}"
WEB_PORT="${WEB_PORT:-5173}"

echo "[dev_up] cleaning old local processes on ${API_PORT}/${WEB_PORT}"
pkill -f "uvicorn app.main:app --host ${API_HOST} --port ${API_PORT}" >/dev/null 2>&1 || true
pkill -f "vite --open=false --host ${WEB_HOST} --port ${WEB_PORT}" >/dev/null 2>&1 || true
pkill -f "npm run dev -- --open=false --host ${WEB_HOST} --port ${WEB_PORT}" >/dev/null 2>&1 || true

echo "[dev_up] starting backend: http://${API_HOST}:${API_PORT}"
cd "${ROOT_DIR}"
python3 -m uvicorn app.main:app --host "${API_HOST}" --port "${API_PORT}" >/tmp/cn_api.log 2>&1 &
API_PID=$!

cleanup() {
  if ps -p "${API_PID}" >/dev/null 2>&1; then
    kill "${API_PID}" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

echo "[dev_up] starting frontend: http://${WEB_HOST}:${WEB_PORT}"
cd "${ROOT_DIR}/frontend"
VITE_API_BASE="http://${API_HOST}:${API_PORT}" npm run dev -- --open=false --host "${WEB_HOST}" --port "${WEB_PORT}" --strictPort
