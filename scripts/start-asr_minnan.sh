#!/bin/bash

set -euo pipefail

# 加载统一配置
source "$(dirname "$0")/load_config.sh"

# --- 环境变量配置（优先级：环境变量 > 配置文件 > 默认值）---
PORT=${PORT:-${ASR_PORT:-9011}}
HOST=${HOST:-${ASR_HOST:-0.0.0.0}}
LOG_LEVEL=${LOG_LEVEL:-debug}

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
export PYTHONPATH="$ROOT_DIR"
export LOG_LEVEL

echo "🎤 启动ASR模型服务 (端口: $PORT, 主机: $HOST, 日志: $LOG_LEVEL)"
cd "$ROOT_DIR/models/asr_service"

# 使用 uvicorn 启动 FastAPI ASR 服务，添加调试日志
exec python -m uvicorn asr_service:app \
    --host "$HOST" \
    --port "$PORT" \
    --reload \
    --reload-dir "$(pwd)" \
    --log-level "$LOG_LEVEL"
