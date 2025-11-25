#!/bin/bash

set -euo pipefail

# 加载统一配置
source "$(dirname "$0")/load_config.sh"

# --- 环境变量配置（优先级：环境变量 > 配置文件 > 默认值）---
PORT=${PORT:-${TTS_MINNAN_PORT:-9031}}
HOST=${HOST:-${TTS_MINNAN_HOST:-0.0.0.0}}
WORKERS=${WORKERS:-1}
LOG_LEVEL=${LOG_LEVEL:-debug}

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
export PYTHONPATH="$ROOT_DIR"
export LOG_LEVEL

echo "🔊 启动TTS模型服务 (端口: $PORT, 主机: $HOST, 进程: $WORKERS, 日志: $LOG_LEVEL)"
cd "$ROOT_DIR/models/tts_service"

exec python -m uvicorn tts_service_minnan:app \
  --host "$HOST" \
  --port "$PORT" \
  --reload \
  --reload-dir "$(pwd)" \
  --log-level "$LOG_LEVEL" \
  --workers "$WORKERS"
