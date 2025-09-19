#!/bin/bash

set -euo pipefail

PORT=${PORT:-9002}
WORKERS=${WORKERS:-1}
HOST=${HOST:-0.0.0.0}
LOG_LEVEL=${LOG_LEVEL:-debug}   # 新增

ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
export PYTHONPATH="$ROOT_DIR"
export LOG_LEVEL   # 传递给 Python

echo "🔊 启动TTS模型服务 (端口: ${PORT}, 进程: ${WORKERS}, 日志: ${LOG_LEVEL})"
cd "$ROOT_DIR"

exec uvicorn models.tts_service.tts_service:app \
  --host "$HOST" \
  --port "$PORT" \
  --workers "$WORKERS"
