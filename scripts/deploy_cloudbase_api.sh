#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_ID="${1:-lung-4g441e9m7f055d4e}"
FUNCTION_NAME="${2:-tcm-api}"

cd "$ROOT_DIR"

python3 scripts/build_cloudbase_http_function.py

tcb fn deploy "$FUNCTION_NAME" \
  --dir "./cloudbase/functions/tcm-api-build" \
  --httpFn \
  --path "/api" \
  -e "$ENV_ID" \
  --force \
  --yes
