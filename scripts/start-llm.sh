#!/bin/bash

set -euo pipefail

# 加载统一配置
source "$(dirname "$0")/load_config.sh"

# --- 环境变量配置（优先级：环境变量 > 配置文件 > 默认值）---
PORT=${PORT:-${LLM_PORT:-9020}}
HOST=${HOST:-${LLM_HOST:-0.0.0.0}}
GPU_ID=${GPU_ID:-0}
LOG_LEVEL=${LOG_LEVEL:-debug}

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
export PYTHONPATH="$ROOT_DIR"
export LOG_LEVEL

echo "🧠 启动LLM模型服务 (端口: $PORT, 主机: $HOST, GPU: $GPU_ID, 日志: $LOG_LEVEL)"
cd "$ROOT_DIR/models/llm_service"

# 使用 uvicorn 启动，支持更多配置选项
# vLLM 需要 GPU，通过 CUDA_VISIBLE_DEVICES 指定 GPU
# 注意：vLLM 模型服务不支持热重载（--reload），因为模型占用大量GPU内存
# 修改代码后需要手动重启服务
CUDA_VISIBLE_DEVICES=$GPU_ID \
python -m uvicorn llm_service:app \
  --host "$HOST" \
  --port "$PORT" \
  --log-level "$LOG_LEVEL" \
  --workers 1
