#!/bin/bash

# --- 环境变量配置 ---
# 代理服务器地址
PROXY_URL="http://127.0.0.1:7890"
# 不需要走代理的地址 (本地地址, 内网IP段等)
NO_PROXY="localhost,127.0.0.1,::1"

# --- 服务启动 ---
echo "🔧 准备启动后端API服务 (端口: 8000)"
cd backend

# 将当前目录添加到Python模块搜索路径
export PYTHONPATH="$(pwd)"

echo "🚀 使用代理 ${PROXY_URL} 启动服务..."
# 使用 exec 启动 uvicorn，并将代理环境变量传递给它
exec env \
  http_proxy="${PROXY_URL}" \
  https_proxy="${PROXY_URL}" \
  no_proxy="${NO_PROXY}" \
  uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --reload \
  --reload-dir "$(pwd)" \
  --log-level debug