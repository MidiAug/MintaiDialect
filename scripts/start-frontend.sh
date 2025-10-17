#!/bin/bash

set -euo pipefail

# --- 环境变量配置 ---
PORT=${PORT:-5173}
HOST=${HOST:-localhost}

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)

echo "🌐 启动前端开发服务 (端口: $PORT)"
cd "$ROOT_DIR/frontend"

exec npm run dev
