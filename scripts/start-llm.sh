#!/bin/bash

set -euo pipefail

# --- 环境变量配置 ---
PORT=${PORT:-9001}
HOST=${HOST:-0.0.0.0}
LOG_LEVEL=${LOG_LEVEL:-debug}

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
export PYTHONPATH="$ROOT_DIR"
export LOG_LEVEL

echo "🧠 启动LLM模型服务 (端口: $PORT, 日志: $LOG_LEVEL)"
cd "$ROOT_DIR/models/llm_service"

exec python llm_service.py
