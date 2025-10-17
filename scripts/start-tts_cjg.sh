#!/bin/bash
set -euo pipefail

PORT=${PORT:-9031}
HOST=${HOST:-0.0.0.0}
WORKERS=${WORKERS:-1}
GPU_ID=${GPU_ID:-6}
LOG_LEVEL=${LOG_LEVEL:-debug}

ROOT_DIR="/root/MintaiDialect"   # 你的服务 repo 根（含 models/tts_service）
INFER_CODE="/home/yyz/infer-code" # 你原始 webui 所在目录（包含 indextts）

export PYTHONPATH="${ROOT_DIR}:${INFER_CODE}"
export LOG_LEVEL
export MODEL_DIR="/home/yyz/ckpts/runs/infer-cjg-ckpt"

echo "🔊 启动陈嘉庚TTS模型服务 (端口: $PORT, GPU: $GPU_ID, workers: $WORKERS, log: $LOG_LEVEL)"
cd "${ROOT_DIR}/models/tts_service"

# 激活 conda env（如需要）
source /home/yyz/anaconda3/bin/activate /home/yyz/anaconda3/envs/itts

CUDA_VISIBLE_DEVICES=$GPU_ID \
python -m uvicorn tts_service_cjg:app \
  --host "$HOST" \
  --port "$PORT" \
  --log-level "$LOG_LEVEL" \
  --workers "$WORKERS" \
  --reload \
  --reload-dir "$(pwd)"
