#!/bin/bash

set -euo pipefail

# --- 环境变量配置 ---
PORT=${PORT:-9030}
WORKERS=${WORKERS:-1}
HOST=${HOST:-0.0.0.0}
LOG_LEVEL=${LOG_LEVEL:-debug}

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
export PYTHONPATH="$ROOT_DIR"
export LOG_LEVEL

echo "🔊 启动TTS模型服务 (端口: $PORT, 进程: $WORKERS, 日志: $LOG_LEVEL)"
cd "$ROOT_DIR/models/tts_service"

exec python -m uvicorn tts_service:app \
  --host "$HOST" \
  --port "$PORT" \
  --reload \
  --reload-dir "$(pwd)" \
  --log-level "$LOG_LEVEL" \
  --workers "$WORKERS"
