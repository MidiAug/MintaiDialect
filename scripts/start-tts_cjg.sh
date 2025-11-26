#!/bin/bash
set -euo pipefail

source "$(dirname "$0")/load_config.sh"

PORT=${PORT:-${TTS_CJG_PORT:-9032}}
HOST=${HOST:-${TTS_CJG_HOST:-0.0.0.0}}
GPU_ID=${GPU_ID:-0}
WORKERS=${WORKERS:-5}
LOG_LEVEL=${LOG_LEVEL:-debug}

ROOT_DIR=$(cd "$(dirname "$0")/.." && pwd)
INDEXTTS_DIR="${ROOT_DIR}/packages"

# 将 packages/infer-code 添加到 PYTHONPATH，优先使用本地支持 speaker_info_path 的版本
export PYTHONPATH="${INDEXTTS_DIR}:${ROOT_DIR}"
export MODEL_DIR="${ROOT_DIR}/models/tts_service/ckpt/cjg"
export AUDIO_PROMPT="${ROOT_DIR}/models/tts_service/speaker_audio/陈嘉庚.wav"

export DS_BUILD_OPS=0
export DS_SKIP_CUDA_CHECK=1

echo "🚀 启动陈嘉庚TTS服务 (port=$PORT, gpu=$GPU_ID, workers=$WORKERS)"
cd "$ROOT_DIR/models/tts_service"

exec python -m uvicorn tts_service_cjg:app \
  --host "$HOST" \
  --port "$PORT" \
  --log-level "$LOG_LEVEL" \
  --workers "$WORKERS"
