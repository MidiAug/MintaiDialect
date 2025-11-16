#!/bin/bash

set -euo pipefail

# --- 环境变量配置 ---
PORT=${PORT:-8008}
HOST=${HOST:-0.0.0.0}
LOG_LEVEL=${LOG_LEVEL:-debug}
PROXY_URL=${PROXY_URL:-"http://127.0.0.1:7890"}
NO_PROXY=${NO_PROXY:-"localhost,127.0.0.1,::1"}

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
export PYTHONPATH="$ROOT_DIR"
export LOG_LEVEL

echo "🔧 启动后端API服务 (端口: $PORT, 日志: $LOG_LEVEL)"
cd "$ROOT_DIR/backend"

# 将当前目录添加到Python模块搜索路径
export PYTHONPATH="$(pwd):$PYTHONPATH"

echo "🚀 使用代理 ${PROXY_URL} 启动服务..."
# 使用 exec 启动 uvicorn，并将代理环境变量传递给它
exec env \
  http_proxy="${PROXY_URL}" \
  https_proxy="${PROXY_URL}" \
  no_proxy="${NO_PROXY}" \
  python -m uvicorn app.main:app \
  --host "$HOST" \
  --port "$PORT" \
  --reload \
  --reload-dir "$(pwd)" \
  --log-level "$LOG_LEVEL"