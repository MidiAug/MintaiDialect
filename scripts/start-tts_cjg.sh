#!/bin/bash
set -euo pipefail

source "$(dirname "$0")/load_config.sh"

PORT=${PORT:-${TTS_CJG_PORT:-9032}}
HOST=${HOST:-${TTS_CJG_HOST:-0.0.0.0}}
GPU_ID=${GPU_ID:-0}
WORKERS=${WORKERS:-4}
LOG_LEVEL=${LOG_LEVEL:-debug}

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
INFER_CODE="/root/data/MintaiDialect/models/tts_service/infer-code"

export PYTHONPATH="${ROOT_DIR}:${INFER_CODE}"
export MODEL_DIR="/root/data/MintaiDialect/models/tts_service/ckpt/cjg"

export DS_BUILD_OPS=0
export DS_SKIP_CUDA_CHECK=1

echo "🚀 启动陈嘉庚TTS服务 (port=$PORT, gpu=$GPU_ID, workers=$WORKERS)"
cd "$ROOT_DIR/models/tts_service"

exec python -m uvicorn tts_service_cjg:app \
  --host "$HOST" \
  --port "$PORT" \
  --log-level "$LOG_LEVEL" \
  --workers "$WORKERS"
