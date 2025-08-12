#!/bin/bash

set -euo pipefail

PORT=${PORT:-9002}
WORKERS=${WORKERS:-2}
HOST=${HOST:-0.0.0.0}

# 将根目录定位到 data/MintaiDialect
ROOT_DIR=$(cd "$(dirname "$0")/../.." && pwd)
export PYTHONPATH="$ROOT_DIR"

echo "🔊 启动TTS模型服务 (端口: ${PORT}, 进程: ${WORKERS})"
cd "$ROOT_DIR"

# 使用 uvicorn CLI 以模块字符串加载，方可启用 --workers
exec uvicorn models.tts_service.tts_service:app \
  --host "$HOST" \
  --port "$PORT" \
  --workers "$WORKERS"
