#!/bin/bash

set -euo pipefail

# 加载统一配置
source "$(dirname "$0")/load_config.sh"

# --- 环境变量配置（优先级：环境变量 > 配置文件 > 默认值）---
PORT=${PORT:-${FRONTEND_PORT:-5173}}
HOST=${HOST:-${FRONTEND_HOST:-localhost}}

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)

echo "🌐 启动前端开发服务 (端口: $PORT, 主机: $HOST)"
cd "$ROOT_DIR/frontend"

exec npm run dev
